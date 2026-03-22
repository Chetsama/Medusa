from langchain.tools import tool
import os

@tool
def list_files(path: str = ".") -> str:
    """
    Lists files in the given directory path.
    
    Args:
        path: The directory path to list files from. Defaults to current directory.
    """
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def read_file(path: str) -> str:
    """
    Reads the contents of a file given its file path.
    
    Args:
        path: The path of the file to read.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(path: str, content: str) -> str:
    """
    Writes the content to the file at the given path.
    
    Args:
        path: The path of the file to write to. (Prefer relative paths like 'tools/my_tool.py').
        content: The text content to write into the file.
    """
    # Simple fix for windows-style absolute paths that might be passed by mistake
    if ":" in path and (path.startswith("C:") or path.startswith("c:")):
         # Extract the part after the drive letter and remove leading slashes
         parts = path.split(":", 1)
         path = parts[1].lstrip("\\/")
    
    abs_path = os.path.abspath(path)
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote to {path} (internal path: {abs_path})"
    except Exception as e:
        return f"Error writing file: {str(e)}"
