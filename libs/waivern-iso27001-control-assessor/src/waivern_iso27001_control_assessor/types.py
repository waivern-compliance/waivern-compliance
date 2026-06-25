"""Configuration and state types for ISO 27001 control assessor."""

from typing import Any, Self, override

from pydantic import BaseModel, ConfigDict, Field
from waivern_core import BaseComponentConfiguration
from waivern_core.config_validation import validate_or_raise
from waivern_core.errors import ProcessorConfigError
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule
from waivern_schemas.iso27001_assessment import EvidenceStatus
from waivern_schemas.security_document_context import SecurityDocumentContextModel
from waivern_schemas.security_evidence import SecurityEvidenceModel


class EvidenceSamplingConfig(BaseModel):
    """Configuration for stratified evidence sampling.

    When enabled, reduces evidence sent to the LLM by applying
    priority-preserving stratified sampling. Negative-polarity items
    are always included; remaining budget is allocated proportionally
    across evidence types with round-robin source diversity.

    Disabled by default — all evidence is sent to the LLM.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable stratified evidence sampling",
    )
    max_evidence_items: int = Field(
        default=20,
        ge=1,
        description="Maximum evidence items to send to the LLM per control",
    )


class ISO27001AssessorConfig(BaseComponentConfiguration):
    """Configuration for ISO27001Assessor.

    Each assessor instance assesses exactly one ISO 27001 control.
    The control_ref identifies which rule to load from the domain ruleset.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - Strict validation (no extra fields)
    """

    domain_ruleset: str = Field(
        default="local/iso27001_domains/1.0.0",
        description="Ruleset URI for ISO 27001 domain rules",
    )
    control_ref: str = Field(
        min_length=1,
        description="ISO 27001:2022 Annex A control reference (e.g. 'A.5.1')",
    )
    evidence_sampling: EvidenceSamplingConfig = Field(
        default_factory=EvidenceSamplingConfig,
        description="Stratified evidence sampling configuration",
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


class ISO27001PrepareState(BaseModel):
    """Intermediate state for the distributed processor prepare/finalise split.

    Captures everything ``finalise()`` needs to produce the output message
    after dispatch results arrive. The executor treats this as opaque and
    persists it for batch-mode resume.
    """

    rule: ISO27001DomainsRule
    evidence_status: EvidenceStatus
    evidence: list[SecurityEvidenceModel]
    documents: list[SecurityDocumentContextModel]
    run_id: str
