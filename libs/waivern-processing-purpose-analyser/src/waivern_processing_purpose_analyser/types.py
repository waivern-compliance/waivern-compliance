"""Configuration and state types for processing purpose analyser."""

from typing import Literal

from pydantic import BaseModel, Field
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    OrchestratorPrepareState,
)
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import BaseComponentConfiguration
from waivern_schemas.processing_purpose_indicator import ProcessingPurposeIndicatorModel

# Type alias for source code context window sizes
SourceCodeContextWindow = Literal["small", "medium", "large", "full"]


class ProcessingPurposeAnalyserConfig(BaseComponentConfiguration):
    """Configuration for ProcessingPurposeAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/processing_purposes/1.0.0"
        ),
        description="Pattern matching configuration",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=LLMValidationConfig,
        description="LLM validation configuration for filtering false positives",
    )

    source_code_context_window: SourceCodeContextWindow = Field(
        default="small",
        description="Context window size for source code evidence: 'small' (±3 lines), 'medium' (±15 lines), 'large' (±50 lines), 'full' (entire file)",
    )

    # from_properties() inherited from BaseComponentConfiguration


class ProcessingPurposePrepareState(BaseModel):
    """Intermediate state for the distributed processor prepare/finalise split.

    Captures everything ``finalise()`` needs to produce the output message
    after dispatch results arrive. The executor treats this as opaque and
    persists it (via ``model_dump(mode="json")``) for batch-mode resume.

    Two operating modes are encoded via ``llm_enabled`` and
    ``orchestrator_state``:

    - LLM-disabled / no findings → ``orchestrator_state=None``. ``finalise()``
      builds the output message directly from ``all_findings`` with no
      validation metadata.
    - LLM-enabled with findings → ``orchestrator_state`` carries the
      ``OrchestratorPrepareState`` needed to invoke ``orchestrator.finalise()``
      on dispatch results. Its ``strategy_state`` slot carries the primary
      strategy's reconstruction data (e.g., source content map) across
      dispatch rounds.

    ``input_schema_name`` is captured so that ``finalise()`` can reconstruct
    the orchestrator with the same strategy configuration used in round 1
    (source_code schema yields a SourceCode primary with a fallback; other
    schemas yield a single evidence-only primary).
    """

    all_findings: list[ProcessingPurposeIndicatorModel]
    """All pattern-matching findings (used for the no-dispatch output path)."""

    run_id: str
    """Run identifier for cache scoping and logging."""

    llm_enabled: bool
    """Whether LLM validation was requested and the service is available."""

    input_schema_name: str
    """Schema name from the first input message — drives factory branching on reconstruction."""

    orchestrator_state: (
        OrchestratorPrepareState[ProcessingPurposeIndicatorModel] | None
    ) = None
    """Captured orchestrator state when a dispatch request was built; otherwise None."""
