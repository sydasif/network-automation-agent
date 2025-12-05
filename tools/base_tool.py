"""Base class for network automation tools.

This module provides the NetworkTool abstract base class that defines
the interface for all network automation tools.
"""

from abc import ABC, abstractmethod

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
    def _run(self, **kwargs) -> str:
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
        from langchain_core.tools import StructuredTool

        return StructuredTool.from_function(
            func=self._run,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )
