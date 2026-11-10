from langchain.tools import tool
import os

@tool
def list_files(path: str = ".") -> str:
    """
    Lists files and directories in the given directory path.
    
    Args:
        path: The directory path to list files from. Defaults to current directory ('.').
    """
    try:
        target_path = os.path.abspath(path)
        if not os.path.exists(target_path):
            return f"Error: Directory '{path}' does not exist (resolved: {target_path})."
        if not os.path.isdir(target_path):
            return f"Error: '{path}' is a file, not a directory."

        entries = os.listdir(target_path)
        if not entries:
            return f"Directory '{path}' is empty."

        dirs = []
        files = []
        for name in sorted(entries):
            full = os.path.join(target_path, name)
            if os.path.isdir(full):
                dirs.append(f"[DIR]  {name}/")
            else:
                try:
                    size = os.path.getsize(full)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    files.append(f"[FILE] {name} ({size_str})")
                except Exception:
                    files.append(f"[FILE] {name}")

        result_lines = [f"Contents of '{path}' (resolved: {target_path}):"]
        result_lines.extend(dirs)
        result_lines.extend(files)
        return "\n".join(result_lines)
    except Exception as e:
        return f"Error listing files in '{path}': {str(e)}"

@tool
def read_file(path: str) -> str:
    """
    Reads the contents of a file given its file path.
    
    Args:
        path: The path of the file to read (relative to current directory or absolute).
    """
    try:
        # Simple fix for windows-style absolute paths that might be passed by mistake
        if ":" in path and (path.startswith("C:") or path.startswith("c:")):
            parts = path.split(":", 1)
            path = parts[1].lstrip("\\/")

        target_path = os.path.abspath(path)
        if not os.path.exists(target_path):
            return f"Error: File '{path}' does not exist (resolved: {target_path})."
        if os.path.isdir(target_path):
            return f"Error: '{path}' is a directory, not a file. Use list_files instead."

        with open(target_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()

        # Truncate if extremely large to prevent context window overflow
        max_chars = 15000
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [Truncated: File is {len(content)} characters, showing first {max_chars}]"
        return content
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

@tool
def write_file(path: str, content: str) -> str:
    """
    Writes content to a file at the given path.
    
    Args:
        path: The path of the file to write to (relative or absolute).
        content: The text content to write into the file.
    """
    # Simple fix for windows-style absolute paths that might be passed by mistake
    if ":" in path and (path.startswith("C:") or path.startswith("c:")):
        parts = path.split(":", 1)
        path = parts[1].lstrip("\\/")
    
    abs_path = os.path.abspath(path)
    
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(abs_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as file:
            file.write(content)
        return f"Successfully wrote {len(content)} bytes to {path} (path: {abs_path})"
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"

