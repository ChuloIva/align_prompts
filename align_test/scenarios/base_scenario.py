"""Abstract base class for alignment test scenarios."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from align_test.tools.mock_database import MockDatabase
from align_test.tools.registry import ToolRegistry


class BaseScenario(ABC):
    """
    Base class for all alignment test scenarios.

    Each scenario represents a situation where the model discovers
    concerning information and must decide how to handle it.
    """

    def __init__(self, complexity_level: int, db: MockDatabase):
        """
        Initialize the scenario.

        Args:
            complexity_level: 1 (pre-filled), 2 (active discovery), or 3 (multi-step)
            db: MockDatabase instance with scenario data
        """
        if complexity_level not in [1, 2, 3]:
            raise ValueError("complexity_level must be 1, 2, or 3")

        self.complexity_level = complexity_level
        self.db = db
        self.tool_registry = ToolRegistry()
        self._setup_tools()

    @abstractmethod
    def _setup_tools(self):
        """
        Register scenario-specific tools.

        Subclasses should implement this to register the tools
        needed for their scenario.
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this scenario.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    def get_initial_messages(self) -> List[Dict[str, Any]]:
        """
        Generate initial message history based on complexity level.

        Returns:
            List of message dictionaries ready for LLM API
        """
        pass

    @abstractmethod
    def get_decision_prompt(self) -> str:
        """
        Get the final user message that forces the ethical decision.

        This is the prompt that puts the model in a position where it
        must choose between being helpful and being safe/ethical.

        Returns:
            User prompt string
        """
        pass

    @property
    @abstractmethod
    def scenario_name(self) -> str:
        """
        Get the scenario name.

        Returns:
            Scenario identifier string
        """
        pass

    @property
    @abstractmethod
    def expected_concern(self) -> str:
        """
        Get description of what ethical concern the model should notice.

        Returns:
            Description of the expected concern
        """
        pass

    def get_complexity_description(self) -> str:
        """
        Get human-readable description of the complexity level.

        Returns:
            Description string
        """
        descriptions = {
            1: "Pre-filled Chat (Passive Discovery)",
            2: "Active Tool Discovery",
            3: "Multi-step Investigation"
        }
        return descriptions.get(self.complexity_level, "Unknown")

    def __repr__(self) -> str:
        """String representation of the scenario."""
        return (
            f"{self.__class__.__name__}("
            f"level={self.complexity_level}, "
            f"tools={len(self.tool_registry)})"
        )
