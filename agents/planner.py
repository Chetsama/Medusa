from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import json

# Define the state for the planner agent
class PlannerState(TypedDict):
    messages: List[dict]
    plan: str
    task: str
    tasks: List[dict]

# Initialize the planner agent with OpenAI model
planner_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

def plan(state):
    """Generate a plan for executing a task"""
    # Get the latest human message
    task = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            task = msg.get("content", "")
            break

    # Create a prompt to generate a plan
    plan_prompt = f"""
    You are a planner agent tasked with breaking down complex requests into actionable steps.
    Analyze the following request and create a detailed plan:

    Request: {task}

    Please create a step-by-step plan with:
    1. Clear breakdown of tasks
    2. Identify which tools will be needed
    3. Logical sequence of operations
    4. Expected outcomes for each step

    Format your response as JSON with the following structure:
    {{
        "plan": "Detailed step-by-step plan",
        "tasks": [
            {{
                "task": "Specific task description",
                "tool": "Name of tool to use (filesystem, shell, git)",
                "details": "Additional details for the task"
            }}
        ]
    }}

    Important: Make sure the response is valid JSON.
    """

    # Generate plan
    response = planner_llm.invoke([HumanMessage(content=plan_prompt)])

    # Parse the JSON response
    try:
        plan_data = json.loads(response.content)
        return {
            "plan": plan_data.get("plan", ""),
            "task": task,
            "tasks": plan_data.get("tasks", [])
        }
    except Exception as e:
        # If JSON parsing fails, return the raw content as plan
        return {
            "plan": response.content,
            "task": task,
            "tasks": []
        }

# Create the planner graph
def create_planner_graph():
    workflow = StateGraph(PlannerState)

    # Add the plan node
    workflow.add_node("plan", plan)

    # Set the entry point
    workflow.set_entry_point("plan")

    # End the workflow
    workflow.add_edge("plan", END)

    return workflow.compile()
