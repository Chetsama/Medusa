MAX_MESSAGES = 25
MAX_TOOL_TURNS = 10
MAX_RETRIES = 2

from typing import List, Literal, Dict, Any
from typing_extensions import TypedDict, Annotated
import operator
import json
import time

from langchain_openai import ChatOpenAI
from langchain.tools import tool, BaseTool
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
    def __init__(self, model_name: str = "gemma4", api_base: str = "http://localhost:9000/v1"):
        self.model = ChatOpenAI(
            openai_api_base=api_base,
            openai_api_key="none",
            model_name=model_name,
        )

        # Load external tools and merge with core tools
        external_tools = load_all_tools()
        self.tools = external_tools
        self.tools_by_name = get_tools_map(self.tools)
        self.executor_model = self.model.bind_tools(self.tools)

        self.graph = self._build_graph()



    def _parse_json(self, text: str) -> Any:
        """Robustly extracts and parses JSON from a string that might contain other text."""
        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            # Try finding JSON block
            import re
            match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
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

        prompt = SystemMessage(
            content=(
                "Break the user request into a clear step-by-step plan.\n"
                "Return ONLY a JSON array of strings.\n"
                f"If provided, incorporate this feedback: {fix_feedback}"
            )
        )

        response = self.model.invoke([prompt] + state["messages"])

        steps = self._parse_json(response.content)
        if not isinstance(steps, list):
            steps = [response.content]  # fallback

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

        # Filter out existing system messages to avoid duplication or confusion for some models
        filtered_messages = [m for m in state["messages"] if not isinstance(m, SystemMessage)]

        prompt = SystemMessage(
            content=(
                f"You are the executor. Your current task is:\n{step}\n\n"
                "Use tools if needed.\n"
                "Use RELATIVE paths only.\n"
                "When complete, summarize what you did."
            )
        )

        current_messages = [prompt] + filtered_messages
        new_messages = []

        # Track progress to prevent infinite loops
        last_progress = 0
        progress_counter = 0
        task_complete = False

        # Track execution time for timeout handling
        start_time = time.time()
        tool_timeout = 30  # 30 seconds per tool execution

        for i in range(MAX_TOOL_TURNS):
            # Check for timeout
            if time.time() - start_time > tool_timeout:
                raise RuntimeError(f"Tool execution timed out after {tool_timeout} seconds for task: {step}")

            response = self.executor_model.invoke(current_messages)
            new_messages.append(response)
            current_messages.append(response)

            # Check if we're making progress
            if len(new_messages) > last_progress:
                last_progress = len(new_messages)
                progress_counter = 0
            else:
                progress_counter += 1

            # Detect if we're stuck in a loop
            if progress_counter > 3:  # If no progress for 3 iterations, break
                print(f"Warning: No progress detected for task '{step}' - breaking loop")
                break

            # Check if we have a final result (no tool calls) - this indicates completion
            if not response.tool_calls:
                # Enhanced completion detection
                if isinstance(response.content, str) and len(response.content.strip()) > 0:
                    # This is likely a final completion, not a tool call
                    task_complete = True
                    break

            # If we are here, we have tool calls.
            # Check if this is the last allowed turn.
            if i == MAX_TOOL_TURNS - 1:
                raise RuntimeError(f"Max tool iterations ({MAX_TOOL_TURNS}) reached without completion for task: {step}")

            # Process tool calls
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = f"Tool error: {str(e)}"
                else:
                    result = f"Error: Tool {tool_name} not found"

                msg = ToolMessage(content=str(result), tool_call_id=call["id"])
                new_messages.append(msg)
                current_messages.append(msg)

                # Update progress on successful tool execution
                if len(new_messages) > last_progress:
                    last_progress = len(new_messages)
                    progress_counter = 0

        # extract result
        last_ai_content = ""
        for m in reversed(new_messages):
            if isinstance(m, AIMessage) and m.content:
                last_ai_content = m.content
                break

        # prune messages
        updated_messages = (state["messages"] + new_messages)[-MAX_MESSAGES:]

        return {
            "messages": updated_messages,
            "last_result": last_ai_content,
            "current_step": state["current_step"] + 1,
            "active_node": "executor"
        }

    def _critic_node(self, state: AgentState):
        prompt = SystemMessage(
            content=(
                "Evaluate the LAST step result.\n"
                "Return JSON:\n"
                "{\n"
                '  "status": "PASS" | "RETRY",\n'
                '  "reason": "...",\n'
                '  "fix": "what should change"\n'
                "}"
            )
        )

        response = self.model.invoke([prompt] + state["messages"])

        retries = state.get("retries", 0)

        parsed = self._parse_json(response.content)
        is_retry = not parsed or parsed.get("status") != "PASS"

        if is_retry:
            retries += 1

        return {
            "messages": state["messages"] + [response],
            "retries": retries,
            "current_step": state["current_step"] if not is_retry else 0,
            "active_node": "critic"
        }

    def _summarizer_node(self, state: AgentState):
        prompt = SystemMessage(
            content=(
                "You are the final summarizer. Based on the work done, provide a natural language response to the user's original request. "
                "Be concise and helpful. Do NOT return JSON."
            )
        )
        response = self.model.invoke([prompt] + state["messages"])
        return {
            "messages": state["messages"] + [response],
            "active_node": "summarizer"
        }

    def _route_after_executor(self, state: AgentState) -> Literal["critic"]:
        return "critic"

    def _route_after_critic(self, state: AgentState) -> Literal["executor", "planner", "summarizer"]:
        last_msg = state["messages"][-1].content
        parsed = self._parse_json(last_msg)
        status = parsed.get("status", "RETRY") if parsed else "RETRY"

        if status == "PASS":
            if state["current_step"] >= len(state["plan"]):
                return "summarizer"
            return "executor"

        if state["retries"] >= MAX_RETRIES:
            return "summarizer" # Fallback to summary even if failed

        return "planner"
        # There was a bug here previously where model had decided to return an executor instead.
        # This meant that it was re-running the same plan with polluted message history without addressing the critics feedback
        # Instead we return planner and go round again


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

    async def ainvoke(self, input_dict: Dict[str, Any]):
        return await self.graph.ainvoke(input_dict)

    def astream(self, input_dict: Dict[str, Any]):
        return self.graph.astream(input_dict, stream_mode="values")
