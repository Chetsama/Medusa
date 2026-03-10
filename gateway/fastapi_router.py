from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI()

VLLM_URL = "http://vllm:8000"

@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):

    url = f"{VLLM_URL}/v1/{path}"
    body = await request.body()

    async def stream_response():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                request.method,
                url,
                content=body,
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in ["host", "content-length"]
                },
            ) as r:

                async for chunk in r.aiter_raw():
                    yield chunk

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )
