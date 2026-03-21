from typing import List, Literal
from typing_extensions import TypedDict, Annotated
import operator

from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
)

from langgraph.graph import StateGraph, START, END


# =========================
# 1. MODEL SETUP
# =========================

model = ChatOpenAI(
    openai_api_base="http://gateway.coffee-dev.uk/v1",
    openai_api_key="none",
    model_name="qwen3-coder",
    )

# =========================
# 2. TOOLS
# =========================

@tool
def add(a: int, b: int) -> int:
    """Add two integers"""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers"""
    return a * b


tools = [add, multiply]
tools_by_name = {t.name: t for t in tools}

executor_model = model.bind_tools(tools)


# =========================
# 3. STATE
# =========================

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    plan: List[str]
    current_step: int
    last_result: str
    retries: int


# =========================
# 4. PLANNER NODE
# =========================

def planner_node(state: AgentState):
    prompt = SystemMessage(
        content=(
            "Break the user request into a clear step-by-step plan.\n"
            "Return ONLY a numbered list.\n"
            "Do NOT call tools."
        )
    )

    response = model.invoke([prompt] + state["messages"])

    # Simple parsing of numbered list
    steps = []
    for line in response.content.split("\n"):
        line = line.strip()
        if line:
            # Remove "1. ", "2. " etc.
            if "." in line:
                line = line.split(".", 1)[1].strip()
            steps.append(line)

    print("\n--- PLAN ---")
    for i, step in enumerate(steps):
        print(f"{i}: {step}")

    return {
        "plan": steps,
        "current_step": 0,
        "messages": [response],
    }


# =========================
# 5. EXECUTOR NODE
# =========================

def executor_node(state: AgentState):
    step = state["plan"][state["current_step"]]

    print(f"\n--- EXECUTING STEP {state['current_step']} ---")
    print(step)

    prompt = SystemMessage(
        content=f"Execute this step. Use tools if needed:\n{step}"
    )

    response = executor_model.invoke(
        [prompt] + state["messages"]
    )

    new_messages = [response]

    # Tool execution
    if response.tool_calls:
        for call in response.tool_calls:
            tool_name = call["name"]
            tool_args = call["args"]

            print(f"Calling tool: {tool_name}({tool_args})")

            tool_fn = tools_by_name[tool_name]
            result = tool_fn.invoke(tool_args)

            print(f"Tool result: {result}")

            new_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=call["id"],
                )
            )

        # Follow-up after tool execution
        follow_up = executor_model.invoke(new_messages)
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


# =========================
# 6. CRITIC NODE
# =========================

def critic_node(state: AgentState):
    print("\n--- CRITIC ---")

    prompt = SystemMessage(
        content=(
            "Evaluate whether the task is fully complete and correct.\n"
            "Respond ONLY with:\n"
            "- PASS\n"
            "- RETRY: <reason>"
        )
    )

    response = model.invoke([prompt] + state["messages"])
    decision = response.content.strip()

    print(f"Critic decision: {decision}")

    if decision.startswith("PASS"):
        return {
            "messages": [response],
            "retries": state["retries"],
        }

    return {
        "messages": [response],
        "retries": state["retries"] + 1,
    }


# =========================
# 7. ROUTING LOGIC
# =========================

MAX_RETRIES = 2

def route_after_executor(state: AgentState) -> Literal["executor", "critic"]:
    if state["current_step"] < len(state["plan"]):
        return "executor"
    return "critic"


def route_after_critic(state: AgentState) -> Literal["executor", "__end__"]:
    last_msg = state["messages"][-1].content

    if last_msg.startswith("PASS"):
        return "__end__"

    if state["retries"] >= MAX_RETRIES:
        print("Max retries reached. Ending.")
        return "__end__"

    print("Retrying execution...")
    return "executor"


# =========================
# 8. BUILD GRAPH
# =========================

def build_agent():
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("critic", critic_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")

    builder.add_conditional_edges(
        "executor",
        route_after_executor,
        ["executor", "critic"],
    )

    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        ["executor", END],
    )

    return builder.compile()


# =========================
# 9. MAIN
# =========================

def main():
    agent = build_agent()

    user_input = "What is (3 + 4) * 5?"

    result = agent.invoke({
        "messages": [HumanMessage(content=user_input)],
        "retries": 0,
    })

    print("\n--- FINAL OUTPUT ---")
    for msg in result["messages"]:
        msg.pretty_print()


if __name__ == "__main__":
    main()
