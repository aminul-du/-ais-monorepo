from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ShorbornoAI Engine")

class AIRequest(BaseModel):
    prompt: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-engine"}

@app.post("/api/ai/analyze")
def analyze(req: AIRequest):
    # Placeholder for actual LLM logic
    return {"status": "success", "response": f"AI Processed: {req.prompt}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
