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

I'm yet to implement multipl agents but I'd like to get the routing setup to enable this in the future. Can you change the current setup so that we route and ultimately use the executor for our single instance?

[issue-006] Wrong Trousers (DONE)

Using the wrong model


[issue-007] Going in circles
Agents seem to be incapable of writing files, which also makes me wonder whether any of the other tool calls are working correctly

[issue-008] <thought></thought>
It'd be nice to see which agents are actually working. At the moment I just get these messages saying that a thought is occuring. I would like to see which agent is currently working and what they are working on.
