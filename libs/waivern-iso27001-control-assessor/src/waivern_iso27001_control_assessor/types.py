"""Configuration and state types for ISO 27001 control assessor."""

from pydantic import BaseModel, Field
from waivern_core import BaseComponentConfiguration
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule
from waivern_schemas.iso27001_assessment import EvidenceStatus
from waivern_schemas.security_document_context import SecurityDocumentContextModel
from waivern_schemas.security_evidence import SecurityEvidenceModel


class ISO27001AssessorConfig(BaseComponentConfiguration):
    """Configuration for ISO27001Assessor.

    Each assessor instance assesses exactly one ISO 27001 control.
    The control_ref identifies which rule to load from the domain ruleset.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
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
    llm_enabled: bool
