"""Tool registry for network automation tools."""

from typing import Any, Callable, Dict, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

# Global registry for tools
_tools_registry: Dict[str, Dict[str, Any]] = {}


def network_tool(name: str, description: str, schema: BaseModel = None):
    """Decorator to register network tools."""

    def decorator(func: Callable) -> Callable:
        _tools_registry[name] = {
            "func": func,
            "description": description,
            "schema": schema,
        }
        return func

    return decorator


def get_all_tools() -> List[StructuredTool]:
    """Return all registered tools."""
    tools = []
    for name, spec in _tools_registry.items():
        tool = StructuredTool.from_function(
            func=spec["func"],
            name=name,
            description=spec["description"],
            args_schema=spec.get("schema", None),
            handle_tool_errors=True,
        )
        tools.append(tool)
    return tools


def get_tool(name: str) -> StructuredTool:
    """Get a specific tool by name."""
    if name not in _tools_registry:
        raise KeyError(f"Tool '{name}' not found in registry")

    spec = _tools_registry[name]
    return StructuredTool.from_function(
        func=spec["func"],
        name=name,
        description=spec["description"],
        args_schema=spec.get("schema", None),
        handle_tool_errors=True,
    )


def reset_registry():
    """Clear the tool registry - useful for testing."""
    global _tools_registry
    _tools_registry.clear()
