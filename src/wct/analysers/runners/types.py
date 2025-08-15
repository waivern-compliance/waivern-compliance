"""Type definitions for analysis runners."""

from dataclasses import dataclass
from typing import Any

from wct.analysers.utilities import EvidenceExtractor


@dataclass
class PatternMatchingRunnerConfig:
    """Configuration for PatternMatchingAnalysisRunner.

    This defines the configuration that the pattern matching runner
    recognizes and uses. Pattern matchers may access additional keys through
    the context dictionary.
    """

    # Required field
    ruleset_name: str
    """Name of the ruleset to use for pattern matching."""

    # Optional fields with defaults
    max_evidence: int = 3
    """Maximum number of evidence snippets per finding (alias for maximum_evidence_count)."""

    maximum_evidence_count: int = 3
    """Maximum number of evidence snippets per finding."""

    context_size: str = "small"
    """Context size for evidence extraction ('small', 'medium', 'large') (alias for evidence_context_size)."""

    evidence_context_size: str = "small"
    """Context size for evidence extraction ('small', 'medium', 'large')."""


@dataclass
class LLMAnalysisRunnerConfig:
    """Configuration for LLMAnalysisRunner.

    This defines the configuration that the LLM analysis runner
    recognizes and uses for validation and processing.
    """

    # LLM validation configuration with defaults
    enable_llm_validation: bool = True
    """Whether to enable LLM validation of findings."""

    llm_batch_size: int = 10
    """Batch size for processing findings through the LLM."""

    llm_validation_mode: str = "standard"
    """Mode for LLM validation ('standard', 'conservative', etc.)."""


@dataclass
class PatternMatcherContext:
    """Strongly typed context object passed to pattern matcher functions.

    This provides a typed interface for all the context information
    that pattern matchers need to access during analysis.
    """

    # Rule information
    rule_name: str
    """Name of the rule being matched."""

    rule_description: str
    """Description of the rule being matched."""

    risk_level: str
    """Risk level from the rule (e.g., 'low', 'medium', 'high')."""

    # Analysis context
    metadata: dict[str, Any]
    """Metadata about the content being analyzed."""

    config: PatternMatchingRunnerConfig
    """Configuration for the pattern matching analysis."""

    # Utilities
    evidence_extractor: EvidenceExtractor
    """Utility for extracting evidence snippets from content."""
