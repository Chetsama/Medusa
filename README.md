<h1>Swarm</h1>

Welcome to a multi agent workflow.

Config


<h2>Setup</h2>

From the root directory, run docker compose up. This will spin up vLLM, hosted at http://vllm:8000

And then run
pip install fastapi uvicorn httpx langchain-openai langgraph langchain && uvicorn gateway.fastapi_router:app --host 0.0.0.0 --port 9000

Currently, 
-The request is sent to http://localhost:9000/v1 in Zed (appending /chat/completions)
-This will reach out to the fastapi router, create the agent orchestrator and then begin the agentic workflow with each agent reaching to http://vllm:8000



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
  swarm/
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

Python Venv stuff
```  
  python3 -m venv .venv
  source .venv/bin/activate
  
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


Test Prompt
Can you please write a program to multiply to matrices together in polyml?
~44 tokens/s
I asked it to read the docker compose
106.5 tokens/second



Here is how the traffic flow works now:

   1. Entry: Your chat client sends a request to http://gateway.coffee-dev.uk/v1/chat/completions.
   2. Internal Translation: This reaches your VM and is handled by the fastapi_router (listening on port 9000).
   3. Interception: Instead of just passing the bytes to vLLM, the fastapi_router now recognizes the /v1/chat/completions path and hands the request to the OrchestratorAgent.
   4. Agent Logic (The "Brain"):
       * The agent begins its Planner -> Executor -> Critic cycle.
       * Crucially, when the agent needs to "think" (i.e., ask the LLM to generate a plan or a response), it sends its own internal requests directly to http://vllm:8000/v1.
       * This is the key fix: By pointing the agent at the vLLM backend directly, we avoid a recursive loop where the agent would have tried to call itself.
   5. Tool Execution: If the plan requires a tool (like list_files or run_shell_command), the agent executes it locally on the VM.
   6. Response: Once the critic node is satisfied, the final result is streamed back to you via the gateway, complete with the <thought> tags for visibility.

  Verification of Implementation:
   * In gateway/fastapi_router.py, I defined VLLM_URL = "http://vllm:8000".
   * I initialized the agent with agent = OrchestratorAgent(api_base=f"{VLLM_URL}/v1").
   * This ensures the "agentic" logic sits in the middle (at port 9000) but talks to the "raw" model (at port 8000) for its internal reasoning.

  All other endpoints (like /v1/models) are still handled by the proxy function and passed directly to vLLM, so your setup remains fully compatible with existing tools.
