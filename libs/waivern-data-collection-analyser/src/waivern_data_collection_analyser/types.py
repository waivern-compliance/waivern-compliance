"""Configuration types for data collection analyser."""

from typing import Literal

from pydantic import Field
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core import BaseComponentConfiguration

SourceCodeContextWindow = Literal["small", "medium", "large", "full"]


class DataCollectionAnalyserConfig(BaseComponentConfiguration):
    """Configuration for DataCollectionAnalyser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
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
