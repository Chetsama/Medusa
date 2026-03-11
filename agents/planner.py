import httpx
from tools.definitions import TOOL_DEFINITIONS

LLM_ENDPOINT = "http://localhost:9000/v1/chat/completions"

SYSTEM_PROMPT = """
You are a planning agent.
Break user tasks into actionable steps by using the provided tools.
"""

async def plan(task):
    payload = {
        "model": "qwen3-coder",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task}
        ],
        "tools": TOOL_DEFINITIONS,
        "tool_choice": "auto"
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(LLM_ENDPOINT, json=payload)
        return r.json()
