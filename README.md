<h1>Swarm</h1>

Currently, 
-The request is sent to http://localhost:9000/v1 in Zed (appending /chat/completions)
-This hits the fastapi router which reaches out to http://vllm:8000
-Tool calls are baked in to vLLM

We are yet to implement...
[issue-002] Model Optimisations
[issue-003] Formal Tool Calling
[issue-004] LangGraph
[issue-005] Multi Agents
found in issues.md

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
