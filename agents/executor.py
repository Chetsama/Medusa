from tools import filesystem, shell, git
import json
import shlex

async def execute(step):
    """
    Executes a given step string or structured tool call.
    Currently handles simple string parsing for compatibility.
    """
    step_lower = step.lower()
    
    try:
        if "list files" in step_lower:
            # Extract path if possible, default to '.'
            parts = step.split()
            path = "." if len(parts) < 3 else parts[-1]
            return {"result": filesystem.list_files(path)}

        if "read file" in step_lower:
            # Extract filename, default to 'README.md'
            parts = step.split()
            filename = "README.md" if len(parts) < 3 else parts[-1]
            return {"result": filesystem.read_file(filename)}

        if "write file" in step_lower:
            # Requires format like: write file <path> <content>
            # This is hard to parse from string, but let's try a simple version
            parts = step.split(maxsplit=2)
            if len(parts) == 3:
                filesystem.write_file(parts[1], parts[2])
                return {"result": f"wrote to {parts[1]}"}
            return {"error": "write file requires path and content"}

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
