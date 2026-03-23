"""PromptBuilder for ISO 27001 control assessment.

Implements the PromptBuilder protocol for generating assessment prompts
that combine control guidance, technical evidence, and document context.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

from waivern_llm import ItemGroup, PromptBuilder
from waivern_schemas.security_evidence import SecurityEvidenceModel


@dataclass(frozen=True)
class ControlContext:
    """Control guidance and Annex A attributes for prompt construction."""

    guidance_text: str
    control_type: str
    cia: list[str]
    cybersecurity_concept: str
    operational_capability: str
    iso_security_domain: str


class ISO27001PromptBuilder(PromptBuilder[SecurityEvidenceModel]):
    """Builds assessment prompts for ISO 27001 control evaluation.

    Unlike validation prompt builders (which ask the LLM to filter existing
    findings), this builder asks the LLM to produce a structured assessment
    verdict from evidence. The prompt combines:

    1. ISO 27001 framework context and assessment methodology
    2. Control guidance text and Annex A attributes
    3. Technical evidence items (code/config findings with polarity)
    4. Document context (policy/procedure content from the group)

    Uses INDEPENDENT batching mode — receives a single group per batch
    where group.content carries document context and group.items carries
    technical evidence.
    """

    def __init__(self, control: ControlContext) -> None:
        """Initialise with control context.

        Args:
            control: Control guidance text and Annex A attributes.

        """
        self._control = control

    @override
    def build_prompt(
        self,
        groups: Sequence[ItemGroup[SecurityEvidenceModel]],
    ) -> str:
        """Build an assessment prompt from evidence and document context.

        Args:
            groups: Groups of findings. INDEPENDENT mode provides a single
                group where items are technical evidence and content is
                formatted document context (may be None).

        Returns:
            Complete prompt string for LLM assessment.

        """
        items = groups[0].items
        content = groups[0].content

        sections: list[str] = [
            _FRAMEWORK_CONTEXT,
            self._build_control_section(),
        ]

        if items:
            sections.append(self._build_evidence_section(items))

        if content is not None:
            sections.append(f"**DOCUMENT CONTEXT:**\n{content}")

        sections.append(_INSTRUCTIONS)

        return "\n\n".join(sections)

    def _build_control_section(self) -> str:
        """Build the control guidance and attributes section."""
        cia_str = ", ".join(self._control.cia)
        return (
            f"**CONTROL UNDER ASSESSMENT:**\n"
            f"{self._control.guidance_text}\n"
            f"- Type: {self._control.control_type} | CIA: {cia_str}\n"
            f"- Cybersecurity concept: {self._control.cybersecurity_concept} | "
            f"Capability: {self._control.operational_capability}\n"
            f"- Security domain: {self._control.iso_security_domain}"
        )

    def _build_evidence_section(self, items: Sequence[SecurityEvidenceModel]) -> str:
        """Build the technical evidence section from security evidence items."""
        parts: list[str] = ["**TECHNICAL EVIDENCE:**"]
        for item in items:
            polarity_marker = " [NEGATIVE]" if item.polarity == "negative" else ""
            entry = (
                f"- [{item.evidence_type}]{polarity_marker} "
                f"(domain: {item.security_domain}, "
                f"confidence: {item.confidence:.1f}): "
                f"{item.description}"
            )
            if item.evidence:
                snippets = "; ".join(e.content for e in item.evidence if e.content)
                if snippets:
                    entry += f"\n  Snippets: {snippets}"
            parts.append(entry)
        return "\n".join(parts)


_FRAMEWORK_CONTEXT = """\
You are assessing a single ISO 27001:2022 Annex A control. \
ISO 27001 is an information security management system standard. \
Annex A defines 93 controls across organisational, people, physical, and technological categories.

Evidence comes from two sources:
- **Technical** (CODE/CONFIG): automated findings from source code and configuration scanning. \
Polarity indicates quality — positive = good practice, negative = gap or weakness, neutral = presence only.
- **Document** (policies, procedures, inspection reports): human-produced text provided as context.\
"""

_INSTRUCTIONS = """\
**ASSESSMENT INSTRUCTIONS:**
- Code/config evidence takes priority over document claims. If code contradicts a policy, the code is ground truth.
- 'compliant': evidence demonstrates the control IS implemented (not just planned or stated in policy).
- 'partial': document evidence shows intent (e.g. policy exists) but technical evidence is absent or insufficient to confirm implementation.
- 'non_compliant': evidence shows the control is not implemented or has significant gaps.
- gap_description must be specific and actionable — describe what is missing and what would close the gap. Set to null when compliant.

**RISK ASSESSMENT PRIORITY:**
Pay special attention to risk assessment results and risk treatment plans in the document context. \
These have an outsized impact on control effectiveness evaluation in the ISO 27001 context:
- A documented risk assessment that identifies relevant threats and assigns treatment ownership \
demonstrates that the organisation has considered the risk landscape for this control.
- A risk treatment plan that maps to this control's domain (e.g. accepting, mitigating, or transferring risk) \
is strong evidence of intent and may elevate a 'non_compliant' to 'partial'.
- Conversely, absence of risk assessment coverage for a control's domain is a significant gap \
even if technical controls exist — ISO 27001 requires risk-driven decision-making.

**RECOMMENDED ACTIONS:**
When the control is 'partial' or 'non_compliant', provide a prioritised list of recommended actions. \
Each action should be specific and fall into one of these categories:
- **Technical implementation**: code changes, configuration updates, tool deployments
- **Document creation/update**: policies, procedures, guidelines, risk registers
- **Evidence gathering**: attestations, audit logs, third-party certifications
When the control is 'compliant', recommended_actions must be an empty list.

**RESPONSE FORMAT:**
Respond with valid JSON:
{
  "status": "compliant" | "partial" | "non_compliant",
  "rationale": "Narrative referencing specific evidence that informed the verdict.",
  "gap_description": "Actionable gap description, or null if compliant.",
  "recommended_actions": ["Action 1", "Action 2"]
}"""
