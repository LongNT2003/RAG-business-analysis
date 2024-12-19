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
    # Convert date string (MM-YYYY) to a datetime object
    date = datetime.strptime(date_str, "%Y-%m")
    ref_date = datetime.strptime(reference_date, "%Y-%m")
    
    # Calculate months since the reference date
    months_since = abs(date.year - ref_date.year) * 12 + abs(date.month - ref_date.month)
    return months_since
def apply_date_penalty(similarity_score, date_str, weight=0.01):
    # Calculate months since reference date
    months_since = get_months_since_reference(date_str)
    
    # Apply a linear penalty; adjust the weight as needed
    penalty = 1 + weight * months_since
    # Apply penalty (lower similarity scores for older documents)
    adjusted_score = similarity_score / penalty
    return adjusted_score

class LLMHandler:
    def __init__(self, model_name: str, gemini_key: str):
        self.api_key = gemini_key
        self.llm = ChatGoogleGenerativeAI(model=model_name, api_key=self.api_key)
    
    def get_llm(self):
        return self.llm
class VectorDatabase:
    def __init__(self, model_name: str, collection_name: str, api: str):
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.collection_name = collection_name
        self.api = api
        self.db = self.load_db()
        
    def load_db(self):
        # Khởi tạo Qdrant client
        client = QdrantClient(
            url="https://5d9673e8-d966-4738-adbb-95a5842604ba.europe-west3-0.gcp.cloud.qdrant.io",
            api_key=self.api
        )
        
        # Khởi tạo Qdrant vector store
        return Qdrant(
            client=client,
            collection_name=self.collection_name,
            embeddings=self.embeddings
        )

    def get_retriever(self, search_kwargs=None):
        if search_kwargs is None:
            search_kwargs = {}
        return self.db.as_retriever(search_kwargs=search_kwargs)


class QuestionAnsweringChain:
    def __init__(self, llm_handler: LLMHandler, vector_db: VectorDatabase, num_docs: int = 5, 
                 apply_rewrite: bool = False, apply_rerank: bool = False, date_impact: float = 0.01):
        self.num_docs = num_docs
        self.llm = llm_handler.get_llm()
        self.vector_db = vector_db  # Lưu vector_db
        
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
            date_str = doc.metadata.get("date", "2024-11")  # Default date if missing
            adjusted_score = apply_date_penalty(score, date_str, self.date_impact)
            adjusted_docs.append((doc, adjusted_score))
        top_chunks = heapq.nlargest(top_k, adjusted_docs, key=lambda x: x[1])
        return [chunk for chunk, score in top_chunks]

    def find_neighbor(self, docs):
        processed_docs = []
        for doc in docs:
            doc_id = doc.metadata.get('_id', 0)  # Default to 0 if _id not found
            neighbor_ids = [doc_id - 2, doc_id - 1, doc_id, doc_id + 1, doc_id + 2]
            try:
                neighbors = self.vector_db.db.get_by_ids(neighbor_ids)
                if neighbors:
                    neighbors.append(doc)
                    neighbors_sorted = sorted(neighbors, key=lambda x: x.metadata.get('_id', 0))
                    combined_content = ' '.join([n.page_content for n in neighbors_sorted])
                    doc.page_content = combined_content
                processed_docs.append(doc)
            except Exception as e:
                print(f"Error processing neighbors for doc {doc_id}: {e}")
                processed_docs.append(doc)  # Keep original doc if error
        return processed_docs

    def format_docs(self, docs):
        formatted = "\n\n".join(doc.page_content for doc in docs)
        self.extracted_links = []
        for doc in docs:
            if doc.metadata.get("url", None):
                self.extracted_links.append(doc.metadata.get("url", None))
        return formatted

    def ReWrite(self, query):

        template = f'''
        Bạn đang thực hiện việc rewrite query trong rag. Viết lại câu hỏi dưới đây sao cho rõ ràng, chính xác, và phù hợp với ngữ cảnh tìm kiếm, thêm một số gợi ý. Đảm bảo rằng câu hỏi viết lại vẫn giữ nguyên ý nghĩa của câu hỏi gốc.(chỉ trả về câu hỏi viết lại)

        Câu hỏi gốc: "{query}"

        Câu hỏi viết lại:
        '''
        rewrite_query = self.llm.invoke(template)
        print(rewrite_query.content)
        return rewrite_query.content

    def get_chat_history(self):
        return '\n'.join(self.memory) if self.memory else ""
    def remove_history_chat(self):
        self.memory=[]

    def create_chain(self, apply_rewrite: bool = False, apply_rerank: bool = False):
        retriever_handler = self.retriever
        if apply_rewrite:
            pre_retriever = self.ReWrite
        else:
            pre_retriever = RunnablePassthrough()
        if apply_rerank:
            retriever_handler = RunnableParallel(
                {'docs': retriever_handler, 'query': RunnablePassthrough()}
            )
            retriever_handler = retriever_handler | self.ReRank
        retriever_handler = retriever_handler | self.find_neighbor | self.format_docs
        chat_history_handler = RunnableLambda(lambda x: self.get_chat_history())
        setup_and_retrieval = RunnableParallel(
            {"context": retriever_handler, "question": RunnablePassthrough(), 'chat_history': chat_history_handler}
        )
        chain = pre_retriever | setup_and_retrieval | self.prompt_template | self.llm | self.output_parser

        return chain

    def run(self, question: str):

        self.memory.append(f'người dùng: {question}')
        response = self.chain.invoke(question)


        self.memory.append(f'chatbot: {response}')
        if len(self.memory) > 3:
            self.memory.pop(0)
            self.memory.pop(0)
        return response, self.extracted_links
