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

# =========================
# 3. AGENT CLASS
# =========================

class OrchestratorAgent:
    def __init__(self, model_name: str = "qwen3-coder", api_base: str = "http://gateway.coffee-dev.uk/v1"):
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
                if "." in line:
                    line = line.split(".", 1)[1].strip()
                steps.append(line)

        return {
            "plan": steps,
            "current_step": 0,
            "messages": [response],
        }

    def _executor_node(self, state: AgentState):
        if state["current_step"] >= len(state["plan"]):
            return {"current_step": state["current_step"]}

        step = state["plan"][state["current_step"]]
        prompt = SystemMessage(content=f"Execute this step. Use tools if needed:\n{step}")

        response = self.executor_model.invoke([prompt] + state["messages"])
        new_messages = [response]

        if response.tool_calls:
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name in self.tools_by_name:
                    tool_fn = self.tools_by_name[tool_name]
                    result = tool_fn.invoke(tool_args)
                    new_messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
                else:
                    new_messages.append(ToolMessage(content=f"Error: Tool {tool_name} not found", tool_call_id=call["id"]))

            # Follow-up after tool execution
            follow_up = self.executor_model.invoke(state["messages"] + new_messages)
            new_messages.append(follow_up)

            return {
                "messages": new_messages,
                "last_result": follow_up.content,
                "current_step": state["current_step"] + 1,
            }

        return {
            "messages": new_messages,
            "last_result": response.content,
            "current_step": state["current_step"] + 1,
        }

    def _critic_node(self, state: AgentState):
        prompt = SystemMessage(
            content=(
                "Evaluate whether the task is fully complete and correct.\n"
                "Respond ONLY with:\n"
                "- PASS\n"
                "- RETRY: <reason>"
            )
        )
        response = self.model.invoke([prompt] + state["messages"])
        
        # Check if we should increment retries
        retries = state.get("retries", 0)
        if not response.content.startswith("PASS"):
            retries += 1
            
        return {
            "messages": [response],
            "retries": retries,
        }

    def _route_after_executor(self, state: AgentState) -> Literal["executor", "critic"]:
        if state["current_step"] < len(state["plan"]):
            return "executor"
        return "critic"

    def _route_after_critic(self, state: AgentState) -> Literal["executor", END]:
        last_msg = state["messages"][-1].content
        if last_msg.startswith("PASS") or state["retries"] >= 2:
            return END
        return "executor"

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("planner", self._planner_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("critic", self._critic_node)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "executor")
        builder.add_conditional_edges("executor", self._route_after_executor, ["executor", "critic"])
        builder.add_conditional_edges("critic", self._route_after_critic, ["executor", END])

        return builder.compile()

    async def ainvoke(self, input_dict: Dict[str, Any]):
        return await self.graph.ainvoke(input_dict)

    def astream(self, input_dict: Dict[str, Any]):
        return self.graph.astream(input_dict, stream_mode="values")
