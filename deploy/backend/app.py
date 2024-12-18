from flask import Flask, request, jsonify
from flask_cors import CORS
from rag_pipeline.back import LLMHandler, VectorDatabase, QuestionAnsweringChain
from dotenv import load_dotenv
import os
import logging
import sys

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
qdrant_key = os.getenv('qdrant_key')

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
            api=qdrant_key
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

# Initialize components when module loads
initialize_components()

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