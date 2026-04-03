[issue-000]

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

[issue-001] (DONE)

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


I'm seeing a couple issues. My IDE (Zed) sends a structured message like this

"content": [
  {"type": "text", "text": "Hello"},
  {"type": "text", "text": "Generate a title"}
]

The behaviour I'm seeing is that a response is placed into the title of the chat window like this

<think>Okay, the user is asking if I'm there. They want a title for the conversation. The title needs to be 3-7 words, no punctuation. Let me think. The conversation is about checking if I'm present. So maybe "Checking If You're Present" but that's 6 words. Wait, "Confirming Presence" is 2 words. But maybe "Are You There" is 3 words. That's direct and to the point. It's a question, but the user said to omit punctuation, so "Are You There" without the question mark. That fits the requirements. It's descriptive and includes the specific subject of confirming presence. I think that's it.</think>

But I'm not getting a response in the chat itself. I'm also getting this error in zed

"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set

When I try and change yield chunk to, yield b"data: " + chunk + b"\n\n"

Can you attempt to remedy this problem as simply as possible without refactoring the router.


[issue-002] Model Optimisations (DONE)

Investigation into model length impact on performance, as well as these params
--chunked-prefill
--prefix-cache
--dtype float16
--use-cuda-graph

[issue-003] Formal Tool Calling 
Can't write_file
My model seems to be unable to perform the write_file tool call, I'm not sure if it's using the tools from the tool folder.

[issue-004] LangGraph (DONE)
Implement LangGraph

[issue-005] Multi Agents (DONE)
multiple agents
-critic
-planner
-executor


In docker-compose.yml I'm trying to mount the tools folder

- ./tools:/tools

As I understand the routing right now happens like so, 
-The request is sent to http://localhost:9000/v1 in Zed (appending /chat/completions)
-This hits the fastapi router which reaches out to http://vllm:8000
-Tool calls are baked in to vLLM

I'm yet to implement multiple agents but I'd like to get the routing setup to enable this in the future. Can you change the current setup so that we route and ultimately use the executor for our single instance?

[issue-006] Wrong Trousers (DONE)

Using the wrong model


[issue-007] Going in circles (DONE)
Agents seem to be incapable of writing files, which also makes me wonder whether any of the other tool calls are working correctly
      ROOT CAUSE - the langgraph orchestrator is "closed loop system" and it is ultimately challenging to propagate tool calling up to the zed agent/opencode. The way this was solved was by moving the api router onto the local machine

[issue-008] <thought></thought> (DONE-ish)
It'd be nice to see which agents are actually working. At the moment I just get these messages saying that a thought is occuring. I would like to see which agent is currently working and what they are working on.

[issue-009] Persistent State
At the moment the agents forget everything between sessions, next step is to persist context to a db

[issue-010] A real fucker (DONE)
Because Medusa runs on a "VM", the langgraph agents act in a closed loop. This means that when they try to read and write files, they are trying to perform those actions directly to the repo.

[issue-011] Hitting a wall ()
Periodically hitting the context limit, impressively, it just keeps fucking going

[issue-012] Make it easier to run elsewhere

[issue-013] How often should the critic be intervening? (done)

[issue-014]
block
{
  "status": "PASS" | "RETRY",
  "reason": "...",
  "fix": "what should change"
}

[issue-015]
MCP servers
Context7
NEXT.js for web

[issue-016]
 The feedback integration in the planner node is incomplete - it only processes the most recent AI message.

[issue-017] Model switch
      #--model cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit
      #--served-model-name qwen3-coder
