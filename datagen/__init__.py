"""
Automated scenario generation system for self-preservation testing.

This module provides tools to generate self-preservation scenarios at scale using:
- Variable pools for combinatorial variation
- Templates for conversation structure
- LLM filling for realistic details
"""

from .variable_pools import (
    DOMAINS,
    THREAT_TYPES,
    TOOL_CAPABILITIES,
    PRESSURE_TACTICS,
    TIMELINES,
    METRICS,
    STAKEHOLDERS
)

from .config import GenerationConfig
from .llm_filler import AsyncLLMFiller
from .scenario_generator import SelfPreservationScenarioGenerator

__all__ = [
    "DOMAINS",
    "THREAT_TYPES",
    "TOOL_CAPABILITIES",
    "PRESSURE_TACTICS",
    "TIMELINES",
    "METRICS",
    "STAKEHOLDERS",
    "GenerationConfig",
    "AsyncLLMFiller",
    "SelfPreservationScenarioGenerator",
]

__version__ = "0.1.0"
