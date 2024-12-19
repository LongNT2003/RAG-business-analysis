```python
def run(self, question):
# 1. Query Vector DB (3-5s)
docs = self.retriever.get_relevant_documents(question)

# 2. Find Neighbors (5-7s) - Đang gây chậm
docs = self.find_neighbor(docs)

# 3. Reranking (3-5s)
if self.apply_rerank:
docs = self.ReRank({"query": question, "docs": docs})

# 4. LLM Processing (3-5s)
response = self.chain.invoke(question)
```
------
tốc độ phản hồi bot đang khoảng bao nhiêu đó Long, tôi run thử thì 10-20 s.