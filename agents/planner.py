from typing import TypedDict, List, Dict, Any
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
    tool_calls: List[Dict[str, Any]]

# Initialize the planner agent with OpenAI model
# For vLLM integration, we'll configure it to support tool calling
planner_llm = ChatOpenAI(
    model="cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit",
    api_key="none",
    base_url="http://vllm:8000",
    max_tokens=5,
    temperature=0,
)

def plan(state: PlannerState) -> Dict[str, Any]:
    """Generate a plan for executing a task with vLLM tool calling support"""
    # Get the latest human message
    task = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            task = msg.get("content", "")
            break

    # Create a prompt to generate a plan with vLLM tool calling support
    plan_prompt = f"""
    You are a planner agent tasked with breaking down complex requests into actionable steps.
    Your primary role is to create a detailed plan that leverages vLLM's tool calling capabilities.

    Analyze the following request and create a detailed plan with:
    1. Clear breakdown of tasks
    2. Identify which tools will be needed (filesystem, shell, git, web_search, etc.)
    3. Logical sequence of operations
    4. Expected outcomes for each step

    Important: When creating your response, structure it for vLLM tool calling integration.

    For vLLM tool calling, ensure your tool calls follow this format:
    {{
        "name": "tool_name",
        "arguments": {{}}
    }}

    Request: {task}

    Format your response as JSON with the following structure:
    {{
        "plan": "Detailed step-by-step plan with vLLM tool calling integration",
        "tasks": [
            {{
                "task": "Specific task description",
                "tool": "Name of tool to use (filesystem, shell, git, web_search)",
                "details": "Additional details for the task",
                "tool_call": {{
                    "name": "tool_name",
                    "arguments": {{}}
                }}
            }}
        ],
        "tool_calls": [
            {{
                "name": "tool_name",
                "arguments": {{}}
            }}
        ]
    }}

    Important: Make sure the response is valid JSON and includes proper tool_call structure for vLLM integration.
    """

    # Generate plan using vLLM integration
    try:
        response = planner_llm.invoke([HumanMessage(content=plan_prompt)])

        # Parse the JSON response
        try:
            plan_data = json.loads(response.content)
            return {
                "plan": plan_data.get("plan", ""),
                "task": task,
                "tasks": plan_data.get("tasks", []),
                "tool_calls": plan_data.get("tool_calls", [])
            }
        except Exception as e:
            # If JSON parsing fails, return the raw content as plan
            return {
                "plan": response.content,
                "task": task,
                "tasks": [],
                "tool_calls": []
            }
    except Exception as e:
        # Fallback if vLLM is not available
        print(f"Warning: Could not connect to vLLM for planning: {str(e)}")
        return {
            "plan": f"Plan for: {task}\n1. Analyze requirement\n2. Identify tools needed\n3. Execute tasks in sequence",
            "task": task,
            "tasks": [
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
            ],
            "tool_calls": []
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

def get_tool_definitions():
    """Define the tools that can be called through vLLM integration"""
    return [
        {
            "type": "function",
            "function": {
                "name": "shell_operation",
                "description": "Execute shell commands",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "filesystem_operation",
                "description": "Perform filesystem operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "Type of filesystem operation (list_files, read_file, write_file)"
                        },
                        "path": {
                            "type": "string",
                            "description": "Path for the operation"
                        }
                    },
                    "required": ["operation", "path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "git_operation",
                "description": "Perform Git operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "Type of Git operation (clone, status, commit, push)"
                        },
                        "repository": {
                            "type": "string",
                            "description": "Repository URL or path"
                        }
                    },
                    "required": ["operation"]
                }
            }
        }
    ]

# Export the functions for use in other modules
__all__ = ['create_planner_graph', 'get_tool_definitions']
