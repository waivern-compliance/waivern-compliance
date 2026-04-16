"""Configuration and state types for data subject analyser."""

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
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel

# Type alias for source code context window sizes
SourceCodeContextWindow = Literal["small", "medium", "large", "full"]


class DataSubjectAnalyserConfig(BaseComponentConfiguration):
    """Configuration for DataSubjectAnalyser.

    Groups related configuration parameters to reduce constructor complexity.
    Uses Pydantic for validation and default values.
    Inherits from BaseComponentConfiguration for DI system integration.
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0"
        ),
        description="Pattern matching configuration",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=lambda: LLMValidationConfig(enable_llm_validation=False),
        description="LLM validation configuration for improving classification accuracy",
    )
    source_code_context_window: SourceCodeContextWindow = Field(
        default="small",
        description=(
            "Context window size for source code evidence: "
            "'small' (±3 lines), 'medium' (±15 lines), "
            "'large' (±50 lines), 'full' (entire file)"
        ),
    )


class DataSubjectPrepareState(BaseModel):
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
      on dispatch results.
    """

    all_findings: list[DataSubjectIndicatorModel]
    """All pattern-matching findings (used for the no-dispatch output path)."""

    run_id: str
    """Run identifier for cache scoping and logging."""

    llm_enabled: bool
    """Whether LLM validation was requested and the service is available."""

    orchestrator_state: OrchestratorPrepareState[DataSubjectIndicatorModel] | None = (
        None
    )
    """Captured orchestrator state when a dispatch request was built; otherwise None."""
