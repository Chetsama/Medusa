from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
import httpx
import json
import asyncio
from typing import Dict, Any

app = FastAPI(title="Swarm vLLM Gateway", version="1.0.0")

# Configuration for vLLM service
VLLM_URL = "http://vllm:8000"
VLLM_API_PREFIX = "/v1"

@app.get("/")
def root():
    return {
        "status": "I'm ready to help papa",
        "service": "Swarm vLLM Gateway",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for the gateway"""
    return {"status": "healthy", "service": "vLLM Gateway"}

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    """
    Enhanced proxy for vLLM integration that handles tool calling and
    streaming responses properly.
    """

    # Build target URL
    target_url = f"{VLLM_URL}{VLLM_API_PREFIX}/{path}"

    # Read request body
    body = await request.body()
    method = request.method

    # Prepare headers
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "content-length", "connection", "keep-alive"]
    }

    # Handle POST requests with special vLLM processing
    if method == "POST":
        try:
            # Parse JSON data
            data = json.loads(body) if body else {}

            # Process structured content for vLLM compatibility
            if "messages" in data:
                for msg in data["messages"]:
                    if isinstance(msg.get("content"), list):
                        # Convert structured content to text format expected by vLLM
                        text_content = "\n".join([
                            c.get("text", "") for c in msg["content"]
                            if isinstance(c, dict) and c.get("type") == "text"
                        ])
                        msg["content"] = text_content

            # Preserve tool-related information for vLLM tool calling
            # This allows proper integration with vLLM's tool calling functionality
            if "tools" in data and "tool_choice" in data:
                # Pass through tool definitions and choice for vLLM to handle
                pass

            # Update body for forwarding
            body = json.dumps(data).encode()

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Log error but continue processing
            print(f"Warning: Could not parse request body: {str(e)}")
            pass

    async def stream_response():
        """Handle streaming responses from vLLM"""
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                async with client.stream(method, target_url, content=body, headers=headers) as response:
                    if response.status_code != 200:
                        error_content = await response.aread()
                        yield error_content
                        return

                    # Handle streaming responses properly
                    in_think_block = False
                    async for chunk in response.aiter_bytes():
                        # Filter out think blocks for cleaner streaming
                        chunk_str = chunk.decode('utf-8', errors='ignore')

                        # Check for think blocks
                        if "<tool_call>" in chunk_str:
                            in_think_block = True
                            # Remove think blocks from the stream
                            if "<tool_call>" in chunk_str:
                                parts = chunk_str.split("<tool_call>")
                                filtered_chunk = "".join(parts[::2])  # Keep even-indexed parts
                                if filtered_chunk:
                                    yield filtered_chunk.encode()
                                in_think_block = False
                            else:
                                # Partial think block - skip until closing
                                continue
                        elif in_think_block:
                            # Skip content inside think blocks
                            continue
                        else:
                            yield chunk

            except Exception as e:
                error_msg = {"error": f"Proxy error: {str(e)}"}
                yield json.dumps(error_msg).encode()

    # Check if this is a streaming response (common for chat completions)
    is_stream = False
    try:
        if method == "POST":
            data = json.loads(body) if body else {}
            is_stream = data.get("stream", False)
    except Exception:
        pass

    # Return appropriate response based on streaming vs non-streaming
    if is_stream:
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    else:
        # For non-streaming requests, get full response
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.request(method, target_url, content=body, headers=headers)
            return response.content, response.status_code, {
                "content-type": response.headers.get("content-type", "application/json")
            }

# Additional endpoints for managing the vLLM integration
@app.get("/v1/models")
async def list_models():
    """Get available models from vLLM"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{VLLM_URL}{VLLM_API_PREFIX}/models")
            return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch models: {str(e)}"}

@app.post("/v1/reset")
async def reset_gateway():
    """Reset the gateway configuration"""
    return {"status": "Gateway reset successful"}

# Error handler for unhandled routes
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"}
    )
