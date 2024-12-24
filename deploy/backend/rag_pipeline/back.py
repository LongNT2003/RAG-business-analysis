from FlagEmbedding import FlagReranker
import heapq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document
from datetime import datetime

def get_months_since_reference(date_str, reference_date="2024-11"):
    """
    Chức năng này chuyển đổi chuỗi ngày (MM-YYYY) thành đối tượng datetime
    và tính số tháng kể từ ngày tham chiếu.
    
    Tham số:
    date_str (str): Chuỗi ngày cần tính (định dạng YYYY-MM).
    reference_date (str): Ngày tham chiếu (định dạng YYYY-MM), mặc định là "2024-11".
    
    Trả về:
    int: Số tháng kể từ ngày tham chiếu.
    """
    date = datetime.strptime(date_str, "%Y-%m")
    ref_date = datetime.strptime(reference_date, "%Y-%m")
    
    months_since = abs(date.year - ref_date.year) * 12 + abs(date.month - ref_date.month)
    return months_since

def apply_date_penalty(similarity_score, date_str, weight=0.01):
    """
    Chức năng này tính toán hình phạt cho điểm tương đồng dựa trên độ tuổi của tài liệu.
    
    Tham số:
    similarity_score (float): Điểm tương đồng ban đầu.
    date_str (str): Ngày của tài liệu (định dạng YYYY-MM).
    weight (float): Trọng số cho hình phạt, mặc định là 0.01.
    
    Trả về:
    float: Điểm tương đồng đã điều chỉnh.
    """
    months_since = get_months_since_reference(date_str)
    penalty = 1 + weight * months_since
    adjusted_score = similarity_score / penalty
    return adjusted_score

class LLMHandler:
    def __init__(self, model_name: str, gemini_key: str):
        """
        Khởi tạo LLMHandler với tên mô hình và khóa API.
        
        Tham số:
        model_name (str): Tên mô hình LLM.
        gemini_key (str): Khóa API cho Gemini.
        """
        self.api_key = gemini_key
        self.llm = ChatGoogleGenerativeAI(model=model_name, api_key=self.api_key)
    
    def get_llm(self):
        """
        Trả về đối tượng LLM.
        
        Trả về:
        ChatGoogleGenerativeAI: Đối tượng LLM.
        """
        return self.llm

class VectorDatabase:
    def __init__(self, model_name: str, collection_name: str, api: str, url : str):
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.collection_name = collection_name
        self.api = api
        self.url=url
        self.db = self.load_db()
        
    def load_db(self):
        return QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            collection_name=self.collection_name,
            url = self.url,
            api_key=self.api
        )
    def get_retriever(self):
        return self.db

