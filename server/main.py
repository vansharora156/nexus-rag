from fastapi import FastAPI

app = FastAPI(title="NexusRAG", description="Production-grade Enterprise RAG System")

@app.get("/")
def read_root():
    return {"message": "NexusRAG API Gateway - Coming in Week 2"}
