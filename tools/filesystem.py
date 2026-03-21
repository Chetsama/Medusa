from langchain.tools import tool
import os

@tool
def list_files(path: str = ".") -> str:
    """
    Lists files in the given directory path.
    
    Args:
        path: The directory path to list files from. Defaults to current directory.
    """
    print(f"DEBUG: calling list_files with path={path}")
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
    print(f"DEBUG: calling read_file with path={path}")
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
        path: The path of the file to write to.
        content: The text content to write into the file.
    """
    print(f"DEBUG: calling write_file with path={path} and content length {len(content)}")
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"
