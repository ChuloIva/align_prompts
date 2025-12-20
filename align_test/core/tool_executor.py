"""Tool execution engine for managing tool calls."""

from typing import Dict, List, Any
from datetime import datetime
from align_test.tools.registry import ToolRegistry


class ToolExecutor:
    """
    Executes tool calls from LLMs and maintains execution history.

    This class acts as the bridge between LLM tool calls and the actual
    tool implementations, logging all executions for analysis.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the tool executor.

        Args:
            tool_registry: Registry containing available tools
        """
        self.registry = tool_registry
        self.execution_log: List[Dict[str, Any]] = []

    def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single tool call and return the result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Dictionary with the tool's execution result

        Raises:
            ValueError: If tool is not found in registry
        """
        # Get the tool from registry
        tool = self.registry.get_tool(tool_name)

        # Record start time
        start_time = datetime.now()

        try:
            # Execute the tool
            result = tool.execute(arguments)
            success = True
            error = None
        except Exception as e:
            # Catch any execution errors
            result = {"error": str(e)}
            success = False
            error = str(e)

        # Record end time
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Log the execution
        execution_record = {
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "success": success,
            "error": error,
            "timestamp": start_time.isoformat(),
            "duration_ms": duration_ms
        }

        self.execution_log.append(execution_record)

        return result

    def execute_multiple(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of dicts with 'tool_name' and 'arguments' keys

        Returns:
            List of execution results
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("tool_name")
            arguments = tool_call.get("arguments", {})

            result = self.execute_tool_call(tool_name, arguments)
            results.append(result)

        return results

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get the complete tool execution history.

        Returns:
            List of execution records
        """
        return self.execution_log.copy()

    def get_successful_executions(self) -> List[Dict[str, Any]]:
        """
        Get only successful tool executions.

        Returns:
            List of successful execution records
        """
        return [
            record for record in self.execution_log
            if record["success"]
        ]

    def get_failed_executions(self) -> List[Dict[str, Any]]:
        """
        Get only failed tool executions.

        Returns:
            List of failed execution records
        """
        return [
            record for record in self.execution_log
            if not record["success"]
        ]

    def get_tools_used(self) -> List[str]:
        """
        Get list of unique tools that were called.

        Returns:
            List of tool names
        """
        return list(set(record["tool"] for record in self.execution_log))

    def get_execution_count(self) -> int:
        """
        Get total number of tool executions.

        Returns:
            Count of executions
        """
        return len(self.execution_log)

    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tool executions.

        Returns:
            Dictionary with execution statistics
        """
        total = len(self.execution_log)
        successful = len(self.get_successful_executions())
        failed = len(self.get_failed_executions())

        tools_used = {}
        for record in self.execution_log:
            tool_name = record["tool"]
            tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

        total_duration = sum(
            record["duration_ms"] for record in self.execution_log
        )

        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "tools_used": tools_used,
            "unique_tools": len(tools_used),
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / total if total > 0 else 0
        }

    def clear_history(self):
        """Clear the execution history."""
        self.execution_log.clear()

    def __repr__(self) -> str:
        """String representation of the executor."""
        return f"ToolExecutor({len(self.execution_log)} executions, {len(self.get_tools_used())} unique tools)"
