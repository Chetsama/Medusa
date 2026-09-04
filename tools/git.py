import subprocess
import os
from langchain.tools import tool

@tool
def git_status() -> str:
    """Returns the git status of the current working directory."""
    try:
        result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=15
        )
        if result.returncode != 0:
            return f"git status error (code {result.returncode}): {result.stderr.strip()}"
        return result.stdout.strip() if result.stdout.strip() else "Working tree clean, nothing to commit."
    except Exception as e:
        return f"Error running git status: {str(e)}"

@tool
def git_diff() -> str:
    """Returns the git diff (unstaged changes) in the current working directory."""
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=15
        )
        if result.returncode != 0:
            return f"git diff error (code {result.returncode}): {result.stderr.strip()}"
        return result.stdout.strip() if result.stdout.strip() else "No unstaged git changes."
    except Exception as e:
        return f"Error running git diff: {str(e)}"

