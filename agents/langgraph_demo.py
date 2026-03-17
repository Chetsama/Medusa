"""
LangGraph Multi-Agent System Demo
This demonstrates the core concepts of a multi-agent system using LangGraph.
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import json

# Define the shared state structure
class LangGraphState(TypedDict):
    """State structure for the LangGraph system"""
    messages: List[Dict[str, Any]]
    plan: str
    task: str
    tasks: List[Dict[str, Any]]
    execution_results: List[str]
    critique: str

# Initialize LLM components
planner_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
executor_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
critic_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def planner_agent(state: LangGraphState) -> Dict[str, Any]:
    """Planner Agent: Breaks down tasks into actionable steps"""
    print("🔍 Planner Agent Activated")

    # Extract the task from messages
    task = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            task = msg.get("content", "")
            break

    # Generate a plan using LLM
    plan_prompt = f"""
    You are a Planner Agent tasked with breaking down requests into actionable steps.

    Request: {task}

    Please create a plan with:
    1. Step-by-step breakdown
    2. Tools needed (filesystem, shell, git)
    3. Expected outcomes

    Respond with valid JSON:
    {{
        "plan": "Detailed plan",
        "tasks": [
            {{
                "task": "Specific task description",
                "tool": "tool name",
                "details": "Additional details"
            }}
        ]
    }}
    """

    try:
        response = planner_llm.invoke([HumanMessage(content=plan_prompt)])
        plan_data = json.loads(response.content)

        return {
            "plan": plan_data.get("plan", ""),
            "task": task,
            "tasks": plan_data.get("tasks", [])
        }
    except Exception as e:
        return {
            "plan": f"Generated plan: {response.content}",
            "task": task,
            "tasks": []
        }

def executor_agent(state: LangGraphState) -> Dict[str, Any]:
    """Executor Agent: Executes planned tasks"""
    print("⚙️  Executor Agent Activated")

    tasks = state.get("tasks", [])
    execution_results = []

    for i, task_info in enumerate(tasks):
        task_desc = task_info.get("task", "")
        tool_name = task_info.get("tool", "")
        details = task_info.get("details", "")

        if tool_name == "filesystem":
            execution_result = f"📁 Filesystem: {task_desc}"
        elif tool_name == "shell":
            execution_result = f"🖥️  Shell: {task_desc}"
        elif tool_name == "git":
            execution_result = f"🌱 Git: {task_desc}"
        else:
            execution_result = f"🔧 Task: {task_desc}"

        execution_results.append(execution_result)
        print(f"   {execution_result}")

    return {"execution_results": execution_results}

def critic_agent(state: LangGraphState) -> Dict[str, Any]:
    """Critic Agent: Evaluates execution quality"""
    print("🔎 Critic Agent Activated")

    task = state.get("task", "")
    execution_results = state.get("execution_results", [])

    critique_prompt = f"""
    You are a Critic Agent evaluating execution.

    Task: {task}
    Results: {execution_results}

    Provide evaluation and suggestions.
    """

    try:
        response = critic_llm.invoke([HumanMessage(content=critique_prompt)])
        return {
            "critique": response.content,
            "task": task
        }
    except Exception as e:
        return {
            "critique": f"Critique: {response.content}",
            "task": task
        }

def create_langgraph_system():
    """Create the complete LangGraph workflow"""
    print("🔄 Creating LangGraph system...")

    workflow = StateGraph(LangGraphState)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("executor", executor_agent)
    workflow.add_node("critic", critic_agent)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "critic")
    workflow.add_edge("critic", END)

    return workflow.compile()

def main():
    """Run the LangGraph demo"""
    print("=" * 60)
    print("LangGraph Multi-Agent System Demo")
    print("=" * 60)

    # Create the orchestrator
    orchestrator = create_langgraph_system()
    print("✅ LangGraph system created!")

    # Sample task
    sample_task = "Create a Python script that lists files and reads a specific file"

    # Initialize state
    initial_state = {
        "messages": [{"role": "user", "content": sample_task}],
        "plan": "",
        "task": sample_task,
        "tasks": [],
        "execution_results": [],
        "critique": ""
    }

    print(f"\n📋 Task: {sample_task}")
    print("\n🚀 Executing LangGraph workflow...")

    # Execute workflow
    result = orchestrator.invoke(initial_state)

    print("\n✅ Workflow completed!")
    print(f"\n📋 Plan: {result['plan'][:100]}...")
    print(f"📝 Critique: {result['critique'][:100]}...")

if __name__ == "__main__":
    main()
