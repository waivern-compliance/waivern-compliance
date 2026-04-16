"""Configuration and state types for personal data analysis analyser."""

from pydantic import BaseModel, Field
from waivern_analysers_shared.llm_validation.validation_orchestrator import (
    OrchestratorPrepareState,
)
from waivern_analysers_shared.types import (
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import BaseComponentConfiguration
from waivern_schemas.personal_data_indicator import PersonalDataIndicatorModel


class PersonalDataAnalyserConfig(BaseComponentConfiguration):
    """Configuration for PersonalDataAnalyser with DI support.

    This provides clear separation of concerns where each runner has its own
    configuration section in the runbook properties.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    pattern_matching: PatternMatchingConfig = Field(
        default_factory=lambda: PatternMatchingConfig(
            ruleset="local/personal_data_indicator/1.0.0"
        ),
        description="Pattern matching configuration for personal data detection",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=LLMValidationConfig,
        description="LLM validation configuration for filtering false positives",
    )

    # from_properties() inherited from BaseComponentConfiguration


class PersonalDataPrepareState(BaseModel):
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

    all_findings: list[PersonalDataIndicatorModel]
    """All pattern-matching findings (used for the no-dispatch output path)."""

    run_id: str
    """Run identifier for cache scoping and logging."""

    llm_enabled: bool
    """Whether LLM validation was requested and the service is available."""

    orchestrator_state: OrchestratorPrepareState[PersonalDataIndicatorModel] | None = (
        None
    )
    """Captured orchestrator state when a dispatch request was built; otherwise None."""
