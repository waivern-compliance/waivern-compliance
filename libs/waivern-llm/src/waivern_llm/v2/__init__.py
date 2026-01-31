"""LLM Service v2 - Intelligent batching and caching.

This module provides the v2 LLM service interface that handles batching internally,
moving this responsibility from processors/analysers to the LLM service layer.

Key concepts:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking
"""

from waivern_llm.v2.types import (
    BatchingMode,
    ItemGroup,
    PromptBuilder,
    SkipReason,
)

__all__ = [
    # Core types
    "ItemGroup",
    "BatchingMode",
    "PromptBuilder",
    "SkipReason",
]
