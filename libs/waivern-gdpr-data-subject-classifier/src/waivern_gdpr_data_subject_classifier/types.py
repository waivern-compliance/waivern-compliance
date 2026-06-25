"""Configuration and state types for GDPR data subject classifier."""

from typing import Any, Self, override

from pydantic import BaseModel, Field
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError
from waivern_schemas.gdpr_data_subject import GDPRDataSubjectFindingModel


class GDPRDataSubjectClassifierConfig(BaseComponentConfiguration):
    """Configuration for GDPRDataSubjectClassifier.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen)
    - Strict validation (no extra fields)
    """

    ruleset: str = Field(
        default="local/gdpr_data_subject_classification/1.0.0",
        description="Ruleset URI for GDPR data subject classification rules",
    )
    llm_validation: LLMValidationConfig = Field(
        default_factory=LLMValidationConfig,
        description="LLM validation configuration for risk modifier detection",
    )

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from runbook properties.

        Args:
            properties: Raw properties from runbook configuration

        Returns:
            Validated configuration object

        Raises:
            ProcessorConfigError: If validation fails

        """
        return validate_or_raise(cls, properties, ProcessorConfigError)


class GDPRDataSubjectPrepareState(BaseModel):
    """Intermediate state for the distributed processor prepare/finalise split.

    Captures classified findings (GDPR category, articles, lawful bases) with
    empty ``risk_modifiers`` — modifiers are applied in ``finalise()`` once
    dispatch results are known. The executor treats this as opaque and
    persists it (via ``model_dump(mode="json")``) for batch-mode resume.

    The ruleset-derived regex detector is not carried in state: the classifier's
    ``__init__`` reconstructs it from the configured ruleset, so regex fallback
    still works on the resume path.
    """

    classified_findings: list[GDPRDataSubjectFindingModel]
    """Findings enriched with GDPR classification; risk_modifiers still empty."""

    run_id: str = ""
    """Run identifier for cache scoping. Empty when upstream did not set it —
    in which case ``llm_enabled`` is forced to False by ``prepare()``, and the
    regex fallback path produces a self-contained output without dispatch."""

    llm_enabled: bool
    """Whether LLM validation was requested and the service is available."""
