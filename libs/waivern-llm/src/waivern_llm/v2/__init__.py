"""LLM Service v2 - Intelligent batching and caching.

This module provides the v2 LLM service interface that handles batching internally,
moving this responsibility from processors/analysers to the LLM service layer.

Key concepts:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking
"""

from waivern_llm.v2.batch_planner import (
    BatchPlan,
    BatchPlanner,
    PlannedBatch,
    SkippedGroup,
)
from waivern_llm.v2.token_estimation import (
    OUTPUT_RATIO,
    PROMPT_OVERHEAD_TOKENS,
    SAFETY_BUFFER,
    TOKENS_PER_FINDING,
    calculate_max_payload_tokens,
    estimate_tokens,
    get_model_context_window,
)
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
    # Batch planning
    "BatchPlanner",
    "BatchPlan",
    "PlannedBatch",
    "SkippedGroup",
    # Token estimation
    "estimate_tokens",
    "get_model_context_window",
    "calculate_max_payload_tokens",
    "OUTPUT_RATIO",
    "SAFETY_BUFFER",
    "PROMPT_OVERHEAD_TOKENS",
    "TOKENS_PER_FINDING",
]
