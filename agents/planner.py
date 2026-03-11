import httpx

LLM_ENDPOINT = "http://localhost:8000/v1/chat/completions"

SYSTEM_PROMPT = """
You are a planning agent.
Break user tasks into ordered actionable steps.
Available commands:
- list files <path>
- read file <filename>
- write file <filename> <content>
- run <shell command>
- git status
- git diff

Example:
Task: "Create a hello world file and list the directory"
Steps:
1. write file hello.txt print("hello world")
2. list files .
"""

async def plan(task):
    payload = {
        "model": "qwen3-coder",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task}
        ]
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(LLM_ENDPOINT, json=payload)
        return r.json()
