"""PromptBuilder for risk modifier validation.

Implements the PromptBuilder protocol for generating validation prompts
for risk modifier detection in GDPR data subject findings.
"""

from collections.abc import Sequence
from typing import override

from waivern_llm.v2 import PromptBuilder
from waivern_rulesets import RiskModifier

from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingModel


class RiskModifierPromptBuilder(PromptBuilder[GDPRDataSubjectFindingModel]):
    """Builds validation prompts for risk modifier detection.

    Uses COUNT_BASED batching mode, so the content parameter is ignored.
    """

    def __init__(self, available_modifiers: list[RiskModifier]) -> None:
        """Initialise prompt builder.

        Args:
            available_modifiers: Risk modifiers from the ruleset to detect.

        """
        self._available_modifiers = available_modifiers

    @override
    def build_prompt(
        self,
        items: Sequence[GDPRDataSubjectFindingModel],
        content: str | None = None,
    ) -> str:
        """Build validation prompt for the given findings.

        Args:
            items: Findings to analyse for risk modifiers.
            content: Ignored - COUNT_BASED mode doesn't use shared content.

        Returns:
            Complete prompt string for LLM validation.

        Raises:
            ValueError: If items is empty.

        """
        if not items:
            raise ValueError("At least one finding must be provided")

        findings_text = self._build_findings_block(items)
        modifier_definitions = self._build_modifier_definitions()
        response_format = self._get_response_format(len(items))

        return f"""You are an expert GDPR data protection analyst. Analyse evidence text to detect risk modifiers that indicate special data subject categories requiring additional protections.

**FINDINGS TO ANALYSE:**
{findings_text}

**TASK:**
For each finding, identify any GDPR risk modifiers present in the evidence text. Risk modifiers indicate special categories of data subjects that require additional protections under GDPR.

**AVAILABLE RISK MODIFIERS:**
{modifier_definitions}

**DETECTION GUIDELINES:**

1. **Analyse semantic meaning, not just keywords:**
   - "minor changes to the patient record" → NO minor modifier (means "small", not "child")
   - "8-year-old patient" → YES minor modifier (refers to a child)
   - "vulnerable to attacks" → NO vulnerable_individual modifier (security context, not person)
   - "elderly patient with dementia" → YES vulnerable_individual modifier (person needing protection)

2. **Positive indicators for minors (Article 8):**
   - Age mentions under 16: "8-year-old", "aged 12", "15 years old"
   - Child-related terms in person context: "child patient", "minor child"
   - Guardian/parental references: "requires guardian signature", "parental consent"
   - School/youth context: "student aged 14", "youth club member"

3. **Negative indicators (NOT risk modifiers):**
   - "minor" meaning small/insignificant: "minor update", "minor changes", "minor issue"
   - Technical vulnerability: "vulnerable to SQL injection", "security vulnerability"
   - Non-person contexts: "child process", "child table", "parent-child relationship" (database)

4. **When uncertain:** Be conservative - only flag modifiers you're confident about.

**FEW-SHOT EXAMPLES:**

Example 1 - Minor detected:
```
Evidence: "Patient record for Sarah, age 8, requires guardian consent for treatment"
```
→ risk_modifiers: ["minor"]
→ reasoning: "Age 8 explicitly mentioned, guardian consent required - clearly a child under Article 8"

Example 2 - No modifiers (false positive avoided):
```
Evidence: "Made minor changes to the patient_id field in database schema"
```
→ risk_modifiers: []
→ reasoning: "'minor' here means 'small changes', not a child - this is a schema modification"

Example 3 - Vulnerable individual detected:
```
Evidence: "Elderly patient with dementia admitted to care facility"
```
→ risk_modifiers: ["vulnerable_individual"]
→ reasoning: "Elderly with dementia indicates a vulnerable person requiring additional protections under Recital 75"

Example 4 - Multiple modifiers:
```
Evidence: "12-year-old patient with learning disability receiving special education support"
```
→ risk_modifiers: ["minor", "vulnerable_individual"]
→ reasoning: "Age 12 indicates minor (Article 8), learning disability indicates vulnerable individual (Recital 75)"

{response_format}"""

    def _build_findings_block(
        self, items: Sequence[GDPRDataSubjectFindingModel]
    ) -> str:
        """Build formatted findings block for the prompt."""
        findings_parts: list[str] = []

        for finding in items:
            evidence_text = (
                "\n  ".join(f"- {evidence.content}" for evidence in finding.evidence)
                if finding.evidence
                else "No evidence"
            )

            findings_parts.append(f"""
Finding [{finding.id}]:
  Data Subject Category: {finding.data_subject_category}
  Source: {finding.metadata.source}
  Evidence:
  {evidence_text}""")

        return "\n".join(findings_parts)

    def _build_modifier_definitions(self) -> str:
        """Build modifier definitions section from ruleset."""
        if not self._available_modifiers:
            return "No specific modifiers defined - use general GDPR risk assessment."

        definitions: list[str] = []
        for modifier in self._available_modifiers:
            articles = ", ".join(modifier.article_references)
            definitions.append(f"- **{modifier.modifier}** ({articles})")

        return "\n".join(definitions)

    def _get_response_format(self, finding_count: int) -> str:
        """Get response format section for the prompt."""
        return f"""**RESPONSE FORMAT:**
Respond with valid JSON only (no markdown formatting).
For each finding, provide the detected risk modifiers (empty list if none).
Echo back the exact finding_id from each Finding [...] header.

{{
  "results": [
    {{
      "finding_id": "<exact UUID from Finding [UUID]>",
      "risk_modifiers": ["modifier_name", ...],
      "reasoning": "Brief explanation of why these modifiers were detected (or why none)",
      "confidence": 0.85
    }}
  ]
}}

Analyse all {finding_count} finding(s) and return results for each:"""
