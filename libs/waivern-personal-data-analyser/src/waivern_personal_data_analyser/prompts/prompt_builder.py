"""PromptBuilder for personal data validation.

Implements the PromptBuilder protocol for generating validation prompts
for personal data indicators.
"""

from collections.abc import Sequence
from typing import override

from waivern_llm import PromptBuilder

from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorModel


class PersonalDataPromptBuilder(PromptBuilder[PersonalDataIndicatorModel]):
    """Builds validation prompts for personal data indicators.

    Uses COUNT_BASED batching mode, so the content parameter is ignored.
    """

    def __init__(self, validation_mode: str = "standard") -> None:
        """Initialise prompt builder.

        Args:
            validation_mode: Validation mode ("standard" or "conservative").

        """
        self._validation_mode = validation_mode

    @override
    def build_prompt(
        self,
        items: Sequence[PersonalDataIndicatorModel],
        content: str | None = None,
    ) -> str:
        """Build validation prompt for the given findings.

        Args:
            items: Findings to validate.
            content: Ignored - COUNT_BASED mode doesn't use shared content.

        Returns:
            Complete prompt string for LLM validation.

        Raises:
            ValueError: If items is empty.

        """
        if not items:
            raise ValueError("At least one finding must be provided")

        findings_block = self._build_findings_block(items)
        finding_count = len(items)

        return f"""You are an expert GDPR compliance analyst. Validate personal data findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_block}

**TASK:**
For each finding, determine if it represents actual personal data (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual personal data about identifiable individuals
- FALSE_POSITIVE: Documentation, examples, tutorials, field names, system messages
- Consider source context and evidence content
- Prioritise privacy protection when uncertain

**CATEGORY-SPECIFIC GUIDANCE:**
- email, phone, name: Common identifiers - validate source context carefully
- address, postcode: Location data - check if it's template/example vs real
- health, biometric: Special category (Article 9) - conservative validation required
- financial (card, bank): Check for known test patterns (4111..., test account numbers)
- national_id, passport: High sensitivity - conservative validation required

**SOURCE CONTEXT GUIDELINES:**
- Database content: Likely actual personal data (check for test/dev indicators)
- Source code: Could be real data handling or just comments/examples
- Configuration files: Usually false positive (field definitions, not actual data)
- Documentation files: Almost always false positive

**RESPONSE FORMAT:**
Respond with valid JSON array only (no markdown formatting).
IMPORTANT: Only return findings you identify as FALSE_POSITIVE or that need human review.
Do not include clear TRUE_POSITIVE findings.
Echo back the exact finding_id from each Finding [...] header - do not modify it.

[
  {{
    "finding_id": "<exact UUID from Finding [UUID]>",
    "validation_result": "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "recommended_action": "discard" | "flag_for_review"
  }}
]

Review all {finding_count} findings. Return FALSE_POSITIVE findings and uncertain ones needing review (empty array if none):"""

    def _build_findings_block(self, items: Sequence[PersonalDataIndicatorModel]) -> str:
        """Build formatted findings block for the prompt."""
        findings_parts: list[str] = []

        for finding in items:
            evidence_text = (
                "\n  ".join(f"- {e.content}" for e in finding.evidence)
                if finding.evidence
                else "No evidence"
            )
            source = finding.metadata.source if finding.metadata else "Unknown"
            patterns = ", ".join(
                f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns
            )

            findings_parts.append(f"""
Finding [{finding.id}]:
  Category: {finding.category}
  Patterns: {patterns}
  Source: {source}
  Evidence:
  {evidence_text}""")

        return "\n".join(findings_parts)
