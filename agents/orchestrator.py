from typing import List, Literal, Dict, Any
from typing_extensions import TypedDict, Annotated
import operator
import json

from langchain_openai import ChatOpenAI
from langchain.tools import tool, BaseTool
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
)
from langgraph.graph import StateGraph, START, END
from tools.registry import load_all_tools, get_tools_map

# =========================
# 1. CORE TOOLS
# =========================

@tool
def add(a: int, b: int) -> int:
    """Add two integers"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers"""
    return a * b

# =========================
# 2. STATE DEFINITION
# =========================

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    plan: List[str]
    current_step: int
    last_result: str
    retries: int
    active_node: str

# =========================
# 3. AGENT CLASS
# =========================

class OrchestratorAgent:
    def __init__(self, model_name: str = "qwen3-coder", api_base: str = "http://localhost:9000/v1"):
        self.model = ChatOpenAI(
            openai_api_base=api_base,
            openai_api_key="none",
            model_name=model_name,
        )

        # Load external tools and merge with core tools
        external_tools = load_all_tools()
        self.tools = [add, multiply] + external_tools
        self.tools_by_name = get_tools_map(self.tools)
        self.executor_model = self.model.bind_tools(self.tools)

        self.graph = self._build_graph()

    def _planner_node(self, state: AgentState):
        prompt = SystemMessage(
            content=(
                "Break the user request into a clear step-by-step plan.\n"
                "Return ONLY a numbered list.\n"
                "Do NOT call tools."
            )
        )
        response = self.model.invoke([prompt] + state["messages"])

        steps = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line:
                # Remove common list prefixes like "1. ", "- ", "* "
                if line[0].isdigit() and "." in line[:4]:
                    line = line.split(".", 1)[1].strip()
                elif line.startswith(("- ", "* ")):
                    line = line[2:].strip()
                
                if line: # Only add if there's content after stripping prefix
                    steps.append(line)

        return {
            "plan": steps,
            "current_step": 0,
            "messages": [response],
            "active_node": "planner"
        }

    def _executor_node(self, state: AgentState):
        if state["current_step"] >= len(state["plan"]):
            # If we're here, it means we've executed everything.
            # If the critic sent us back, we might want to restart or just return.
            return {"current_step": state["current_step"], "active_node": "executor"}

        step = state["plan"][state["current_step"]]
        prompt = SystemMessage(
            content=(
                f"You are the executor. Your current task is:\n{step}\n\n"
                "You have access to tools. Use them if necessary to accomplish the task.\n"
                "When writing or reading files, use RELATIVE paths from the project root (e.g., 'tools/new_tool.py').\n"
                "Do NOT use Windows absolute paths (like C:\\...).\n"
                "If the task requires multiple actions (e.g., search then write), you can call tools sequentially.\n"
                "When the task is complete, provide a final summary of what you did."
            )
        )

        current_messages = [prompt] + state["messages"]
        new_messages = []

        # Loop for multiple tool turns
        for _ in range(3): # Limit to 3 rounds of tool calls per step to avoid runaway
            response = self.executor_model.invoke(current_messages)
            new_messages.append(response)
            current_messages.append(response)

            if not response.tool_calls:
                break

            print(f"DEBUG: executor node detected tool calls: {response.tool_calls}")
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name in self.tools_by_name:
                    print(f"DEBUG: calling tool {tool_name} with args {tool_args}")
                    tool_fn = self.tools_by_name[tool_name]
                    result = tool_fn.invoke(tool_args)
                    print(f"DEBUG: tool {tool_name} returned: {str(result)[:100]}...")
                    msg = ToolMessage(content=str(result), tool_call_id=call["id"])
                    new_messages.append(msg)
                    current_messages.append(msg)
                else:
                    print(f"DEBUG: tool {tool_name} not found")
                    msg = ToolMessage(content=f"Error: Tool {tool_name} not found", tool_call_id=call["id"])
                    new_messages.append(msg)
                    current_messages.append(msg)

            # If it's just a tool call, continue the loop for the next turn
            # But if the model gave content alongside tool calls, it might be the final answer (rare)
            # Actually, LangChain's bind_tools models usually call tools then need to be called again.

        return {
            "messages": new_messages,
            "last_result": new_messages[-1].content if new_messages else "No output",
            "current_step": state["current_step"] + 1,
            "active_node": "executor"
        }

    def _critic_node(self, state: AgentState):
        prompt = SystemMessage(
            content=(
                "Evaluate whether the entire task is fully complete and correct based on the history.\n"
                "If anything is missing or incorrect, explain what needs to be fixed.\n"
                "Respond ONLY with:\n"
                "- PASS\n"
                "- RETRY: <reason>"
            )
        )
        response = self.model.invoke([prompt] + state["messages"])

        retries = state.get("retries", 0)
        is_retry = not response.content.startswith("PASS")
        if is_retry:
            retries += 1

        return {
            "messages": [response],
            "retries": retries,
            "current_step": 0 if is_retry else state["current_step"],
            "active_node": "critic"
        }

    def _route_after_executor(self, state: AgentState) -> Literal["executor", "critic"]:
        if state["current_step"] < len(state["plan"]):
            return "executor"
        return "critic"

    def _route_after_critic(self, state: AgentState) -> Literal["executor", "planner", END]:
        last_msg = state["messages"][-1].content
        if last_msg.startswith("PASS") or state["retries"] >= 2:
            return END

        # If we need to retry, go back to planner to potentially revise the plan
        # or reset step to 0 to restart execution.
        # Let's try resetting to 0 and going to executor first.
        # But wait, LangGraph state is immutable, we return the change.
        # If we return to 'executor', it will start from current_step (which is len(plan) if we didn't reset it).
        return "executor"

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("planner", self._planner_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("critic", self._critic_node)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "executor")
        builder.add_conditional_edges("executor", self._route_after_executor, ["executor", "critic"])
        builder.add_conditional_edges("critic", self._route_after_critic, {
            "executor": "executor",
            "planner": "planner",
            END: END
        })

        return builder.compile()

    async def ainvoke(self, input_dict: Dict[str, Any]):
        return await self.graph.ainvoke(input_dict)

    def astream(self, input_dict: Dict[str, Any]):
        return self.graph.astream(input_dict, stream_mode="values")
