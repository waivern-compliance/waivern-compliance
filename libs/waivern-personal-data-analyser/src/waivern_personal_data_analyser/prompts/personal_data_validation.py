"""LLM validation prompts for personal data findings validation."""

from waivern_personal_data_analyser.schemas import PersonalDataIndicatorModel


def get_personal_data_validation_prompt(
    findings: list[PersonalDataIndicatorModel],
    validation_mode: str = "standard",
) -> str:
    """Generate validation prompt for personal data findings.

    Args:
        findings: List of personal data findings to validate
        validation_mode: "standard" or "conservative" validation approach

    Returns:
        Formatted validation prompt for the LLM

    """
    if not findings:
        raise ValueError("At least one finding must be provided")

    findings_text = _build_findings_block(findings)
    response_format = _get_response_format(len(findings))

    return f"""You are an expert GDPR compliance analyst. Validate multiple personal data findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_text}

**TASK:**
For each finding, determine if it represents actual personal data (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual personal data about identifiable individuals
- FALSE_POSITIVE: Documentation, examples, tutorials, field names, system messages
- Consider source context and evidence content
- Prioritise privacy protection when uncertain

{response_format}"""


def _build_findings_block(findings: list[PersonalDataIndicatorModel]) -> str:
    """Build formatted findings block for the prompt."""
    findings_text: list[str] = []

    for finding in findings:
        evidence_text = (
            "\n  ".join(f"- {evidence.content}" for evidence in finding.evidence)
            if finding.evidence
            else "No evidence"
        )

        source = finding.metadata.source if finding.metadata else "Unknown"

        findings_text.append(f"""
Finding [{finding.id}]:
  Category: {finding.category}
  Patterns: {", ".join(finding.matched_patterns)}
  Source: {source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _get_response_format(finding_count: int) -> str:
    """Get response format section for the prompt."""
    return f"""**RESPONSE FORMAT:**
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

Use "flag_for_review" when uncertain and human review is recommended.

Review all {finding_count} findings. Return FALSE_POSITIVE findings and uncertain ones needing review (empty array if none):"""
