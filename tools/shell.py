import subprocess
import os
from langchain.tools import tool

@tool
def run_shell_command(cmd: str) -> str:
    """
    Executes a bash shell command in the current working directory and returns stdout, stderr, and return code.
    
    Args:
        cmd: The shell command string to execute.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            timeout=30
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        parts = []
        if out:
            parts.append(f"STDOUT:\n{out}")
        if err:
            parts.append(f"STDERR:\n{err}")
        parts.append(f"RETURN CODE: {result.returncode}")
        return "\n".join(parts)

    except subprocess.TimeoutExpired:
        return f"Error: Command '{cmd}' timed out after 30 seconds."
    except Exception as e:
        return f"Error executing shell command: {str(e)}"

