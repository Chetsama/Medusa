from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import json
import asyncio
from typing import Dict, Any

app = FastAPI(title="Swarm vLLM Gateway", version="1.0.0")

# Configuration for services
VLLM_URL = "http://vllm:8000"
VLLM_API_PREFIX = "/v1"
LANGGRAPH_URL = "http://langgraph:9001"

@app.get("/")
def root():
    return {
        "status": "I'm ready to help papa",
        "service": "Swarm vLLM Gateway",
        "version": "1.0.0",
        "routing": "gateway -> langgraph -> vLLM"
    }

@app.get("/health")
def health_check():
    """Health check endpoint for the gateway"""
    return {"status": "healthy", "service": "vLLM Gateway"}

@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    """
    Proxy that routes requests through LangGraph first, then to vLLM
    """

    # Read request body
    body = await request.body()
    method = request.method

    # Forward to LangGraph service for processing
    # LangGraph will handle the tool calling and integration with vLLM
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            # Forward the request to the LangGraph service
            langgraph_url = f"{LANGGRAPH_URL}/process"
            response = await client.request(
                method,
                langgraph_url,
                content=body,
                headers=request.headers,
                params=request.query_params
            )

            # If LangGraph handles the request properly, return its response
            if response.status_code == 200:
                # Return the LangGraph response
                return response.content, response.status_code, {
                    "content-type": response.headers.get("content-type", "application/json")
                }

            # If LangGraph cannot handle it, fall back to vLLM
            # This maintains backward compatibility
            target_url = f"{VLLM_URL}{VLLM_API_PREFIX}/{path}"

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

                    # Update body for forwarding
                    body = json.dumps(data).encode()

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # Log error but continue processing
                    print(f"Warning: Could not parse request body: {str(e)}")
                    pass

            # Return response from vLLM
            response = await client.request(method, target_url, content=body, headers=headers)
            return response.content, response.status_code, {
                "content-type": response.headers.get("content-type", "application/json")
            }

        except Exception as e:
            # Fallback to direct vLLM connection if LangGraph is not available
            target_url = f"{VLLM_URL}{VLLM_API_PREFIX}/{path}"
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length", "connection", "keep-alive"]
            }

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
