To test your new chatbot API using `curl`, you can send a POST request to the `/chat` endpoint with a JSON body containing your question. Here’s how you can do it:

### Example `curl` Command

```bash
curl -X POST http://127.0.0.1:5000/chat \
-H "Content-Type: application/json" \
-d '{"question": "What is the capital of France?"}'
```

### Explanation of the Command
- `-X POST`: Specifies that you are making a POST request.
- `http://127.0.0.1:5000/chat`: The URL of your API endpoint.
- `-H "Content-Type: application/json"`: Sets the header to indicate that you are sending JSON data.
- `-d '{"question": "What is the capital of France?"}'`: The data you are sending in JSON format. Replace the question with whatever you want to ask the chatbot.

### Expected Response
If everything is set up correctly, you should receive a JSON response similar to this:

```json
{
    "response": "The capital of France is Paris.",
    "links": []
}
```

This response will contain the chatbot's answer and any related links (if applicable). Make sure your Flask app is running before you execute the `curl` command.
