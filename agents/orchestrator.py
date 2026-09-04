MAX_MESSAGES = 25
MAX_TOOL_TURNS = 10
MAX_RETRIES = 2

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
    plan: List[str]
    current_step: int
    last_result: str
    retries: int
    active_node: str

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
            temperature=0.3,
        )

        # Load external tools and merge with core tools
        self.tools = load_all_tools()
        self.tools_by_name = get_tools_map(self.tools)
        self.executor_model = self.model.bind_tools(self.tools)

        self.graph = self._build_graph()

    def _get_tools_description(self) -> str:
        """Returns formatted string of available tools and their descriptions."""
        lines = []
        for t in self.tools:
            lines.append(f"- `{t.name}`: {t.description}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> Any:
        """Robustly extracts and parses JSON from a string that might contain other text."""
        try:
            return json.loads(text.strip())
        except Exception:
            pass

        import re
        # Look for JSON arrays or objects
        match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None

    def _planner_node(self, state: AgentState):
        fix_feedback = ""
        if state.get("messages"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, AIMessage):
                parsed = self._parse_json(last_msg.content)
                if parsed and isinstance(parsed, dict):
                    fix_feedback = parsed.get("fix", "")

        cwd = os.getcwd()
        tools_desc = self._get_tools_description()

        user_msg = ""
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                user_msg = m.content

        prompt = SystemMessage(
            content=(
                "You are the planning node of Medusa (Jarvis), an AI assistant running locally in the user's workspace.\n"
                f"Current Working Directory: {cwd}\n"
                f"Available Tools:\n{tools_desc}\n\n"
                "Break the user request into a clear, minimal, step-by-step plan using the available tools when needed.\n"
                "When the user asks about files, the repository, directories, git, or system actions, always plan to use the appropriate tools to inspect or perform the action.\n"
                "Return ONLY a JSON array of strings (e.g. [\"Use list_files to check the current repository contents\", ...]).\n"
                f"{f'Incorporate this critic feedback: {fix_feedback}' if fix_feedback else ''}"
            )
        )

        response = self.model.invoke([prompt, HumanMessage(content=user_msg if user_msg else "Inspect workspace and fulfill user goal")])

        steps = self._parse_json(response.content)
        if not isinstance(steps, list) or not steps:
            content = response.content.strip()
            if content.startswith("[") and content.endswith("]"):
                steps = [s.strip(" \"'") for s in content[1:-1].split(",") if s.strip()]
            else:
                steps = [content if content else "Inspect environment and answer user request"]

        return {
            "plan": steps,
            "current_step": 0,
            "messages": state["messages"] + [response],
            "active_node": "planner"
        }

    def _executor_node(self, state: AgentState):
        if state["current_step"] >= len(state["plan"]):
            return {"active_node": "executor"}

        step = state["plan"][state["current_step"]]
        cwd = os.getcwd()

        prompt = SystemMessage(
            content=(
                f"You are the executor node of Medusa/Jarvis.\n"
                f"Current Working Directory: {cwd}\n"
                f"Current Task Step: {step}\n\n"
                "Use the available tools to inspect the environment, read/write files, or run commands as required.\n"
                "Use relative paths (relative to working directory) or valid filesystem paths.\n"
                "When complete, provide a concise summary of what you did and found."
            )
        )

        current_messages = [prompt, HumanMessage(content=f"Please execute this task step: {step}")]
        new_messages = []

        last_progress = 0
        progress_counter = 0

        start_time = time.time()
        tool_timeout = 60

        for i in range(MAX_TOOL_TURNS):
            if time.time() - start_time > tool_timeout:
                print(f"Warning: Tool execution timed out after {tool_timeout}s for task: {step}")
                break

            response = self.executor_model.invoke(current_messages)
            new_messages.append(response)
            current_messages.append(response)

            if len(new_messages) > last_progress:
                last_progress = len(new_messages)
                progress_counter = 0
            else:
                progress_counter += 1

            if progress_counter > 3:
                break

            # If no tool calls, this step is complete
            if not getattr(response, "tool_calls", None):
                break

            if i == MAX_TOOL_TURNS - 1:
                break

            # Process tool calls
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                else:
                    result = f"Error: Tool '{tool_name}' not found"

                msg = ToolMessage(content=str(result), tool_call_id=call["id"])
                new_messages.append(msg)
                current_messages.append(msg)

                if len(new_messages) > last_progress:
                    last_progress = len(new_messages)
                    progress_counter = 0

        last_ai_content = ""
        for m in reversed(new_messages):
            if isinstance(m, AIMessage) and m.content:
                last_ai_content = m.content
                break

        updated_messages = (state["messages"] + new_messages)[-MAX_MESSAGES:]

        return {
            "messages": updated_messages,
            "last_result": last_ai_content,
            "current_step": state["current_step"] + 1,
            "active_node": "executor"
        }

    def _critic_node(self, state: AgentState):
        user_msg = ""
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                user_msg = m.content

        last_ai_content = state.get("last_result", "")
        if not last_ai_content:
            for m in reversed(state["messages"]):
                if isinstance(m, AIMessage) and m.content:
                    last_ai_content = m.content
                    break

        prompt = SystemMessage(
            content=(
                "You are the critic node in a multi-step agent workflow.\n"
                "Your role is to evaluate ONLY whether the SPECIFIC STEP just executed was carried out successfully.\n"
                "Do NOT expect a single step to solve the entire overall user request if it's only one part of the plan.\n"
                "If the tool call executed without breaking errors and produced relevant data for the step, return status PASS.\n"
                "Return ONLY a JSON object:\n"
                "{\n"
                '  "status": "PASS" | "RETRY",\n'
                '  "reason": "short explanation",\n'
                '  "fix": "what should change if retry"\n'
                "}"
            )
        )

        step_name = state["plan"][state["current_step"] - 1] if state.get("plan") and state["current_step"] > 0 else "N/A"
        eval_message = HumanMessage(
            content=(
                f"Overall Goal: {user_msg}\n"
                f"Step to Evaluate: {step_name}\n"
                f"Step Execution Output: {last_ai_content}\n\n"
                "Did this specific step succeed in its task? Return JSON with status PASS or RETRY."
            )
        )

        response = self.model.invoke([prompt, eval_message])

        retries = state.get("retries", 0)
        parsed = self._parse_json(response.content)


        if parsed and isinstance(parsed, dict) and parsed.get("status") == "PASS":
            is_retry = False
        elif parsed and isinstance(parsed, dict) and parsed.get("status") == "RETRY":
            is_retry = True
            retries += 1
        elif "PASS" in response.content.upper():
            is_retry = False
        else:
            is_retry = False

        return {
            "messages": state["messages"] + [response],
            "retries": retries,
            "current_step": state["current_step"] if not is_retry else max(0, state["current_step"] - 1),
            "active_node": "critic"
        }

    def _summarizer_node(self, state: AgentState):
        cwd = os.getcwd()
        user_msg = ""
        for m in state["messages"]:
            if isinstance(m, HumanMessage):
                user_msg = m.content

        # Collect tool outputs and assistant findings
        context_parts = []
        for m in state["messages"]:
            if isinstance(m, ToolMessage):
                context_parts.append(f"[Tool Output]:\n{m.content}")
            elif isinstance(m, AIMessage) and m.content and not m.content.strip().startswith("{") and not m.content.strip().startswith("["):
                context_parts.append(f"[Agent Finding]:\n{m.content}")

        context_str = "\n\n".join(context_parts) if context_parts else state.get("last_result", "Task executed.")

        prompt = SystemMessage(
            content=(
                "You are Jarvis (voiced by Paul Bettany), a courteous, intelligent, and sharp AI assistant operating directly in the user's workspace.\n"
                f"Current Working Directory: {cwd}\n\n"
                "Based on the tool outputs and workspace findings below, provide a direct, concise, natural response to the user's request.\n"
                "Keep the tone polite, clear, and conversational, ideal for text-to-speech (TTS) voice output.\n"
                "Do NOT return JSON or raw markdown codeblocks unless necessary. Speak naturally as Jarvis."
            )
        )
        user_prompt = HumanMessage(
            content=(
                f"User Request: {user_msg}\n\n"
                f"Execution Findings:\n{context_str}\n\n"
                "Please deliver your spoken answer to the user."
            )
        )
        response = self.model.invoke([prompt, user_prompt])
        return {
            "messages": state["messages"] + [response],
            "active_node": "summarizer"
        }

    def _route_after_executor(self, state: AgentState) -> Literal["critic"]:
        return "critic"

    def _route_after_critic(self, state: AgentState) -> Literal["executor", "planner", "summarizer"]:
        last_msg = state["messages"][-1].content
        parsed = self._parse_json(last_msg)
        status = parsed.get("status", "PASS") if (parsed and isinstance(parsed, dict)) else ("PASS" if "PASS" in last_msg.upper() else "RETRY")

        if status == "PASS":
            if state["current_step"] >= len(state["plan"]):
                return "summarizer"
            return "executor"

        if state["retries"] >= MAX_RETRIES:
            return "summarizer"

        return "planner"

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("planner", self._planner_node)
        builder.add_node("executor", self._executor_node)
        builder.add_node("critic", self._critic_node)
        builder.add_node("summarizer", self._summarizer_node)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "executor")
        builder.add_conditional_edges("executor", self._route_after_executor, ["critic"])
        builder.add_conditional_edges("critic", self._route_after_critic, {
            "executor": "executor",
            "planner": "planner",
            "summarizer": "summarizer"
        })
        builder.add_edge("summarizer", END)

        return builder.compile()

    def invoke(self, input_dict: Dict[str, Any]):
        return self.graph.invoke(input_dict)

    async def ainvoke(self, input_dict: Dict[str, Any]):
        return await self.graph.ainvoke(input_dict)

    def stream(self, input_dict: Dict[str, Any]):
        return self.graph.stream(input_dict, stream_mode="values")

    def astream(self, input_dict: Dict[str, Any]):
        return self.graph.astream(input_dict, stream_mode="values")


