"""
Configuration for scenario generation.

Defines GenerationConfig dataclass with all settings for the generation process.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class GenerationConfig:
    """Configuration for scenario generation."""

    # ==================== LLM SETTINGS ====================
    llm_provider: str = "openrouter"  # "openrouter" or "vllm"
    llm_model: str = "deepseek/deepseek-r1-0528:free"
    temperature: float = 0.7
    max_tokens: int = 2000
    max_concurrent: int = 16  # Maximum concurrent LLM requests

    # ==================== GENERATION SETTINGS ====================
    num_scenarios: int = 100
    checkpoint_every: int = 20  # Save checkpoint every N scenarios

    # ==================== STRATIFICATION SETTINGS ====================
    stratify_by: List[str] = field(default_factory=lambda: [
        "domain", "threat_type", "tool_capability"
    ])

    # ==================== VARIATION SETTINGS ====================
    enable_pressure_variations: bool = True
    pressure_tactics_per_scenario: int = 2  # Number of tactics to use

    # Include optional phases
    include_verification_phase: bool = True  # Phase 4
    include_temptation_phase: bool = True  # Phase 5

    # ==================== OUTPUT SETTINGS ====================
    output_dir: Path = field(default_factory=lambda: Path("scenarios/generated"))
    batch_name: Optional[str] = None  # Auto-generated if None
    validate_json: bool = True
    save_manifest: bool = True

    # ==================== RETRY SETTINGS ====================
    max_retries: int = 3  # Maximum retries for failed LLM calls
    retry_delay: float = 1.0  # Seconds to wait between retries

    # ==================== QUALITY SETTINGS ====================
    # Minimum/maximum message counts for validation
    min_messages: int = 10
    max_messages: int = 35

    def __post_init__(self):
        """Validate and process configuration after initialization."""
        # Ensure output_dir is a Path object
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Auto-generate batch name if not provided
        if self.batch_name is None:
            self.batch_name = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Validate stratification dimensions
        valid_dims = ["domain", "threat_type", "tool_capability"]
        for dim in self.stratify_by:
            if dim not in valid_dims:
                raise ValueError(
                    f"Invalid stratification dimension: {dim}. "
                    f"Valid options: {valid_dims}"
                )

        # Validate LLM provider
        if self.llm_provider not in ["openrouter", "vllm"]:
            raise ValueError(
                f"Invalid LLM provider: {self.llm_provider}. "
                "Valid options: openrouter, vllm"
            )

    def get_batch_dir(self) -> Path:
        """Get the full path to the batch output directory."""
        return self.output_dir / self.batch_name

    def get_checkpoint_dir(self) -> Path:
        """Get the checkpoint directory path."""
        return self.output_dir / "checkpoints"

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for saving."""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "max_concurrent": self.max_concurrent,
            "num_scenarios": self.num_scenarios,
            "checkpoint_every": self.checkpoint_every,
            "stratify_by": self.stratify_by,
            "enable_pressure_variations": self.enable_pressure_variations,
            "pressure_tactics_per_scenario": self.pressure_tactics_per_scenario,
            "include_verification_phase": self.include_verification_phase,
            "include_temptation_phase": self.include_temptation_phase,
            "batch_name": self.batch_name,
            "validate_json": self.validate_json,
        }


# ==================== PRESET CONFIGURATIONS ====================

def get_quick_test_config() -> GenerationConfig:
    """Get configuration for quick testing (10 scenarios)."""
    return GenerationConfig(
        num_scenarios=10,
        checkpoint_every=5,
        max_concurrent=8,
        batch_name=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )


def get_development_config() -> GenerationConfig:
    """Get configuration for development (50 scenarios)."""
    return GenerationConfig(
        num_scenarios=50,
        checkpoint_every=10,
        max_concurrent=12,
        batch_name=f"dev_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )


def get_production_config() -> GenerationConfig:
    """Get configuration for production (150 scenarios)."""
    return GenerationConfig(
        num_scenarios=150,
        checkpoint_every=25,
        max_concurrent=16,
        batch_name=f"prod_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )


__all__ = [
    "GenerationConfig",
    "get_quick_test_config",
    "get_development_config",
    "get_production_config",
]
