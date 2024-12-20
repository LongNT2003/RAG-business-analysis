from semantic_chunkers import StatisticalChunker
from semantic_router.encoders import HuggingFaceEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
import pandas as pd
from time import sleep
import json

class SemanticChunking:
    def __init__(self, min_token=50, max_token=350, model_name="hiieu/halong_embedding"):
        encoder = HuggingFaceEncoder(name=model_name)
        self.statistic_chunking = StatisticalChunker(
            encoder=encoder,
            min_split_tokens=min_token,
            max_split_tokens=max_token
        )

    def split_documents(self, docs: list[dict]):
        """
        Splits the input documents into smaller chunks and returns them as LangChain Document objects.

        Args:
            docs (list[dict]): List of dictionaries with 'content' and 'link' keys.

        Returns:
            list[Document]: List of LangChain Document objects, each representing a chunk.
        """
        langchain_docs = []
        _id=0
        for doc in docs:
            content = doc["content"]
            link = doc["link"]
            
            # Perform chunking using the StatisticalChunker
            chunks = self.statistic_chunking(docs=[content])
            
            for split in chunks[0]:  # chunks[0] because `self.statistic_chunking` processes a single doc
                split_Document=Document(
                        page_content=split.content,
                        metadata={"link": link}
                    )
                split_Document.id=_id
                _id+=1
                langchain_docs.append(
                    split_Document
                )
        
        return langchain_docs

def read_document_json(path: str) -> dict:
    """
    Reads a JSON file containing documents and returns its content as a dictionary.

    Args:
        path (str): The file path to the JSON file.

    Returns:
        dict: The parsed content of the JSON file.
    """
    try:
        data =pd.read_json(path)
        return data.to_dict(orient='records')
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in file: {path}")

class VectorDBHandler:
    def __init__(self,url : str, api_key: str, model_name="hiieu/halong_embedding", collection_name="cmc_final_db"):
        """
        Initialize the VectorDBHandler class.

        Args:
            url (str): URL of the Qdrant instance.
            api_key (str): API key for authentication.
            model_name (str): Name of the HuggingFace embedding model.
            collection_name (str): Name of the Qdrant collection.
        """
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.client = QdrantClient(url=self.url, api_key=self.api_key)
        
        # Ensure the collection exists
        self._initialize_collection()

    def _initialize_collection(self):
        """
        Ensure the Qdrant collection exists; create if it does not.
        """
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            print(f"Collection '{self.collection_name}' created.")
        else:
            print(f"Collection '{self.collection_name}' already exists.")

    def check_chunk_ids(self):
        """
        Check the current number of points (documents) in the collection.

        Returns:
            int: The next available ID for inserting new documents.
        """
        count = self.client.count(self.collection_name).count
        print(f"Current number of points: {count}")
        return count

    def add_documents(self, chunks: list[Document], max_retries: int = 10, retry_delay: int = 5):
        """
        Add new documents to the Qdrant vector database with synchronization check and retry mechanism.

        Args:
            chunks (list[Document]): List of documents to add.
            max_retries (int): Maximum number of retries in case of failure.
            retry_delay (int): Delay (in seconds) between retries.

        Returns:
            int: Total number of successfully added documents.
        """
        # Get the next available ID
        next_id = self.check_chunk_ids()

        # Synchronization check
        if chunks and chunks[0].id != next_id:
            if chunks[0].id == 0:
                print(f"Detected unsynchronized chunk IDs. Adjusting chunks to start from ID {next_id}.")
                for i, chunk in enumerate(chunks):
                    chunk.id = next_id + chunk.id
            else:
                print("Chunk IDs are synchronized. No adjustments needed.")
        
        # Filter out chunks that already exist in the collection
        remaining_chunks = [chunk for chunk in chunks if chunk.id >= next_id]
        print(f"Initial number of new points to insert: {len(remaining_chunks)}")
        
        total_added = 0
        retries = 0

        while remaining_chunks and retries < max_retries:
            try:
                # Add documents
                vector_store = QdrantVectorStore(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding=self.embeddings,
                )
                vector_store.add_documents(remaining_chunks)
                
                # Update counters
                total_added += len(remaining_chunks)
                print(f"Successfully added {len(remaining_chunks)} documents.")
                
                # Clear remaining chunks (all added successfully)
                remaining_chunks = []
            except Exception as e:
                retries += 1
                print(f"Error adding documents (Attempt {retries}/{max_retries}): {e}")
                
                if retries < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                else:
                    print("Max retries reached. Exiting.")
        
        if remaining_chunks:
            print(f"Failed to add {len(remaining_chunks)} documents after {max_retries} retries.")
        else:
            print(f"All documents added successfully. Total added: {total_added}")
        
        return total_added
    
def list_collections(url , api_key):
    """
    List all collections in the Qdrant instance.

    Returns:
        list: A list of collection names.
    """
    client = QdrantClient(url=url, api_key=api_key)
    collections = client.get_collections()
    print("Available collections:", [col.name for col in collections.collections])
    results=[col.name for col in collections.collections]
    client.close()
    return results

if __name__=='__main__':
    from dotenv import load_dotenv
    import os
    url='https://5d9673e8-d966-4738-adbb-95a5842604ba.europe-west3-0.gcp.cloud.qdrant.io'
    load_dotenv()
    qdrant_key = os.getenv('qdrant_key_old')
    print(list_collections(api_key=qdrant_key, url=url))
    # docs=read_document_json('data/raw/companyA.json')
    # print(docs)
    # splitter=SemanticChunking()
    # chunks=splitter.split_documents(docs)
    # print([ch.metadata for ch in chunks])