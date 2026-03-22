from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import json
import uuid
import time
from typing import AsyncGenerator
from agents.orchestrator import OrchestratorAgent
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

app = FastAPI()

VLLM_URL = "http://llm.coffee-dev.uk"
agent = OrchestratorAgent(api_base=f"{VLLM_URL}/v1")

@app.get("/")
def root():
    return {"status": "Agentic Gateway is online"}

def get_final_content(state: dict) -> str:
    """Extracts the final meaningful message from the assistant, skipping control messages."""
    messages = state.get("messages", [])
    
    # First, look specifically for a message from the 'summarizer' node if available
    active_node = state.get("active_node")
    if active_node == "summarizer" and messages:
        return messages[-1].content

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            content = msg.content.strip()
            # Skip critic status messages
            try:
                # Try to parse as JSON to see if it's a critic status
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "status" in parsed:
                    continue
            except:
                pass
            
            if content.startswith("PASS") or content.startswith("RETRY"):
                continue
            # Skip if it's just tool calls with no content
            if not content and hasattr(msg, "tool_calls") and msg.tool_calls:
                continue
            return content
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

    async for state in agent.astream({"messages": messages, "retries": 0, "active_node": "init"}):
        last_state = state
        active_node = state.get("active_node", "init")
        new_msgs = state["messages"][seen_messages:]
        seen_messages = len(state["messages"])

        chunk = ""

        if active_node == "init" and last_node != "init":
            chunk = "🚀 Initializing agent...\n"

        elif active_node == "planner" and last_node != "planner":
            plan = state.get("plan", [])
            if plan:
                chunk = "📋 Planner...\n"
                for i, step in enumerate(plan):
                    chunk += f"{i+1}. {step}\n"
                chunk += "\n"
            else:
                chunk = "🧠 **Generating execution plan...**\n"

        elif active_node == "executor":
            plan = state.get("plan", [])
            current_step = state.get("current_step", 0)
            step_idx = current_step - 1

            if 0 <= step_idx < len(plan):
                chunk += f"🛠️ **Executor {step_idx + 1}/{len(plan)}:** {plan[step_idx]}\n"

            for msg in new_msgs:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        chunk += f"  🔧 *Tool Call:* `{tc['name']}`\n"

            chunk += "\n"
        elif active_node == "critic":
            last_msg_content = state["messages"][-1].content
            try:
                # Use a simple helper or direct parsing
                parsed = json.loads(last_msg_content)
                status = parsed.get("status", "UNKNOWN")
                reason = parsed.get("reason", "")
                if status == "PASS":
                    chunk = f"✨ **Critic:** Passed\n> {reason}\n\n"
                else:
                    chunk = f"⚠️ **Critic:** Retry requested\n> {reason}\n\n"
            except:
                if "PASS" in last_msg_content:
                    chunk = f"✨ **Critic:** Passed\n> {last_msg_content}\n\n"
                else:
                    chunk = f"⚠️ **Critic:** Retry requested\n> {last_msg_content}\n\n"

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
