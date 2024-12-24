from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline.back import LLMHandler, VectorDatabase, QuestionAnsweringChain
from rag_pipeline.seed_data import read_document_json, SemanticChunking, VectorDBHandler, list_collections
from crawling.webcrawler import auto_crawl
from dotenv import load_dotenv
import os
import logging
import sys
import threading
import json
# Set console output encoding to UTF-8 để khi docker compose nó log ra được port 3000
sys.stdout.reconfigure(encoding='utf-8')

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load environment variables once
load_dotenv()
gemini_key = os.getenv('gemini_key')
qdrant_key = os.getenv('qdrant_key_old')
# new url
url="https://d508995c-b590-4046-a6cb-75dac0ce258d.us-west-2-0.aws.cloud.qdrant.io"
# old url
url='https://5d9673e8-d966-4738-adbb-95a5842604ba.europe-west3-0.gcp.cloud.qdrant.io'
# Global variables for components
vector_db = None
llm_handler = None
qa_chain = None

def initialize_components():
    """Initialize components only once when server starts.
    
    Steps:
    1. Log the initialization process.
    2. Initialize the vector database if it is not already initialized.
    3. Initialize the LLM handler if it is not already initialized.
    4. Initialize the QA chain if it is not already initialized.
    """
    global vector_db, llm_handler, qa_chain
    
    logger.info("🔄 Initializing components...")
    
    # Initialize vector database
    if vector_db is None:
        vector_db = VectorDatabase(
            model_name="hiieu/halong_embedding",
            collection_name='cmc_final_db',
            api=qdrant_key,
            url=url
        )
        logger.info("✅ Vector database initialized")
    
    # Initialize LLM handler
    if llm_handler is None:
        llm_handler = LLMHandler(
            model_name="gemini-1.5-flash", 
            gemini_key=gemini_key
        )
        logger.info("✅ LLM handler initialized")
    
    # Initialize QA chain
    if qa_chain is None:
        qa_chain = QuestionAnsweringChain(
            llm_handler=llm_handler,
            vector_db=vector_db,
            num_docs=5,
            apply_rerank=True,
            apply_rewrite=True,
            date_impact=0.001
        )
        logger.info("✅ QA chain initialized")

def switch_collection(collection_name):
    global vector_db, llm_handler, qa_chain
    vector_db = VectorDatabase(
        model_name="hiieu/halong_embedding",
        collection_name=collection_name,
        api=qdrant_key,
        url=url
    )
    logger.info(f"✅ Vector database initialized with collection: {collection_name}")
    qa_chain = QuestionAnsweringChain(
        llm_handler=llm_handler,
        vector_db=vector_db,
        num_docs=5,
        apply_rerank=True,
        apply_rewrite=True,
        date_impact=0.001
    )
    logger.info(f"✅ QA chain initialized with collection: {collection_name}")
# Initialize components when module loads
initialize_components()

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the RAG Business Analysis API!"})

@app.route('/crawl', methods=['POST'])
def crawl():
    try:
        # Parse the request JSON for the URL and company name
        data = request.get_json()
        if not data or 'url' not in data or 'company_name' not in data:
            return jsonify({"error": "URL and company name are required"}), 400

        max_links = int(data['max_links']) if 'max_links' in data else 10
        url = data['url']
        company_name = data['company_name']

        # Log the request for debugging purposes
        logger.info(f"Crawling initiated for URL: {url}, company: {company_name}, max_links: {max_links}")

        # Immediately respond with 200 OK
        response_message = {"message": "Crawl request received and processing."}
        flask_response = jsonify(response_message)
        flask_response.status_code = 200

        # Use threading to perform the crawl in the background
        def background_crawl():
            try:
                total_links, total_chars = auto_crawl(start_url=url, depth=5, max_links=max_links)
                logger.info(f"Crawling completed. Total links: {total_links}, Total characters: {total_chars}")
            except Exception as e:
                logger.error(f"Error during background crawl: {str(e)}")

        # Start background thread
        threading.Thread(target=background_crawl).start()

        return flask_response

    except Exception as e:
        # Log and return error if something goes wrong
        logger.error(f"Error during crawl setup: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/crawl_status', methods=['GET'])
def check_status():
    """Endpoint to check the status of the crawling process."""
    STATUS_FILE = r"data\raw\status.json"
    if not os.path.exists(STATUS_FILE):
        return jsonify({"error": "Status file not found. Crawling process has not started."}), 404

    try:
        # Read the status file
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        status_text = "\n".join([f"{key}: {value}" for key, value in status_data.items()])
        
        return status_text, 200  # Send as plain text
    except Exception as e:
        return jsonify({"error": f"Failed to read status file: {str(e)}"}), 500
@app.route('/save_db', methods=['POST'])
def save_db():
    data = request.json
    collection_name = data.get('company_name')
    logger.info(f"Saving data to collection name: {collection_name}")
    try:
        # Step 1: Read documents from raw data folder
        docs = read_document_json('data/raw/outputs.json')

        # Step 2: Perform semantic chunking
        splitter = SemanticChunking()
        chunks = splitter.split_documents(docs)
        logger.info(f"Successesfully spllit data to chunk!")
        # Step 3: Initialize VectorDBHandler and insert chunks into database
        vector_db_handler = VectorDBHandler(url=url,api_key=qdrant_key,collection_name=collection_name)
        vector_db_handler.add_documents(chunks)

        # Return success message
        return jsonify({"message": "Database saved successfully!"}), 200

    except Exception as e:
        # Return error message if something goes wrong
        return jsonify({"error": str(e)}), 500

@app.route('/get_collections', methods = ['GET'])
def get_collections():
    logger.info('get available collections!')
    collections=list_collections(url=url,api_key=qdrant_key)
    return jsonify({'collections': collections}), 200


@app.route('/change_collection', methods=['POST'])
def change_collection():
    try:
        # Parse the request JSON for the collection name
        data = request.get_json()
        if not data or 'collection_name' not in data:
            return jsonify({"error": "Collection name is required"}), 400

        collection_name = data['collection_name']
        logger.info(f"Changing active collection to: {collection_name}")

        switch_collection(collection_name)
        return jsonify({"message": f"Active collection changed to {collection_name}"}), 200

    except Exception as e:
        logger.error(f"Error changing collection: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/send_message', methods=['POST'])
def chat():
    """Handle chat messages from users.
    
    Steps:
    1. Get the JSON data from the request.
    2. Extract the question from the data.
    3. Log the received question.
    4. Check if the question is provided; if not, log a warning and return an error response.
    5. Process the question using the QA chain and log the processing status.
    6. Return the response and extracted links in JSON format.
    """
    data = request.json
    question = data.get('question')
    
    logger.info(f"Received question: {question}")  # Log the received question

    if not question:
        logger.warning("No question provided in the request")  # Log warning for missing question
        return jsonify({"error": "No question provided"}), 400

    try:
        logger.info("Processing question...")  # Log before processing
        response, extracted_links = qa_chain.run(question)
        logger.info("Question processed successfully")  # Log successful processing
        logger.info(f"Response: {response}")
        logger.info(f"Extracted links: {extracted_links}")
        return jsonify({
            "response": response,
            "links": extracted_links
        })
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")  # Log the error
        return jsonify({"error": "Internal server error"}), 500




@app.route('/health', methods=['GET'])
def health_check():
    """Check the health of the application.
    
    Steps:
    1. Return a JSON response indicating the status of the application.
    """
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    logger.info("🚀 Starting Flask application...")
    # Set debug=False to prevent reloading
    app.run(host='0.0.0.0', port=3000, debug=False)