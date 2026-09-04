import importlib
import inspect
import os
import sys
from typing import Dict, List, Optional
from langchain.tools import BaseTool

def get_tools_from_module(module_name: str) -> List[BaseTool]:
    """Dynamically imports a module and extracts all functions decorated with @tool."""
    tools = []
    try:
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module):
            if hasattr(obj, "name") and hasattr(obj, "description") and isinstance(obj, BaseTool):
                tools.append(obj)
    except Exception as e:
        print(f"Error loading tools from {module_name}: {e}")
    return tools

def load_all_tools(tools_dir: Optional[str] = None) -> List[BaseTool]:
    """Scans the tools directory and loads all decorated tools."""
    if tools_dir is None:
        tools_dir = os.path.dirname(os.path.abspath(__file__))

    # Ensure Medusa root is in sys.path
    repo_root = os.path.dirname(os.path.abspath(tools_dir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    all_tools = []
    for entry in os.scandir(tools_dir):
        if entry.is_file() and entry.name.endswith(".py") and entry.name not in ("__init__.py", "registry.py"):
            mod_name = f"tools.{entry.name[:-3]}"
            all_tools.extend(get_tools_from_module(mod_name))
    return all_tools

def get_tools_map(tools: List[BaseTool]) -> Dict[str, BaseTool]:
    """Returns a dictionary mapping tool names to tool objects."""
    return {t.name: t for t in tools}

