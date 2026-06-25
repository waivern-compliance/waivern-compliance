"""Configuration types for data collection analyser."""

from typing import Any, Literal, Self, override

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError

SourceCodeContextWindow = Literal["small", "medium", "large", "full"]


class DataCollectionAnalyserConfig(BaseComponentConfiguration):
    """Configuration for DataCollectionAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - Strict validation (no extra fields)

    No LLM validation config — data collection detection is deterministic.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/data_collection/1.0.0"
        ),
        description="Pattern matching configuration for data collection detection",
    )

    source_code_context_window: SourceCodeContextWindow = Field(
        default="small",
        description="Size of source code context window around matches",
    )

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ProcessorConfigError: If validation fails

        """
        return validate_or_raise(cls, properties, ProcessorConfigError)
