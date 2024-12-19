# # Empty file to make rag_pipeline a package 

# [+] Running 3/3
#  ✔ Network deploy_app-network   Created                                                                                                                              0.1s 
#  ✔ Container deploy-backend-1   Created                                                                                                                              0.1s 
#  ✔ Container deploy-frontend-1  Created                                                                                                                              0.2s 
# Attaching to backend-1, frontend-1
# backend-1   | Traceback (most recent call last):
# backend-1   |   File "/app/app.py", line 3, in <module>
# backend-1   |     from rag_pipeline.back import LLMHandler, VectorDatabase, QuestionAnsweringChain
# backend-1   | ModuleNotFoundError: No module named 'rag_pipeline'                                                                                                         
# backend-1 exited with code 1
# frontend-1  | 
# frontend-1  | > chatbot@1.0.0 start
# frontend-1  | > http-server . -p 5000 --cors -c-1                                                                                                                         
# frontend-1  |                                                                                                                                                             
# frontend-1  | Starting up http-server, serving .
# frontend-1  | Available on:
# frontend-1  |   http://127.0.0.1:5000                                                                                                                                     
# frontend-1  |   http://172.18.0.3:5000                                                                                                                                    
# frontend-1  | Hit CTRL-C to stop the server
# frontend-1  | [2024-12-19T14:02:29.385Z]  "GET /" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
# frontend-1  | (node:18) [DEP0066] DeprecationWarning: OutgoingMessage.prototype._headers is deprecated
# frontend-1  | (Use `node --trace-deprecation ...` to show where the warning was created)                                                                                  
# frontend-1  | [2024-12-19T14:02:29.458Z]  "GET /style.css" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
# frontend-1  | [2024-12-19T14:02:29.656Z]  "GET /ic_close.png" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
# frontend-1  | [2024-12-19T14:02:29.658Z]  "GET /ic_ai.png" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"                                                                                                                                                          
# frontend-1  | [2024-12-19T14:02:29.661Z]  "GET /script.js" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"                                                                                                                                                          
# frontend-1  | [2024-12-19T14:02:29.664Z]  "GET /ic_send.png" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"                                                                                                                                                        
# frontend-1  | [2024-12-19T14:02:29.679Z]  "GET /config.js" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"                                                                                                                                                          
# frontend-1  | [2024-12-19T14:02:31.377Z]  "GET /favicon.ico" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
# frontend-1  | [2024-12-19T14:02:31.380Z]  "GET /favicon.ico" Error (404): "Not found"
# frontend-1  | [2024-12-19T14:03:01.857Z]  "GET /style.css" "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"


# v View in Docker Desktop   o View Config   w Enable Watch