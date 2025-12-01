"""Base class for network automation tools.

This module provides the NetworkTool abstract base class that defines
the interface for all network automation tools.
"""

from abc import ABC, abstractmethod

from langchain_core.tools import tool
from pydantic import BaseModel


class NetworkTool(ABC):
    """Base class for all network automation tools.

    This abstract class defines the interface that all tools must implement.
    Tools can be registered and discovered through the tool registry.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LangChain.

        Returns:
            Tool name (e.g., "show_command")
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM.

        Returns:
            Human-readable description of what the tool does
        """
        pass

    @property
    @abstractmethod
    def args_schema(self) -> type[BaseModel]:
        """Pydantic schema for tool arguments.

        Returns:
            Pydantic BaseModel class defining tool arguments
        """
        pass

    @abstractmethod
    def _execute_impl(self, **kwargs) -> str:
        """Execute the tool logic (implementation-specific).

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Tool execution result as string
        """
        pass

    def to_langchain_tool(self):
        """Convert to LangChain tool format.

        Returns:
            LangChain tool compatible with LLM binding
        """

        # Create a wrapper function that calls our implementation
        @tool(args_schema=self.args_schema)
        def tool_fn(**kwargs) -> str:
            return self._execute_impl(**kwargs)

        # Set tool metadata
        tool_fn.name = self.name
        tool_fn.description = self.description

        return tool_fn
