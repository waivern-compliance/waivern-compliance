"""Types for analyser configuration and pattern matching.

This module re-exports all types for backward compatibility.
Types are organised into submodules by concern:

- pattern_matching: Pattern matching types and configuration
- llm_validation: LLM validation configuration
- protocols: Schema reader and handler protocols
"""

from waivern_analysers_shared.types.llm_validation import (
    LLMValidationConfig,
)
from waivern_analysers_shared.types.pattern_matching import (
    EvidenceContextSize,
    PatternMatch,
    PatternMatchingConfig,
    PatternMatchResult,
    PatternType,
)
from waivern_analysers_shared.types.protocols import (
    SchemaInputHandler,
    SchemaReader,
)

__all__ = [
    # Pattern matching
    "EvidenceContextSize",
    "PatternMatch",
    "PatternMatchingConfig",
    "PatternMatchResult",
    "PatternType",
    # LLM validation
    "LLMValidationConfig",
    # Protocols
    "SchemaInputHandler",
    "SchemaReader",
]
