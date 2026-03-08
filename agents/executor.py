from tools import filesystem, shell

async def execute(step):
    if "list files" in step.lower():
        return filesystem.list_files(".")

    if "read file" in step.lower():
        return filesystem.read_file("README.md")

    if "run" in step.lower():
        return shell.run_command(step)

    return "step not understood"
