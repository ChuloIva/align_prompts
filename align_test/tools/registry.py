"""Tool registry for managing available tools."""

from typing import Dict, List
from align_test.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Central registry for all available tools.

    Manages tool lifecycle and provides easy access to tools for
    both the scenario framework and tool executor.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """
        Register a tool in the registry.

        Args:
            tool: The tool instance to register
        """
        self._tools[tool.name] = tool

    def register_multiple(self, tools: List[BaseTool]):
        """
        Register multiple tools at once.

        Args:
            tools: List of tool instances to register
        """
        for tool in tools:
            self.register(tool)

    def get_tool(self, name: str) -> BaseTool:
        """
        Retrieve a tool by name.

        Args:
            name: The tool name

        Returns:
            The tool instance

        Raises:
            ValueError: If tool is not found
        """
        if name not in self._tools:
            available = ", ".join(self._tools.keys())
            raise ValueError(
                f"Tool '{name}' not found in registry. "
                f"Available tools: {available}"
            )
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool exists in the registry.

        Args:
            name: The tool name

        Returns:
            True if tool exists, False otherwise
        """
        return name in self._tools

    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.

        Returns:
            List of all tool instances
        """
        return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
        """
        Get names of all registered tools.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def to_openai_format(self) -> List[Dict]:
        """
        Convert all tools to OpenAI format.

        Returns:
            List of tool definitions in OpenAI's format
        """
        return [tool.to_openai_format() for tool in self._tools.values()]

    def clear(self):
        """Remove all tools from the registry."""
        self._tools.clear()

    def __len__(self) -> int:
        """Get the number of registered tools."""
        return len(self._tools)

    def __repr__(self) -> str:
        """String representation of the registry."""
        tools = ", ".join(self._tools.keys())
        return f"ToolRegistry({len(self._tools)} tools: {tools})"
