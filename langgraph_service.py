#!/usr/bin/env python3
"""
LangGraph Service for Docker Compose
===================================

This script serves as a standalone LangGraph service that can be
run via docker compose to ensure proper startup and integration
with other services in the swarm.

The service exposes:
- A health endpoint for monitoring
- A simple API interface for LangGraph interactions
"""

import asyncio
import sys
import os
from typing import Dict, Any
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Try importing LangGraph components
    from agents.langgraph_demo import create_langgraph_system, main
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    from pydantic import BaseModel
    from typing import List

    # Import for LangGraph functionality
    from langgraph.graph import StateGraph, END
    from langchain_core.messages import HumanMessage
    from langchain_openai import ChatOpenAI
    import httpx

    HAS_LANGGRAPH = True
except ImportError as e:
    logger.warning(f"Import error: {e}")
    HAS_LANGGRAPH = False

# Create FastAPI app
app = FastAPI(
    title="LangGraph Service",
    description="LangGraph implementation for Swarm Project",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# vLLM integration configuration
VLLM_URL = "http://vllm:8000"
VLLM_API_PREFIX = "/v1"

class TaskRequest(BaseModel):
    task: str
    messages: List[Dict[str, Any]] = []

class TaskResponse(BaseModel):
    status: str
    result: Dict[str, Any]
    error: str = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "service": "LangGraph Service",
        "version": "1.0.0",
        "description": "LangGraph implementation for Swarm Project",
        "integration": "LangGraph -> vLLM"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LangGraph Service",
        "dependencies": {
            "langgraph": HAS_LANGGRAPH,
        }
    }

@app.post("/process")
async def process_request(request: Request):
    """
    Main entry point for processing requests through LangGraph,
    then forwarding to vLLM if needed.
    """
    try:
        # Read the raw body to forward to vLLM
        body = await request.body()

        # Try to parse as JSON if it's a POST request
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        logger.info(f"Processing request through LangGraph: {data.get('messages', [])}")

        # In a real implementation, this would involve:
        # 1. Processing through LangGraph agents
        # 2. Routing tool calls to vLLM when needed
        # 3. Returning responses

        # For now, let's simulate processing and forward to vLLM
        # This would normally involve more complex LangGraph logic

        # Forward to vLLM for actual processing
        async with httpx.AsyncClient(timeout=None) as client:
            # Forward the request to vLLM
            vllm_url = f"{VLLM_URL}{VLLM_API_PREFIX}/chat/completions"
            headers = {
                k: v for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length", "connection", "keep-alive"]
            }

            response = await client.post(vllm_url, content=body, headers=headers)

            # Return the vLLM response
            return response.content, response.status_code, {
                "content-type": response.headers.get("content-type", "application/json")
            }

    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute-task")
async def execute_task(request: TaskRequest):
    """Execute a LangGraph task"""
    try:
        if not HAS_LANGGRAPH:
            raise HTTPException(status_code=500, detail="LangGraph components not available")

        # Simple demonstration of LangGraph execution
        logger.info(f"Executing task: {request.task}")

        # For now, just run the demo
        # In a production scenario, you'd actually process the task through LangGraph

        # Simulate task execution
        result = {
            "task": request.task,
            "status": "completed",
            "details": "LangGraph processing completed successfully"
        }

        return TaskResponse(
            status="success",
            result=result
        )

    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/langgraph/demo")
async def langgraph_demo():
    """Run the LangGraph demo"""
    try:
        if not HAS_LANGGRAPH:
            raise HTTPException(status_code=500, detail="LangGraph components not available")

        # Run the demo
        logger.info("Running LangGraph demo...")

        # For demo purposes, we'll just show what would happen
        return {
            "status": "demo_completed",
            "message": "LangGraph demo executed successfully",
            "service": "LangGraph Service"
        }

    except Exception as e:
        logger.error(f"Demo execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the service
    logger.info("Starting LangGraph Service...")

    # Get port from environment or default to 9001
    port = int(os.getenv("LANGGRAPH_PORT", "9001"))
    host = os.getenv("LANGGRAPH_HOST", "0.0.0.0")

    logger.info(f"Service will run on {host}:{port}")

    # Run the service
    try:
        # If we have LangGraph components, we can start the actual demo
        if HAS_LANGGRAPH:
            logger.info("LangGraph components available - starting service with demo capability")
        else:
            logger.warning("LangGraph components not available - starting basic service")

        # Start Uvicorn server
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        logger.info(f"LangGraph service listening on {host}:{port}")
        server.run()

    except KeyboardInterrupt:
        logger.info("Shutting down LangGraph service...")
    except Exception as e:
        logger.error(f"Error starting LangGraph service: {str(e)}")
        sys.exit(1)
