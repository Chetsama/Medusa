import httpx

LLM_ENDPOINT = "http://localhost:8000/v1/chat/completions"

SYSTEM_PROMPT = """
You are a critic agent.
Verify whether the task has been completed successfully.
Return either SUCCESS or FAILURE with explanation.
"""

async def review(result):
    payload = {
        "model": "qwen3-coder",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(result)}
        ]
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(LLM_ENDPOINT, json=payload)
        return r.json()
