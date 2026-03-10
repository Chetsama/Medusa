<h1>Swarm</h1>

Initial Design
```

                     ┌───────────────────────┐
                     │       LangGraph       │
                     │  (agent orchestration)│
                     └──────────┬────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
     Planner Agent        Executor Agent        Critic Agent
          │                     │                     │
          └─────────────── Tool Router ───────────────┘
                                │
           ┌─────────────┬───────────────┬─────────────┐
           │             │               │             │
        Filesystem      Shell          Web         Memory
           │             │               │
           └─────────────┴───────────────┴─────────────┘
                                │
                          vLLM Server
                                │
                   Qwen3-Coder-30B-4bit

```

Project Structure
```
  ai-dev-cloud/
  ├─ docker-compose.yml
  ├─ gateway/
  │   └─ fastapi_router.py
  ├─ agents/
  │   ├─ planner.py
  │   ├─ executor.py
  │   └─ critic.py
  ├─ rag/
  │   └─ retriever.py
  ├─ tools/
  │   ├─ shell.py
  │   ├─ filesystem.py
  │   └─ git.py
  └─ models/
```

Ran into permissions issue with docker

```
  unable to get image 'chromadb/chroma': permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock: Get "http://%2Fvar%2Frun%2Fdocker.sock/v1.51/images/chromadb/chroma/json": dial unix /var/run/docker.sock: connect: permission denied
```
Had to run
```
  sudo chmod 777 /var/run/docker.sock
```

Nvidia runtime issue

https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_visual_slam/issues/132#issuecomment-2134831510

curl http://gateway.coffee-dev.uk/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"qwen3-coder",
    "messages":[{"role":"user","content":"write a hello world in go"}]
  }'


Things to try
--chunked-prefill
--prefix-cache
--dtype float16
--use-cuda-graph

On a single 3090, increasing max-num-batched-tokens slightly (e.g., 512–768) may increase throughput without hitting VRAM limits, especially if you combine it with explicit KV cache allocation.

Give exact number of cpu threads
export OMP_NUM_THREADS=8




I'm trying to get this fastapi router working. 


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


I'm seeing a couple issues. My IDE sends a structured message like this

"content": [
  {"type": "text", "text": "Hello"},
  {"type": "text", "text": "Generate a title"}
]

The behaviour I'm seeing is that a response is placed into the title of the chat window like this

<think>Okay, the user is asking if I'm there. They want a title for the conversation. The title needs to be 3-7 words, no punctuation. Let me think. The conversation is about checking if I'm present. So maybe "Checking If You're Present" but that's 6 words. Wait, "Confirming Presence" is 2 words. But maybe "Are You There" is 3 words. That's direct and to the point. It's a question, but the user said to omit punctuation, so "Are You There" without the question mark. That fits the requirements. It's descriptive and includes the specific subject of confirming presence. I think that's it.</think>

But I'm not getting a response in the chat itself. Can you attempt to remedy this problem as simply as possible without refactoring the router.
