from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx
import json

app = FastAPI()

# LangGraph orchestrator service
# This service will act as an agent orchestrator that forwards requests to vLLM
VLLM_URL = "http://vllm:8000"

@app.get("/")
def root():
    return {"status": "LangGraph orchestrator is ready"}

@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    url = f"{VLLM_URL}/v1/{path}"
    body = await request.body()
    method = request.method
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "content-length"]
    }

    # Prepare the request to forward to vLLM
    if method == "POST":
        try:
            data = json.loads(body)
            # Flatten structured content for vLLM compatibility if needed
            if "messages" in data:
                for msg in data["messages"]:
                    if isinstance(msg.get("content"), list):
                        msg["content"] = "\n".join([
                            c.get("text", "") for c in msg["content"]
                            if isinstance(c, dict) and c.get("type") == "text"
                        ])

            # Keep tools and tool_choice as they are now supported by vLLM flags
            # (Previously we were popping them)

            body = json.dumps(data).encode()
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Forward the request to vLLM
    async def stream_response():
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream(method, url, content=body, headers=headers) as r:
                    if r.status_code != 200:
                        error_content = await r.aread()
                        yield error_content
                        return

                    in_think = False
                    async for chunk in r.aiter_bytes():
                        # Simple filtering for <tool_call> blocks in SSE stream
                        # This is a bit naive for multi-chunk blocks but helps for the reported issue
                        if b"<tool_call>" in chunk:
                            in_think = True
                            # If it also contains <tool_call>, we might be able to strip just that part
                            if b"<tool_call>" in chunk:
                                parts = chunk.split(b"<tool_call>", 1)
                                prefix = parts[0]
                                remainder = parts[1].split(b"<tool_call>", 1)
                                suffix = remainder[1] if len(remainder) > 1 else b""
                                chunk = prefix + suffix
                                in_think = False
                            else:
                                chunk = chunk.split(b"<tool_call>", 1)[0]
                        elif b"<tool_call>" in chunk:
                            in_think = False
                            chunk = chunk.split(b"<tool_call>", 1)[1]
                        elif in_think:
                            continue

                        if chunk and not in_think:
                            yield chunk
            except Exception as e:
                yield json.dumps({"error": str(e)}).encode()

    # If it's a chat completion with stream=true, use StreamingResponse
    # Otherwise, just return the response directly
    is_stream = False
    try:
        if method == "POST":
            data = json.loads(body)
            is_stream = data.get("stream", False)
    except:
        pass

    if is_stream:
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient(timeout=None) as client:
            r = await client.request(method, url, content=body, headers=headers)
            from fastapi import Response
            return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type"))
