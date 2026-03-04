"""Configuration types for security evidence normaliser."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class SecurityEvidenceNormaliserConfig(BaseComponentConfiguration):
    """Configuration for SecurityEvidenceNormaliser.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)

    No LLM configuration — normalisation is fully deterministic.
    Domain mapping is driven by the YAML ruleset, not hard-coded logic.
    """

    domain_ruleset: str = Field(
        default="local/security_evidence_domain_mapping/1.0.0",
        description="Ruleset URI for mapping indicator values to security domains",
    )
    maximum_evidence_items: int = Field(
        default=3,
        ge=1,
        description=(
            "Maximum number of evidence snippets to include per security evidence item. "
            "Snippets are collected across all findings in a group and capped at this value."
        ),
    )