class QuestionAnsweringChain:
    def __init__(self, llm_handler: LLMHandler, vector_db: VectorDatabase, num_docs: int = 5, 
                 apply_rewrite: bool = False, apply_rerank: bool = False, date_impact: float = 0.01):
        """
        Khởi tạo chuỗi hỏi đáp với các thành phần cần thiết.
        
        Tham số:
        llm_handler (LLMHandler): Đối tượng LLMHandler.
        vector_db (VectorDatabase): Đối tượng VectorDatabase.
        num_docs (int): Số lượng tài liệu cần lấy, mặc định là 5.
        apply_rewrite (bool): Có áp dụng viết lại hay không, mặc định là False.
        apply_rerank (bool): Có áp dụng xếp hạng lại hay không, mặc định là False.
        date_impact (float): Ảnh hưởng của ngày tháng, mặc định là 0.01.
        """
        self.num_docs = num_docs
        self.llm = llm_handler.get_llm()
        self.db = vector_db.get_retriever()
        self.extracted_links=[]
        self.memory = []
        self.date_impact=date_impact
        if apply_rerank:
            self.retriever = self.db.as_retriever(search_kwargs={"k": int(num_docs * 2.5)})
        else:
            self.retriever = self.db.as_retriever(search_kwargs={"k": num_docs})
        self.output_parser = StrOutputParser()
        self.prompt_template = ChatPromptTemplate.from_template(
            """
            Bạn là chatbot thông minh. Dựa vào những thông tin dưới đây để trả lời chi tiết câu hỏi, nếu không có dữ liệu liên quan đến câu hỏi, hãy trả lời 'Chúng tôi không có thông tin', ngoài ra có thể có 1 số câu hỏi không cần thôn tin dưới, hãy trả lời tự nhiên:
            {context}

            Lịch sử hội thoại:
            {chat_history}

            Hãy trả lời câu hỏi sau: {question}
            """
        )
        self.reranker = FlagReranker('namdp-ptit/ViRanker', use_fp16=True)

        self.chain = self.create_chain(apply_rewrite=apply_rewrite, apply_rerank=apply_rerank)

    def ReRank(self, query_docs):
        """
        Xếp hạng lại các tài liệu dựa trên điểm tương đồng và ngày tháng.
        
        Tham số:
        query_docs (dict): Từ điển chứa truy vấn và danh sách tài liệu.
        
        Trả về:
        list: Danh sách các tài liệu đã xếp hạng lại.
        """
        query = query_docs['query']
        chunks = query_docs['docs']
        top_k = self.num_docs
        scores = self.reranker.compute_score(
            [[query, chunk.page_content] for chunk in chunks],
            normalize=True
        )
        chunk_with_rank = [(chunks[idx], scores[idx]) for idx in range(len(chunks))]
        adjusted_docs = []
        for doc, score in chunk_with_rank:
            date_str = doc.metadata.get("date", "2024-12")
            adjusted_score = apply_date_penalty(score, date_str, self.date_impact)
            adjusted_docs.append((doc, adjusted_score))
        top_chunks = heapq.nlargest(top_k, adjusted_docs, key=lambda x: x[1])
        return [chunk for chunk, score in top_chunks]

    def find_neighbor(self, docs : list[Document]):
        """
        Tìm các tài liệu lân cận dựa trên ID của tài liệu.
        
        Tham số:
        docs (list): Danh sách các tài liệu.
        
        Trả về:
        list: Danh sách các tài liệu đã xử lý.
        """
        processed_docs = []
        for doc in docs:    
            try:
                doc_id = doc.metadata['_id']
                neighbor_ids = [doc_id - 2, doc_id - 1,doc_id, doc_id + 1, doc_id + 2]
                neighbors = self.db.get_by_ids(neighbor_ids)
                if neighbors:
                    neighbors.append(doc)
                    neighbors_sorted = sorted(neighbors, key=lambda x: x.metadata['_id'])
                    doc.page_content = '.'.join([neighbor.page_content for neighbor in neighbors_sorted])
                processed_docs.append(doc)
            except Exception as e:
                print(f"Error processing neighbors for doc {doc_id}: {e}")
                processed_docs.append(doc)
        return processed_docs

    def format_docs(self, docs : list[Document]):
        """
        Định dạng các tài liệu thành chuỗi và lưu các liên kết.
        
        Tham số:
        docs (list): Danh sách các tài liệu.
        
        Trả về:
        str: Chuỗi định dạng của các tài liệu.
        """
        formatted = "\n\n".join(doc.page_content for doc in docs)
        self.extracted_links = []
        for doc in docs:
            if doc.metadata.get("url", None):
                self.extracted_links.append(doc.metadata.get("url", None))
        return formatted

    def ReWrite(self, query):
        """
        Viết lại câu hỏi để rõ ràng và chính xác hơn.
        
        Tham số:
        query (str): Câu hỏi gốc cần viết lại.
        
        Trả về:
        str: Câu hỏi đã viết lại.
        """
        template = f'''
        Bạn đang thực hiện việc rewrite query trong rag. Viết lại câu hỏi dưới đây sao cho rõ ràng, chính xác, và phù hợp với ngữ cảnh tìm kiếm, thêm một số gợi ý. Đảm bảo rằng câu hỏi viết lại vẫn giữ nguyên ý nghĩa của câu hỏi gốc.(chỉ trả về câu hỏi viết lại)

        Câu hỏi gốc: "{query}"

        Câu hỏi'''
        rewrite_query = self.llm.invoke(template)
        print(rewrite_query.content)
        return rewrite_query.content

    def get_chat_history(self):
        """
        Lấy lịch sử hội thoại.
        
        Trả về:
        str: Lịch sử hội thoại dưới dạng chuỗi.
        """
        return '\n'.join(self.memory) if self.memory else ""

    def remove_history_chat(self):
        """
        Xóa lịch sử hội thoại.
        """
        self.memory = []

    def create_chain(self, apply_rewrite: bool = False, apply_rerank: bool = False):
        """
        Tạo chuỗi xử lý câu hỏi với các thành phần cần thiết.
        
        Tham số:
        apply_rewrite (bool): Có áp dụng viết lại hay không.
        apply_rerank (bool): Có áp dụng xếp hạng lại hay không.
        
        Trả về:
        Runnable: Chuỗi xử lý câu hỏi.
        """
        # Bước 1: Lấy retriever_handler từ self.retriever
        retriever_handler = self.retriever
        
        # Bước 2: Kiểm tra xem có áp dụng viết lại không
        if apply_rewrite:
            pre_retriever = self.ReWrite
        else:
            pre_retriever = RunnablePassthrough()
        
        # Bước 3: Kiểm tra xem có áp dụng xếp hạng lại không
        if apply_rerank:
            retriever_handler = RunnableParallel(
                {'docs': retriever_handler, 'query': RunnablePassthrough()}
            )
            retriever_handler = retriever_handler | self.ReRank
        
        # Bước 4: Kết hợp các hàm xử lý
        retriever_handler = retriever_handler | self.find_neighbor | self.format_docs
        
        # Bước 5: Tạo handler cho lịch sử hội thoại
        chat_history_handler = RunnableLambda(lambda x: self.get_chat_history())
        
        # Bước 6: Thiết lập và lấy dữ liệu
        setup_and_retrieval = RunnableParallel(
            {"context": retriever_handler, "question": RunnablePassthrough(), 'chat_history': chat_history_handler}
        )
        
        # Bước 7: Tạo chuỗi xử lý cuối cùng
        chain = pre_retriever | setup_and_retrieval | self.prompt_template | self.llm | self.output_parser

        return chain

    def run(self, question: str):
        """
        Chạy chuỗi hỏi đáp với câu hỏi được cung cấp.
        
        Tham số:
        question (str): Câu hỏi của người dùng.
        
        Trả về:
        tuple: Phản hồi từ chatbot và các liên kết đã trích xuất.
        """
        self.memory.append(f'người dùng: {question}')
        self.extracted_links=[]
        response = self.llm.invoke(
            f"""Xác định xem câu hỏi dưới đây có phải là câu chào hỏi thông thường hay câu hỏi yêu cầu truy vấn thông tin. 
            - Nếu là câu chào hỏi thông thường, trả lời bằng một câu trả lời tự nhiên và thân thiện(chỉ trả về câu chào lại).
            - Nếu câu hỏi yêu cầu truy vấn thông tin, trả lời là '0' (không phải câu chào hỏi).

            Câu hỏi: {question}"""

        ).content
        if str(response).strip() == '0':
            response = self.chain.invoke(question)
        else:
            all_responses=list(response.split('\n'))
            if len(all_responses)>1:
                final_response=[]
                for res in all_responses:
                    if 'chào hỏi' not in res or 'thông thường' not in res:
                        final_response.append(res)
                response='\n'.join(final_response)                
        self.memory.append(f'chatbot: {response}')
        if len(self.memory) > 5:
            self.memory.pop(0)
            self.memory.pop(0)
        return response, self.extracted_links
