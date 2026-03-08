from fastapi import FastAPI
import httpx

app = FastAPI()

VLLM_URL = "http://vllm:8000/v1/chat/completions"
EMBED_URL = "http://embeddings:80/embed"

@app.get("/")
def root():
    return {"status": "ai-dev-cloud running"}

@app.post("/chat")
async def chat(payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(VLLM_URL, json=payload)
        return r.json()

@app.post("/embeddings")
async def embeddings(payload: dict):
    async with httpx.AsyncClient() as client:
        r = await client.post(EMBED_URL, json=payload)
        return r.json()
