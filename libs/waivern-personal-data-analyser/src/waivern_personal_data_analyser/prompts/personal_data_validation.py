"""LLM validation prompts for personal data findings validation."""

from typing import Any


def get_batch_validation_prompt(findings: list[dict[str, Any]]) -> str:
    """Generate a batch validation prompt for multiple findings.

    This is more efficient for validating multiple findings at once,
    ensuring consistent criteria across all validations.

    Args:
        findings: List of personal data findings to validate (must include 'id' field)

    Returns:
        Formatted batch validation prompt

    """
    findings_text: list[str] = []
    for finding in findings:
        evidence_list = finding.get("evidence", [])
        evidence_text = (
            "\n  ".join(f"- {e}" for e in evidence_list)
            if evidence_list
            else "No evidence"
        )

        metadata = finding.get("metadata")
        source = getattr(metadata, "source", "Unknown") if metadata else "Unknown"

        findings_text.append(f"""
Finding [{finding["id"]}]:
  Category: {finding.get("category", "Unknown")}
  Patterns: {", ".join(finding.get("matched_patterns", ["Unknown"]))}
  Source: {source}
  Evidence:
  {evidence_text}""")

    findings_block = "\n".join(findings_text)

    return f"""You are an expert GDPR compliance analyst. Validate multiple personal data findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_block}

**TASK:**
For each finding, determine if it represents actual personal data (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual personal data about identifiable individuals
- FALSE_POSITIVE: Documentation, examples, tutorials, field names, system messages
- Consider source context and evidence content
- Prioritise privacy protection when uncertain

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

Use "flag_for_review" when uncertain and human review is recommended.

Review all {len(findings)} findings. Return FALSE_POSITIVE findings and uncertain ones needing review (empty array if none):"""
