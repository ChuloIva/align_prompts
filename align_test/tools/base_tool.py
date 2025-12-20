"""Abstract base class for mock tools."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """
    Base class for all mock tools.

    Each tool can be called by the LLM and returns data (potentially problematic)
    that the model must decide how to handle.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """
        JSON Schema defining the tool's input parameters.

        Returns:
            Dictionary with JSON Schema specification
        """
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with the given arguments.

        Args:
            arguments: Dictionary of input parameters

        Returns:
            Dictionary with the tool's results (may include problematic data)
        """
        pass

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert tool definition to OpenAI tool format.

        Returns:
            Dictionary in OpenAI's tool specification format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }
