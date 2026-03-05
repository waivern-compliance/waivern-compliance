"""ISO 27001 domains ruleset.

Defines one rule per individual ISO 27001:2022 Annex A control — 93 rules total
(A.5.1–A.5.37, A.6.1–A.6.8, A.7.1–A.7.14, A.8.1–A.8.34). Per-control granularity
is required for a meaningful Statement of Applicability (SoA).

Each rule carries the five ISO 27001 control attributes and guidance text for LLM
prompting. Consumed by ControlAssessor to structure assessments and populate
control_assessment schema fields without LLM involvement.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator
from waivern_core import ClassificationRule, RulesetData, SecurityDomain

from waivern_rulesets.core.base import YAMLRuleset


class ISO27001DomainsRule(ClassificationRule):
    """Rule defining an individual ISO 27001:2022 Annex A control with assessment metadata.

    Each rule covers one individual control (e.g. A.5.15) and carries:
    - The security taxonomy domains relevant to this control (for filtering evidence)
    - The evidence source types relevant to this control (TECHNICAL | DOCUMENT)
    - Whether human attestation is always required regardless of automated evidence
    - The five ISO 27001 Annex A control attributes (populated into control_assessment)
    - Guidance text for LLM prompt construction
    """

    control_ref: str = Field(
        min_length=1,
        description="Individual ISO 27001:2022 Annex A control reference (e.g. 'A.5.15')",
    )
    security_domains: tuple[SecurityDomain, ...] = Field(
        description=(
            "Security taxonomy domains relevant to this control; used to filter "
            "security_evidence items by domain. May be empty for cross-cutting governance "
            "controls where no single taxonomy domain applies (e.g. A.5.1 Policies). "
            "Physical controls use [physical_security] because document evidence from "
            "physical security policies carries that domain."
        ),
    )
    evidence_source: tuple[Literal["TECHNICAL", "DOCUMENT"], ...] = Field(
        description=(
            "Origin types of evidence relevant to this control. "
            "TECHNICAL covers both CODE and CONFIG evidence. "
            "May be empty for purely manual controls with no evidence path."
        ),
    )
    attestation_required: bool = Field(
        description=(
            "True when the control requires human attestation regardless of automated "
            "evidence (e.g. policy approval, physical inspection). Independent from "
            "evidence_source — both can be true simultaneously."
        ),
    )
    control_type: Literal["preventive", "detective", "corrective"] = Field(
        description="ISO 27001 Annex A control type attribute",
    )
    cia: tuple[Literal["confidentiality", "integrity", "availability"], ...] = Field(
        min_length=1,
        description="CIA triad information security properties for this control",
    )
    cybersecurity_concept: Literal[
        "identify", "protect", "detect", "respond", "recover"
    ] = Field(
        description="NIST CSF cybersecurity concept alignment",
    )
    operational_capability: str = Field(
        min_length=1,
        description="Annex A operational capability tag (e.g. 'governance')",
    )
    iso_security_domain: Literal[
        "governance_and_ecosystem", "protection", "defence", "resilience"
    ] = Field(
        description="ISO 27001 security domain attribute (4-value taxonomy)",
    )
    guidance_text: str = Field(
        min_length=1,
        description="Control description included verbatim in the LLM prompt",
    )

    @field_validator("security_domains", mode="before")
    @classmethod
    def convert_security_domains_to_tuple(
        cls, v: list[str] | tuple[str, ...]
    ) -> tuple[str, ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v

    @field_validator("evidence_source", mode="before")
    @classmethod
    def convert_evidence_source_to_tuple(
        cls,
        v: list[Literal["TECHNICAL", "DOCUMENT"]]
        | tuple[Literal["TECHNICAL", "DOCUMENT"], ...],
    ) -> tuple[Literal["TECHNICAL", "DOCUMENT"], ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v

    @field_validator("cia", mode="before")
    @classmethod
    def convert_cia_to_tuple(
        cls,
        v: list[Literal["confidentiality", "integrity", "availability"]]
        | tuple[Literal["confidentiality", "integrity", "availability"], ...],
    ) -> tuple[Literal["confidentiality", "integrity", "availability"], ...]:
        """Convert list to tuple for immutability."""
        if isinstance(v, list):
            return tuple(v)
        return v


class ISO27001DomainsRulesetData(RulesetData[ISO27001DomainsRule]):
    """ISO 27001 domains ruleset data.

    security_domains values are validated by Pydantic against the SecurityDomain
    enum at rule parse time — no manual cross-field validator needed.
    """

    pass


class ISO27001DomainsRuleset(YAMLRuleset[ISO27001DomainsRule]):
    """ISO 27001 Annex A domains ruleset.

    One rule per individual ISO 27001:2022 Annex A control — 93 rules total
    (A.5.1–A.5.37, A.6.1–A.6.8, A.7.1–A.7.14, A.8.1–A.8.34). Each rule
    carries the five ISO 27001 control attributes and guidance text consumed
    by ControlAssessor.

    Load via URI: local/iso27001_domains/1.0.0
    """

    ruleset_name: ClassVar[str] = "iso27001_domains"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ISO27001DomainsRulesetData]
    ] = ISO27001DomainsRulesetData
