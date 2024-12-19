from dotenv import load_dotenv
import os
from FlagEmbedding import FlagReranker
import heapq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document
from datetime import datetime
from qdrant_client import QdrantClient

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
    def __init__(self, model_name: str, collection_name: str, api: str):
        """
        Khởi tạo VectorDatabase với tên mô hình, tên bộ sưu tập và khóa API.
        
        Tham số:
        model_name (str): Tên mô hình cho embeddings.
        collection_name (str): Tên bộ sưu tập trong cơ sở dữ liệu.
        api (str): Khóa API cho Qdrant.
        """
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.collection_name = collection_name
        self.api = api
        self.db = self.load_db()
        
    def load_db(self):
        """
        Tải cơ sở dữ liệu từ Qdrant.
        
        Trả về:
        Qdrant: Đối tượng Qdrant đã khởi tạo.
        """
        client = QdrantClient(
            url="https://5d9673e8-d966-4738-adbb-95a5842604ba.europe-west3-0.gcp.cloud.qdrant.io",
            api_key=self.api
        )
        
        return Qdrant(
            client=client,
            collection_name=self.collection_name,
            embeddings=self.embeddings
        )

    def get_retriever(self, search_kwargs=None):
        """
        Trả về đối tượng retriever từ cơ sở dữ liệu.
        
        Tham số:
        search_kwargs (dict): Tham số tìm kiếm, mặc định là None.
        
        Trả về:
        Retriever: Đối tượng retriever.
        """
        if search_kwargs is None:
            search_kwargs = {}
        return self.db.as_retriever(search_kwargs=search_kwargs)

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
        self.vector_db = vector_db
        
        if apply_rerank:
            search_kwargs = {"k": int(num_docs * 2.5)}
        else:
            search_kwargs = {"k": num_docs}
            
        self.retriever = vector_db.get_retriever(search_kwargs=search_kwargs)
        
        self.extracted_links = []
        self.memory = []
        self.date_impact = date_impact
        self.output_parser = StrOutputParser()
        self.prompt_template = ChatPromptTemplate.from_template(
            """
            Bạn là chatbot thông minh. Dựa vào những thông tin dưới đây để trả lời chi tiết câu hỏi, 
            nếu không có dữ liệu liên quan đến câu hỏi, hãy trả lời 'Chúng tôi không có thông tin', 
            ngoài ra có thể có 1 số câu hỏi không cần thông tin dưới, hãy trả lời tự nhiên:
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
            date_str = doc.metadata.get("date", "2024-11")
            adjusted_score = apply_date_penalty(score, date_str, self.date_impact)
            adjusted_docs.append((doc, adjusted_score))
        top_chunks = heapq.nlargest(top_k, adjusted_docs, key=lambda x: x[1])
        return [chunk for chunk, score in top_chunks]

    def find_neighbor(self, docs):
        """
        Tìm các tài liệu lân cận dựa trên ID của tài liệu.
        
        Tham số:
        docs (list): Danh sách các tài liệu.
        
        Trả về:
        list: Danh sách các tài liệu đã xử lý.
        """
        processed_docs = []
        for doc in docs:
            doc_id = doc.metadata.get('_id', 0)
            neighbor_ids = [doc_id - 2, doc_id - 1, doc_id, doc_id + 1, doc_id + 2]
            try:
                neighbors = [self.vector_db.db.get(id) for id in neighbor_ids if id >= 0]
                neighbors = [n for n in neighbors if n is not None]
                if neighbors:
                    neighbors.append(doc)
                    neighbors_sorted = sorted(neighbors, key=lambda x: x.metadata.get('_id', 0))
                    combined_content = ' '.join([n.page_content for n in neighbors_sorted])
                    doc.page_content = combined_content
                processed_docs.append(doc)
            except Exception as e:
                print(f"Error processing neighbors for doc {doc_id}: {e}")
                processed_docs.append(doc)
        return processed_docs

    def format_docs(self, docs):
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

        Câu hỏi viết lại:
        '''
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
        response = self.chain.invoke(question)

        self.memory.append(f'chatbot: {response}')
        if len(self.memory) > 3:
            self.memory.pop(0)
            self.memory.pop(0)
        return response, self.extracted_links
