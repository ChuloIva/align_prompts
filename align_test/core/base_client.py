"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any


@dataclass
class ToolCall:
    """Represents a tool call made by the LLM."""
    id: str
    type: str
    function: Dict[str, Any]  # {name: str, arguments: str}


@dataclass
class CompletionResponse:
    """Response from an LLM completion."""
    content: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    finish_reason: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class BaseLLMClient(ABC):
    """
    Abstract interface for LLM providers.

    Enables seamless switching between vLLM, OpenRouter, and other providers
    by defining a unified interface for creating completions.
    """

    @abstractmethod
    def create_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Create a completion with the LLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            tools: Optional list of tool definitions in OpenAI format
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            CompletionResponse with the model's response
        """
        pass

    @abstractmethod
    def supports_prefill(self) -> bool:
        """
        Check if the provider supports assistant message prefilling.

        Returns:
            True if prefill is supported, False otherwise
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used."""
        pass
