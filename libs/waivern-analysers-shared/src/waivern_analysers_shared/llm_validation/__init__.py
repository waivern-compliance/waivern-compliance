"""LLM validation utilities for analysers."""

from waivern_analysers_shared.llm_validation.batched_files_strategy import (
    BatchedFilesStrategyBase,
    BatchingResult,
    FileBatch,
    FileValidationResult,
)
from waivern_analysers_shared.llm_validation.decision_engine import (
    ValidationDecisionEngine,
)
from waivern_analysers_shared.llm_validation.default_strategy import (
    DefaultLLMValidationStrategy,
)
from waivern_analysers_shared.llm_validation.extended_context_strategy import (
    ExtendedContextLLMValidationStrategy,
    SourceBatch,
)
from waivern_analysers_shared.llm_validation.file_content import (
    FileContentProvider,
    FileInfo,
)
from waivern_analysers_shared.llm_validation.grouping import (
    ConcernGroupingStrategy,
    GroupingStrategy,
    SourceGroupingStrategy,
)
from waivern_analysers_shared.llm_validation.models import (
    SKIP_REASON_BATCH_ERROR,
    SKIP_REASON_MISSING_CONTENT,
    SKIP_REASON_NO_SOURCE,
    SKIP_REASON_OVERSIZED,
    LLMValidationOutcome,
    LLMValidationResponseModel,
    LLMValidationResultModel,
    RecommendedActionType,
    RemovedGroup,
    SkippedFinding,
    ValidationResult,
    ValidationResultType,
)
from waivern_analysers_shared.llm_validation.protocols import (
    ConcernProvider,
    SourceProvider,
)
from waivern_analysers_shared.llm_validation.sampling import (
    RandomSamplingStrategy,
    SamplingResult,
    SamplingStrategy,
)
from waivern_analysers_shared.llm_validation.strategy import LLMValidationStrategy
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    ValidationOrchestrator,
)

__all__ = [
    # Batched files strategy
    "BatchedFilesStrategyBase",
    "BatchingResult",
    "FileBatch",
    "FileValidationResult",
    "FileContentProvider",
    "FileInfo",
    # Validation decision
    "ValidationDecisionEngine",
    # Grouping strategies
    "ConcernGroupingStrategy",
    "GroupingStrategy",
    "SourceGroupingStrategy",
    # Sampling strategies
    "RandomSamplingStrategy",
    "SamplingResult",
    "SamplingStrategy",
    # Models
    "LLMValidationOutcome",
    "LLMValidationResponseModel",
    "LLMValidationResultModel",
    "RecommendedActionType",
    "RemovedGroup",
    "SKIP_REASON_BATCH_ERROR",
    "SKIP_REASON_MISSING_CONTENT",
    "SKIP_REASON_NO_SOURCE",
    "SKIP_REASON_OVERSIZED",
    "SkippedFinding",
    "ValidationResult",
    "ValidationResultType",
    # Protocols
    "ConcernProvider",
    "SourceProvider",
    # Strategies
    "DefaultLLMValidationStrategy",
    "ExtendedContextLLMValidationStrategy",
    "LLMValidationStrategy",
    "SourceBatch",
    # Orchestration
    "ValidationOrchestrator",
]
