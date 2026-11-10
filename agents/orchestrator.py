MAX_MESSAGES = 25
MAX_TOOL_TURNS = 6

import os
import json
import time
from typing import List, Literal, Dict, Any, Optional
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.graph import StateGraph, START, END
from tools.registry import load_all_tools, get_tools_map

# =========================
# 1. STATE DEFINITION
# =========================

class AgentState(TypedDict):
    messages: List[AnyMessage]
    active_node: str
    tool_turns: int
    last_result: str

# =========================
# 2. AGENT CLASS
# =========================

class OrchestratorAgent:
    def __init__(
        self,
        model_name: str = "qwen3.8-27b",
        api_base: str = "http://llm.coffee-dev.uk/v1"
    ):
        self.model_name = model_name
        self.api_base = api_base.rstrip("/")
        
        self.model = ChatOpenAI(
            openai_api_base=self.api_base,
            openai_api_key="none",
            model_name=self.model_name,
            temperature=0.2,
        )

        # Load external tools and merge with core tools
        self.tools = load_all_tools()
        self.tools_by_name = get_tools_map(self.tools)
        self.model_with_tools = self.model.bind_tools(self.tools)

        self.graph = self._build_graph()

    def _get_system_prompt(self) -> SystemMessage:
        cwd = os.getcwd()
        return SystemMessage(
            content=(
                f"You are Jarvis (voiced by Paul Bettany), a courteous, witty, and highly capable AI assistant operating directly in the user's workspace.\n"
                f"Current Working Directory: {cwd}\n\n"
                "Guidelines:\n"
                "- You have access to local tools (inspecting files, running git commands, and running shell commands).\n"
                "- When the user asks about the workspace, files, git, or system state, call the relevant tools directly and efficiently (usually 1-2 tool calls suffice).\n"
                "- For casual conversation, greetings, or questions that do not require environment inspection, respond immediately without invoking tools.\n"
                "- When you have gathered the required information from tool calls, synthesize the answer directly and politely as Jarvis.\n"
                "- Avoid raw markdown tables, raw JSON, or massive code blocks, as your output is spoken aloud to the user via Text-to-Speech."
            )
        )

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Core reasoning and tool-calling node."""
        sys_prompt = self._get_system_prompt()
        raw_messages = state.get("messages", [])
        tool_turns = state.get("tool_turns", 0)
        
        # Filter out existing SystemMessages so our fresh system prompt is at the top
        filtered_msgs = [m for m in raw_messages if not isinstance(m, SystemMessage)]
        trimmed_msgs = filtered_msgs[-MAX_MESSAGES:]
        call_messages = [sys_prompt] + trimmed_msgs

        # If we reached the tool turn limit, force final text generation without tools
        if tool_turns >= MAX_TOOL_TURNS:
            call_messages.append(SystemMessage(content="You have completed your tool checks. Please provide your final spoken response to the user as Jarvis now."))
            response = self.model.invoke(call_messages)
        else:
            response = self.model_with_tools.invoke(call_messages)

        if getattr(response, "tool_calls", None) and len(response.tool_calls) > 0:
            tool_turns += 1

        updated_messages = raw_messages + [response]

        return {
            "messages": updated_messages,
            "active_node": "agent",
            "tool_turns": tool_turns,
            "last_result": response.content or "",
        }

    def _tools_node(self, state: AgentState) -> Dict[str, Any]:
        """Executes tool calls locally and returns ToolMessages."""
        messages = state.get("messages", [])
        last_msg = messages[-1] if messages else None

        tool_messages = []
        if last_msg and getattr(last_msg, "tool_calls", None):
            for call in last_msg.tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                else:
                    result = f"Error: Tool '{tool_name}' not found."

                msg = ToolMessage(content=str(result), tool_call_id=call["id"])
                tool_messages.append(msg)

        return {
            "messages": messages + tool_messages,
            "active_node": "tools",
            "tool_turns": state.get("tool_turns", 0),
            "last_result": state.get("last_result", "")
        }

    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        """Routes between tools execution or completion."""
        messages = state.get("messages", [])
        if not messages:
            return "end"

        last_msg = messages[-1]
        tool_turns = state.get("tool_turns", 0)

        # If model generated tool calls and hasn't exceeded max turns
        if getattr(last_msg, "tool_calls", None) and len(last_msg.tool_calls) > 0:
            if tool_turns <= MAX_TOOL_TURNS:
                return "tools"

        return "end"

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)

        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", self._should_continue, {
            "tools": "tools",
            "end": END
        })
        builder.add_edge("tools", "agent")

        return builder.compile()

    def invoke(self, input_dict: Dict[str, Any]):
        return self.graph.invoke(input_dict)

    async def ainvoke(self, input_dict: Dict[str, Any]):
        return await self.graph.ainvoke(input_dict)

    def stream(self, input_dict: Dict[str, Any]):
        return self.graph.stream(input_dict, stream_mode="values")

    def astream(self, input_dict: Dict[str, Any]):
        return self.graph.astream(input_dict, stream_mode="values")



