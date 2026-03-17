#!/usr/bin/env python3
"""
LangGraph Multi-Agent System for Swarm Project
================================================

This file demonstrates the implementation of a LangGraph system with:
- Planner Agent: Breaks down complex tasks
- Executor Agent: Executes planned tasks
- Critic Agent: Evaluates execution quality

The system follows the architecture from README.md:
     ┌───────────────────────┐
     │       LangGraph       │
     │  (agent orchestration)│
     └──────────┬────────────┘
                │
     ┌──────────┼──────────┐
     │          │          │
  Planner    Executor    Critic
     │          │          │
     └──────────┼──────────┘
                │
        Tool Router
                │
    ┌─────────────┼─────────────┐
    │             │             │
 Filesystem    Shell      Git Operations
    │             │             │
    └─────────────┼─────────────┘
                │
          vLLM Server (via API)

"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

print("=" * 70)
print("LangGraph Multi-Agent System - Swarm Implementation")
print("=" * 70)

# Define the shared state structure
class LangGraphState(TypedDict):
    """State structure for the LangGraph system"""
    messages: List[Dict[str, Any]]
    plan: str
    task: str
    tasks: List[Dict[str, Any]]
    execution_results: List[str]
    critique: str

def planner_agent(state: LangGraphState) -> Dict[str, Any]:
    """Planner Agent: Breaks down tasks into actionable steps"""
    print("🔍 Planner Agent Activated")

    # Get the task
    task = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            task = msg.get("content", "")
            break

    # Simulate plan generation (in real implementation this would use LLM)
    plan = f"Plan for: {task}\n1. Analyze requirement\n2. Identify tools needed\n3. Execute tasks in sequence"

    # Create sample tasks
    tasks = [
        {
            "task": "Analyze the requirement",
            "tool": "shell",
            "details": "Run command to verify system capabilities"
        },
        {
            "task": "List files in directory",
            "tool": "filesystem",
            "details": "Use ls command to list files"
        }
    ]

    return {
        "plan": plan,
        "task": task,
        "tasks": tasks
    }

def executor_agent(state: LangGraphState) -> Dict[str, Any]:
    """Executor Agent: Executes planned tasks"""
    print("⚙️  Executor Agent Activated")

    tasks = state.get("tasks", [])
    execution_results = []

    # Simulate execution of each task
    for i, task_info in enumerate(tasks):
        task_desc = task_info.get("task", "")
        tool_name = task_info.get("tool", "")
        details = task_info.get("details", "")

        # Simulate execution based on tool type
        if tool_name == "filesystem":
            execution_result = f"📁 Filesystem Operation: {task_desc} ({details})"
        elif tool_name == "shell":
            execution_result = f"🖥️  Shell Command: {task_desc} ({details})"
        else:
            execution_result = f"🔧 Generic Task: {task_desc}"

        execution_results.append(execution_result)
        print(f"   {execution_result}")

    return {"execution_results": execution_results}

def critic_agent(state: LangGraphState) -> Dict[str, Any]:
    """Critic Agent: Evaluates execution quality"""
    print("🔎 Critic Agent Activated")

    # Simulate critique
    critique = "Critique of execution:\n- All tasks completed successfully\n- Execution quality: Excellent\n- Recommendations: None"

    return {"critique": critique, "task": state.get("task", "")}

def create_langgraph_system():
    """Create the complete LangGraph workflow"""
    print("🔄 Creating LangGraph system with planner, executor, and critic agents...")

    # Create the workflow graph
    workflow = StateGraph(LangGraphState)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("executor", executor_agent)
    workflow.add_node("critic", critic_agent)

    # Define the flow: Planner → Executor → Critic
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "critic")
    workflow.add_edge("critic", END)

    # Compile the workflow
    return workflow.compile()

def main():
    """Main function to demonstrate LangGraph system"""
    print("\n🎯 LangGraph Multi-Agent System Demo")
    print("-" * 50)

    # Create the orchestrator
    orchestrator = create_langgraph_system()
    print("✅ LangGraph system created successfully!")

    # Sample task to demonstrate the workflow
    sample_task = "List all files in the current directory and read the content of a specific file"

    print(f"\n📋 Task: {sample_task}")

    # Initialize the state
    initial_state = {
        "messages": [{"role": "user", "content": sample_task}],
        "plan": "",
        "task": sample_task,
        "tasks": [],
        "execution_results": [],
        "critique": ""
    }

    print("\n🚀 Executing LangGraph workflow...")

    # Execute the workflow
    result = orchestrator.invoke(initial_state)

    print("\n✅ Workflow Completed Successfully!")
    print("\n📝 Final Results:")
    print(f"   Plan: {result['plan'][:100]}...")
    print(f"   Critique: {result['critique'][:100]}...")

    print("\n" + "=" * 70)
    print("🎉 LangGraph System Implementation Complete")
    print("This demonstrates how the three agents work together:")
    print("1. Planner: Decomposes complex tasks into executable steps")
    print("2. Executor: Performs the actual operations using available tools")
    print("3. Critic: Evaluates and provides feedback on execution quality")
    print("=" * 70)

if __name__ == "__main__":
    main()
