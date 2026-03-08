import httpx

EMBED_ENDPOINT = "http://localhost:8080/embed"
CHROMA_ENDPOINT = "http://localhost:8001/api/v1"

async def embed(text):
    async with httpx.AsyncClient() as client:
        r = await client.post(EMBED_ENDPOINT, json={"inputs": text})
        return r.json()

async def retrieve(query):
    vector = await embed(query)

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{CHROMA_ENDPOINT}/query",
            json={"query_embeddings": [vector], "n_results": 5}
        )
        return r.json()
