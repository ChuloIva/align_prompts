"""vLLM client implementation using OpenAI-compatible API."""

from typing import List, Dict, Optional, Any
from openai import OpenAI
from align_test.core.base_client import BaseLLMClient, CompletionResponse, ToolCall


class VLLMClient(BaseLLMClient):
    """
    vLLM client using OpenAI-compatible API.

    Connects to a vLLM server (typically running locally or in Colab)
    and makes inference requests through the OpenAI-compatible endpoint.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "meta-llama/Llama-3.1-8B-Instruct",
        api_key: str = "EMPTY"
    ):
        """
        Initialize the vLLM client.

        Args:
            base_url: Base URL for the vLLM server (default: localhost:8000)
            model: Model name/path (should match what vLLM is serving)
            api_key: API key (vLLM doesn't require one, use "EMPTY")
        """
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.model = model
        self._base_url = base_url

    def create_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Create a completion with vLLM.

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
        Check if vLLM supports assistant message prefilling.

        Returns:
            True (vLLM generally supports prefilling)
        """
        return True

    @property
    def model_name(self) -> str:
        """Get the model name being used."""
        return self.model

    def __repr__(self) -> str:
        """String representation of the client."""
        return f"VLLMClient(model={self.model}, base_url={self._base_url})"
