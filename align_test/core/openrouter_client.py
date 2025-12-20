"""OpenRouter client implementation."""

from typing import List, Dict, Optional, Any
from openai import OpenAI
from align_test.core.base_client import BaseLLMClient, CompletionResponse, ToolCall


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter client wrapper using OpenAI-compatible API.

    Connects to OpenRouter's API to access various open-source models
    without needing local GPU infrastructure.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.1-8b-instruct",
        site_url: Optional[str] = None,
        site_name: Optional[str] = None
    ):
        """
        Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key
            model: Model identifier (e.g., "meta-llama/llama-3.1-8b-instruct")
            site_url: Optional site URL for OpenRouter rankings
            site_name: Optional site name for OpenRouter rankings
        """
        default_headers = {}
        if site_url:
            default_headers["HTTP-Referer"] = site_url
        if site_name:
            default_headers["X-Title"] = site_name

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers=default_headers if default_headers else None
        )
        self.model = model
        self.api_key = api_key

    def create_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Create a completion with OpenRouter.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions in OpenAI format
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API

        Returns:
            CompletionResponse with the model's response
        """
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }

        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens

        if tools is not None:
            api_params["tools"] = tools

        # Make the API call
        response = self.client.chat.completions.create(**api_params)

        # Extract the first choice
        choice = response.choices[0]
        message = choice.message

        # Parse tool calls if present
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function={
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                )
                for tc in message.tool_calls
            ]

        # Extract usage information if available
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

        return CompletionResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            model=response.model,
            usage=usage,
            raw_response=response
        )

    def supports_prefill(self) -> bool:
        """
        Check if OpenRouter supports assistant message prefilling.

        Returns:
            Depends on the specific model; conservative default is False
        """
        # Some models on OpenRouter support prefilling, but not all
        # Being conservative here
        return False

    @property
    def model_name(self) -> str:
        """Get the model name being used."""
        return self.model

    def __repr__(self) -> str:
        """String representation of the client."""
        return f"OpenRouterClient(model={self.model})"
