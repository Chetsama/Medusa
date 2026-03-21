from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import json
import uuid
import time
from typing import AsyncGenerator
from agents.orchestrator import OrchestratorAgent
from langchain.messages import HumanMessage, SystemMessage, AIMessage

app = FastAPI()

VLLM_URL = "http://llm.coffee-dev.uk"
agent = OrchestratorAgent(api_base=f"{VLLM_URL}/v1")

@app.get("/")
def root():
    return {"status": "Agentic Gateway is online"}

async def agent_streamer(messages: list) -> AsyncGenerator[str, None]:
    """Streams agent steps as SSE events with a single consolidated <thought> tag."""
    thread_id = str(uuid.uuid4())
    created_time = int(time.time())

    # Initial metadata chunk
    yield f"data: {json.dumps({'id': thread_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': 'agent-orchestrator', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None}]})}\n\n"

    # Open the thought block
    yield f"data: {json.dumps({'id': thread_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': 'agent-orchestrator', 'choices': [{'index': 0, 'delta': {'content': '<thought>\n'}, 'finish_reason': None}]})}\n\n"

    last_thought = ""
    last_state = None

    async for state in agent.astream({"messages": messages, "retries": 0, "active_node": "init"}):
        last_state = state
        active_node = state.get("active_node", "init")
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)

        thought = ""
        if active_node == "init":
            thought = "○ Initializing agent..."
        elif active_node == "planner":
            thought = "○ [planner] Generating execution plan..."
        elif active_node == "executor":
            if plan:
                # In our graph, current_step is incremented after the node finishes.
                # So if we just finished a node, current_step-1 is what just happened.
                step_idx = current_step - 1
                if 0 <= step_idx < len(plan):
                    thought = f"○ [executor] Step {step_idx + 1}/{len(plan)}: {plan[step_idx]}"
                else:
                    thought = f"○ [executor] Moving to next step..."
            else:
                thought = "○ [executor] Executing task..."
        elif active_node == "critic":
            last_msg = state["messages"][-1].content if state.get("messages") else ""
            status = "PASS" if "PASS" in last_msg else "RETRY"
            thought = f"○ [critic] Verification: {status}"
        
        # Stream the thought ONLY if it changed
        if thought and thought != last_thought:
            yield f"data: {json.dumps({'id': thread_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': 'agent-orchestrator', 'choices': [{'index': 0, 'delta': {'content': f'{thought}\n'}, 'finish_reason': None}]})}\n\n"
            last_thought = thought

    # Close the thought block
    yield f"data: {json.dumps({'id': thread_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': 'agent-orchestrator', 'choices': [{'index': 0, 'delta': {'content': '</thought>\n\n'}, 'finish_reason': None}]})}\n\n"

    # Final content from the last state produced by astream
    if last_state:
        final_content = last_state.get("last_result", "")
        if not final_content and last_state.get("messages"):
             final_content = last_state["messages"][-1].content

        if final_content:
            yield f"data: {json.dumps({'id': thread_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': 'agent-orchestrator', 'choices': [{'index': 0, 'delta': {'content': final_content}, 'finish_reason': 'stop'}]})}\n\n"

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
        final_msg = result["messages"][-1].content
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
