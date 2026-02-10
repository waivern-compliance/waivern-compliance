"""Multi-provider LLM abstraction for Waivern Compliance Framework.

This module provides the LLM service interface that handles batching internally,
moving this responsibility from processors/analysers to the LLM service layer.

Architecture
------------

The LLM service separates concerns between processors and the service layer:

**Processor responsibilities** (domain logic):
- What to group by (source files, categories, etc.)
- What content to include with each group
- Batching mode selection (COUNT_BASED vs EXTENDED_CONTEXT)
- Prompt building via PromptBuilder protocol

**LLM Service responsibilities** (infrastructure):
- Token estimation (model-specific)
- Batch size calculation (based on context window)
- Bin-packing algorithm (optimisation detail)
- Response caching (scoped by run_id)

Usage Pattern
-------------

1. Create ItemGroup(s) with findings and optional content::

    groups = [ItemGroup(items=findings, content=source_content)]

2. Implement PromptBuilder for your domain::

    class MyPromptBuilder(PromptBuilder[MyFinding]):
        def build_prompt(self, items, content=None) -> str: ...

3. Call LLMService.complete()::

    result = await llm_service.complete(
        groups,
        prompt_builder=MyPromptBuilder(),
        response_model=MyResponseModel,
        batching_mode=BatchingMode.COUNT_BASED,
        run_id=run_id,
    )

4. Handle results and skipped findings::

    for response in result.responses: ...
    for skipped in result.skipped: ...

Batching Modes
--------------

- **COUNT_BASED**: Flattens all items, splits by count. Use for evidence-only
  validation where source content doesn't help.

- **EXTENDED_CONTEXT**: Keeps groups intact, bin-packs by tokens. Use when
  source file content helps validation (e.g., validating findings against
  the original source code).

Caching
-------

The LLMService caches responses per run_id. Cache keys are computed from
prompt + model + response_model. Cache is cleared after successful completion
(temporary working storage, not permanent state).
"""

__version__ = "0.1.0"

from waivern_llm.batch_planner import (
    BatchPlan,
    BatchPlanner,
    PlannedBatch,
)
from waivern_llm.batch_types import (
    BatchRequest,
    BatchResult,
    BatchStatus,
    BatchStatusLiteral,
    BatchSubmission,
)
from waivern_llm.cache import CacheEntry
from waivern_llm.errors import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMServiceError,
    PendingBatchError,
)
from waivern_llm.factory import LLMServiceFactory
from waivern_llm.providers import (
    AnthropicProvider,
    BatchLLMProvider,
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
    "BatchLLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider",
    # Errors
    "LLMServiceError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "PendingBatchError",
    # Batch types
    "BatchRequest",
    "BatchSubmission",
    "BatchStatus",
    "BatchStatusLiteral",
    "BatchResult",
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
