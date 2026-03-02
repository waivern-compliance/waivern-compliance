"""ISO 27001 domains ruleset.

Defines one rule per Annex A clause (A.5, A.6, A.7, A.8), each carrying
the five ISO 27001 control attributes and guidance text for LLM prompting.
Consumed by ControlAssessor to structure assessments and populate
control_assessment schema fields without LLM involvement.

Dependencies (keep in sync when upstream definitions change):
- SecurityDomain enum in waivern-security-evidence → security_domains master list

Tests enforce completeness: test_all_security_domains_are_covered will fail
if the security_domains master list diverges from the SecurityDomain enum.
"""

from typing import ClassVar, Literal

from pydantic import Field, field_validator, model_validator
from waivern_core import ClassificationRule, RulesetData

from waivern_rulesets.core.base import YAMLRuleset


class ISO27001DomainsRule(ClassificationRule):
    """Rule defining an ISO 27001 Annex A clause with assessment metadata.

    Each rule covers one Annex A clause (A.5, A.6, A.7, or A.8) and carries:
    - The security taxonomy domains relevant to this clause (for filtering evidence)
    - The five ISO 27001 Annex A control attributes (populated into control_assessment)
    - Guidance text for LLM prompt construction
    """

    domain: str = Field(
        min_length=1,
        description="Annex A clause reference (e.g. 'A.8')",
    )
    security_domains: tuple[str, ...] = Field(
        min_length=1,
        description=(
            "Security taxonomy domains covered by this Annex A clause; "
            "used to filter relevant security_evidence items per assessment call"
        ),
    )
    control_type: Literal["preventive", "detective", "corrective"] = Field(
        description="ISO 27001 Annex A control type attribute",
    )
    cia: tuple[Literal["confidentiality", "integrity", "availability"], ...] = Field(
        min_length=1,
        description="CIA triad information security properties for this clause",
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
        description="Annex A control descriptions included verbatim in the LLM prompt",
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
    """ISO 27001 domains ruleset data with cross-field validation."""

    security_domains: list[str] = Field(
        min_length=1,
        description=(
            "Master list of valid security domain values. "
            "DEPENDENCY: Must stay in sync with SecurityDomain enum in waivern-security-evidence. "
            "When adding or removing a domain there, update this list and re-check all rules below."
        ),
    )

    @model_validator(mode="after")
    def validate_rules(self) -> "ISO27001DomainsRulesetData":
        """Validate all rule security_domains values against the master list."""
        valid_domains = set(self.security_domains)

        for rule in self.rules:
            invalid = [d for d in rule.security_domains if d not in valid_domains]
            if invalid:
                msg = (
                    f"Rule '{rule.name}' has invalid security_domains: "
                    f"{invalid}. Valid: {sorted(valid_domains)}"
                )
                raise ValueError(msg)

        return self


class ISO27001DomainsRuleset(YAMLRuleset[ISO27001DomainsRule]):
    """ISO 27001 Annex A domains ruleset.

    One rule per Annex A clause (A.5 Organisational, A.6 People, A.7 Physical,
    A.8 Technological). Each rule carries the five ISO 27001 control attributes
    and guidance text consumed by ControlAssessor.

    Load via URI: local/iso27001_domains/1.0.0
    """

    ruleset_name: ClassVar[str] = "iso27001_domains"
    ruleset_version: ClassVar[str] = "1.0.0"
    _data_class: ClassVar[  # pyright: ignore[reportIncompatibleVariableOverride]
        type[ISO27001DomainsRulesetData]
    ] = ISO27001DomainsRulesetData
