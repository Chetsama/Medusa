# Swarm

Currently, 
-The request is sent to http://localhost:9000/v1 in Zed (appending /chat/completions)
-This hits the fastapi router which reaches out to http://vllm:8000
-Tool calls are baked in to vLLM

We are yet to implement...
[issue-002] Model Optimisations
[issue-003] Formal Tool Calling
[issue-004] LangGraph
[issue-005] Multi Agents

## LangGraph Implementation

We have implemented a LangGraph system with three core agents:

### Architecture
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

### Agent Roles

**Planner Agent**: 
- Breaks down complex tasks into actionable steps
- Identifies required tools (filesystem, shell, git)
- Creates detailed execution plans

**Executor Agent**: 
- Executes planned tasks using available tools
- Manages tool operations
- Reports execution results

**Critic Agent**: 
- Evaluates the quality of execution
- Provides feedback and suggestions
- Identifies potential issues and improvements

### Features Implemented

- ✅ Full LangGraph orchestration system
- ✅ Three-agent workflow (planner, executor, critic)
- ✅ State management for agent communication
- ✅ Tool-based execution framework
- ✅ Modular agent design
- ✅ Error handling capabilities

## Project Structure
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

## Setup Instructions

1. Ensure Docker is installed and running
2. Install required Python dependencies:
   ```
   pip install langchain langchain-openai
   ```

3. Run the LangGraph system:
   ```
   python main.py
   ```

## Usage

The LangGraph system processes tasks through a three-stage workflow:
1. **Planning**: The planner breaks down the request into actionable steps
2. **Execution**: The executor carries out the planned operations using available tools
3. **Evaluation**: The critic assesses the quality of execution and provides feedback

## Future Enhancements

- Integration with vLLM for enhanced LLM capabilities
- Expanded toolset for more complex operations
- Enhanced error handling and recovery mechanisms
- Persistent state management for long-running workflows
- Real-time monitoring and logging capabilities