"""Multi-provider LLM abstraction for Waivern Compliance Framework.

This module provides the LLM service interface that handles batching internally,
moving this responsibility from processors/analysers to the LLM service layer.

Key concepts:
- Processors decide what to group (domain logic)
- LLM Service decides how to batch (token-aware bin-packing)
- Unified cache handles both sync responses and async batch tracking
"""

__version__ = "0.1.0"

from waivern_llm.batch_planner import (
    BatchPlan,
    BatchPlanner,
    PlannedBatch,
)
from waivern_llm.cache import CacheEntry
from waivern_llm.errors import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMServiceError,
)
from waivern_llm.factory import LLMServiceFactory
from waivern_llm.providers import (
    AnthropicProvider,
    GoogleProvider,
    LLMProvider,
    OpenAIProvider,
)
from waivern_llm.service import DefaultLLMService, LLMService
from waivern_llm.token_estimation import (
    OUTPUT_RATIO,
    PROMPT_OVERHEAD_TOKENS,
    SAFETY_BUFFER,
    TOKENS_PER_FINDING,
    calculate_max_payload_tokens,
    estimate_tokens,
    get_model_context_window,
)
from waivern_llm.types import (
    BatchingMode,
    ItemGroup,
    LLMCompletionResult,
    PromptBuilder,
    SkippedFinding,
    SkipReason,
)

__all__ = [
    # Version
    "__version__",
    # Core types
    "ItemGroup",
    "BatchingMode",
    "PromptBuilder",
    "SkipReason",
    "SkippedFinding",
    "LLMCompletionResult",
    # Service
    "LLMService",
    "DefaultLLMService",
    "LLMServiceFactory",
    # Providers
    "LLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider",
    # Errors
    "LLMServiceError",
    "LLMConfigurationError",
    "LLMConnectionError",
    # Cache
    "CacheEntry",
    # Batch planning
    "BatchPlanner",
    "BatchPlan",
    "PlannedBatch",
    # Token estimation
    "estimate_tokens",
    "get_model_context_window",
    "calculate_max_payload_tokens",
    "OUTPUT_RATIO",
    "SAFETY_BUFFER",
    "PROMPT_OVERHEAD_TOKENS",
    "TOKENS_PER_FINDING",
]
