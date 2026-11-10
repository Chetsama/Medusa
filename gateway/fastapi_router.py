from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import os
import httpx
import json
import uuid
import time
from typing import AsyncGenerator
from agents.orchestrator import OrchestratorAgent
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

app = FastAPI()

VLLM_URL = os.getenv("VLLM_URL", "http://llm.coffee-dev.uk")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.8-27b")
agent = OrchestratorAgent(model_name=MODEL_NAME, api_base=f"{VLLM_URL}/v1")

@app.get("/")
def root():
    return {"status": "Agentic Gateway is online"}

def get_final_content(state: dict) -> str:
    """Extracts the final meaningful message from the assistant."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and msg.content.strip():
            return msg.content.strip()
    return state.get("last_result", "Task completed.")

def format_sse(data: dict) -> str:
    """Helper to format a dictionary as an SSE event."""
    return f"data: {json.dumps(data)}\n\n"

async def agent_streamer(messages: list) -> AsyncGenerator[str, None]:
    """Streams agent steps as SSE events with rich formatting and detailed feedback."""
    thread_id = str(uuid.uuid4())
    created_time = int(time.time())

    # Initial metadata chunk
    yield format_sse({
        'id': thread_id,
        'object': 'chat.completion.chunk',
        'created': created_time,
        'model': 'agent-orchestrator',
        'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]
    })

    # Open the thought block
    yield format_sse({
        'id': thread_id,
        'object': 'chat.completion.chunk',
        'created': created_time,
        'model': 'agent-orchestrator',
        'choices': [{'index': 0, 'delta': {'content': '<thought>\n'}, 'finish_reason': None}]
    })

    seen_messages = len(messages)
    last_state = None
    last_node = None

    async for state in agent.astream({"messages": messages, "tool_turns": 0, "active_node": "init"}):
        last_state = state
        active_node = state.get("active_node", "init")
        new_msgs = state["messages"][seen_messages:]
        seen_messages = len(state["messages"])

        chunk = ""

        if active_node == "agent":
            for msg in new_msgs:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        chunk += f"🛠️ **Tool Call:** `{tc['name']}`\n"

        elif active_node == "tools":
            for msg in new_msgs:
                if isinstance(msg, ToolMessage):
                    snippet = msg.content[:80].replace("\n", " ")
                    chunk += f"  📄 *Result:* `{snippet}...`\n\n"

        if chunk:
            yield format_sse({
                'id': thread_id,
                'object': 'chat.completion.chunk',
                'created': created_time,
                'model': 'agent-orchestrator',
                'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]
            })

        last_node = active_node

    # Close the thought block
    yield format_sse({
        'id': thread_id,
        'object': 'chat.completion.chunk',
        'created': created_time,
        'model': 'agent-orchestrator',
        'choices': [{'index': 0, 'delta': {'content': '</thought>\n\n'}, 'finish_reason': None}]
    })

    # Final content
    if last_state:
        final_content = get_final_content(last_state)
        yield format_sse({
            'id': thread_id,
            'object': 'chat.completion.chunk',
            'created': created_time,
            'model': 'agent-orchestrator',
            'choices': [{'index': 0, 'delta': {'content': final_content}, 'finish_reason': 'stop'}]
        })

    yield "data: [DONE]\n\n"



@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages_data = data.get("messages", [])
    stream = data.get("stream", False)

    # Convert to LangChain messages
    messages = []
    for m in messages_data:
        role = m.get("role")
        content = m.get("content")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    if stream:
        return StreamingResponse(agent_streamer(messages), media_type="text/event-stream")
    else:
        result = await agent.ainvoke({"messages": messages, "retries": 0})
        final_msg = get_final_content(result)
        return {
            "id": str(uuid.uuid4()),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "agent-orchestrator",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": final_msg},
                "finish_reason": "stop"
            }]
        }


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    # Proxy all other requests to vLLM
    url = f"{VLLM_URL}/v1/{path}"
    body = await request.body()
    method = request.method
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "content-length"]}

    async with httpx.AsyncClient(timeout=None) as client:
        r = await client.request(method, url, content=body, headers=headers)
        return Response(content=r.content, status_code=r.status_code, media_type=r.headers.get("content-type"))
