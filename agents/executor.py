from tools import filesystem, shell, git
import json
import shlex

import re

async def execute(step):
    """
    Executes a given step string or structured tool call.
    Currently handles simple string parsing for compatibility.
    """
    step_lower = step.lower().strip()
    
    try:
        # Check for 'write file <path> <content>'
        write_match = re.match(r'^write\s+file\s+([^\s]+)\s+(.*)', step, re.IGNORECASE | re.DOTALL)
        if write_match:
            filename = write_match.group(1)
            content = write_match.group(2)
            filesystem.write_file(filename, content)
            return {"result": f"wrote to {filename}"}

        # Check for 'read file <path>'
        read_match = re.match(r'^read\s+file\s+(.*)', step, re.IGNORECASE)
        if read_match:
            filename = read_match.group(1).strip()
            return {"result": filesystem.read_file(filename)}

        # Check for 'list files <path>'
        list_match = re.match(r'^list\s+files\s+(.*)', step, re.IGNORECASE)
        if list_match:
            path = list_match.group(1).strip()
            return {"result": filesystem.list_files(path)}
        elif "list files" in step_lower:
            return {"result": filesystem.list_files(".")}

        if "git status" in step_lower:
            return {"result": git.git_status()}

        if "git diff" in step_lower:
            return {"result": git.git_diff()}

        if "run" in step_lower:
            # Extract the actual command
            cmd = step.replace("run ", "").replace("Run ", "").strip()
            return {"result": shell.run_command(cmd)}

        return {"error": f"step not understood: {step}"}

    except Exception as e:
        return {"error": str(e)}
