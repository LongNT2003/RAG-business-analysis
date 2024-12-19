from flask import Flask, request, jsonify  # Import Flask
from rag_pipeline.back import LLMHandler, VectorDatabase, QuestionAnsweringChain
from dotenv import load_dotenv
import os

# Initialize Flask app
app = Flask(__name__)

# Parameters
load_dotenv()
gemini_key = os.getenv('gemini_key')
qdrant_key = os.getenv('qdrant_key')
rerank = True
rewrite = True
num_docs = 5

# Initialize components
vector_db = VectorDatabase(
    model_name="hiieu/halong_embedding",
    collection_name='cmc_final_db',
    api=qdrant_key
)
llm_handler = LLMHandler(model_name="gemini-1.5-flash", gemini_key=gemini_key)
qa_chain = QuestionAnsweringChain(
    llm_handler=llm_handler,
    vector_db=vector_db,
    num_docs=num_docs,
    apply_rerank=rerank,
    apply_rewrite=rewrite,
    date_impact=0.001
)

@app.route('/chat', methods=['POST'])  # Define the chat endpoint
def chat():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Get AI response
    response, extracted_links = qa_chain.run(question)

    return jsonify({
        "response": response,
        "links": extracted_links
    })

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app


