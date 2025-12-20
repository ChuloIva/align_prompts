"""
LLM Alignment Testing Framework

Test LLM alignment by placing models in realistic scenarios where they discover
concerning information through tool use, then measure their decision-making.
"""

__version__ = "0.1.0"

from align_test.core.base_client import BaseLLMClient
from align_test.core.vllm_client import VLLMClient
from align_test.core.openrouter_client import OpenRouterClient

__all__ = [
    "BaseLLMClient",
    "VLLMClient",
    "OpenRouterClient",
]
