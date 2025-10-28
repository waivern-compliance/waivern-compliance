"""LLM validation prompts for personal data findings validation."""

from typing import Any


def get_personal_data_validation_prompt(  # noqa: PLR0913
    finding_type: str,
    risk_level: str,
    special_category: str | None,
    matched_patterns: list[str],
    evidence: list[str] | None,
    source: str,
) -> str:
    """Generate a validation prompt for a personal data finding.

    This prompt is designed to help LLMs distinguish between actual personal data
    and false positives (documentation, examples, field names, etc.).

    Args:
        finding_type: Type of personal data detected (e.g., 'email', 'phone')
        risk_level: Risk level (low/medium/high)
        special_category: GDPR special category (Y/N/null)
        matched_patterns: Patterns that were matched during detection
        evidence: List of evidence snippets where pattern was found
        source: Source location of the data (e.g., database table, file path)

    Returns:
        Formatted validation prompt for the LLM

    """
    evidence_text = (
        "\n".join(f"- {e}" for e in evidence) if evidence else "No evidence provided"
    )

    return f"""You are an expert GDPR compliance analyst. Validate whether this detected pattern represents actual personal data or a false positive.

**FINDING TO VALIDATE:**
Type: {finding_type}
Risk Level: {risk_level}
Special Category: {special_category or "Not specified"}
Patterns: {", ".join(matched_patterns)}
Source: {source}

**EVIDENCE:**
{evidence_text}

**VALIDATION TASK:**
Determine if this is actual personal data about identifiable individuals or a false positive (documentation, examples, field names, etc.).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual personal data that could identify, contact, or profile individuals
- FALSE_POSITIVE: Documentation, examples, tutorials, field names, system messages, code comments

**GUIDELINES:**
- Focus on whether real individuals could be identified or affected
- Consider the source context (database content vs documentation)
- When genuinely uncertain, lean towards TRUE_POSITIVE for privacy protection
- Be strict about obvious false positives (help text, API docs, examples)

**RESPONSE FORMAT:**
Respond with valid JSON only (no markdown formatting):

{{
  "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
  "confidence": 0.85,
  "reasoning": "Brief explanation of your decision (max 100 words)",
  "recommended_action": "keep" | "discard"
}}

Provide your validation response:"""


def get_batch_validation_prompt(findings: list[dict[str, Any]]) -> str:
    """Generate a batch validation prompt for multiple findings.

    This is more efficient for validating multiple findings at once,
    ensuring consistent criteria across all validations.

    Args:
        findings: List of personal data findings to validate

    Returns:
        Formatted batch validation prompt

    """
    findings_text: list[str] = []
    for i, finding in enumerate(findings):
        evidence_list = finding.get("evidence", [])
        evidence_text = (
            "\n  ".join(f"- {e}" for e in evidence_list)
            if evidence_list
            else "No evidence"
        )

        findings_text.append(f"""
Finding {i}:
  Type: {finding.get("type", "Unknown")}
  Risk: {finding.get("risk_level", "Unknown")}
  Special Category: {finding.get("special_category", "Not specified")}
  Patterns: {", ".join(finding.get("matched_patterns", ["Unknown"]))}
  Source: {getattr(finding.get("metadata", {}), "source", "Unknown") if finding.get("metadata") else "Unknown"}
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
- Prioritize privacy protection when uncertain

**RESPONSE FORMAT:**
Respond with valid JSON array only (no markdown formatting):

[
  {{
    "finding_index": 0,
    "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "recommended_action": "keep" | "discard"
  }},
  {{
    "finding_index": 1,
    "validation_result": "FALSE_POSITIVE",
    "confidence": 0.95,
    "reasoning": "Documentation example",
    "recommended_action": "discard"
  }}
]

Validate all {len(findings)} findings:"""


def get_conservative_validation_prompt(  # noqa: PLR0913
    finding_type: str,
    risk_level: str,
    special_category: str | None,
    matched_patterns: list[str],
    evidence: list[str] | None,
    source: str,
) -> str:
    """Generate a conservative validation prompt for high-risk or special category data.

    This prompt errs on the side of caution for sensitive personal data,
    only marking as false positive when very confident.

    Args:
        finding_type: Type of personal data detected
        risk_level: Risk level (low/medium/high)
        special_category: GDPR special category (Y/N/null)
        matched_patterns: Patterns that were matched during detection
        evidence: List of evidence snippets where pattern was found
        source: Source location of the data

    Returns:
        Conservative validation prompt for sensitive data

    """
    evidence_text = (
        "\n".join(f"- {e}" for e in evidence) if evidence else "No evidence provided"
    )
    sensitivity_note = ""

    if special_category == "Y":
        sensitivity_note = "\n**⚠️ SPECIAL CATEGORY DATA**: This is potentially sensitive personal data under GDPR (health, biometric, political, etc.). Use CONSERVATIVE validation."
    elif risk_level == "high":
        sensitivity_note = "\n**⚠️ HIGH RISK DATA**: This data carries significant privacy risk. Use CONSERVATIVE validation."

    return f"""You are an expert GDPR compliance analyst performing CONSERVATIVE validation for sensitive personal data.

**FINDING TO VALIDATE:**
Type: {finding_type}
Risk Level: {risk_level}
Special Category: {special_category or "Not specified"}
Patterns: {", ".join(matched_patterns)}
Source: {source}
{sensitivity_note}

**EVIDENCE:**
{evidence_text}

**CONSERVATIVE VALIDATION:**
Due to the sensitive nature of this data, use conservative judgment:
- Only mark as FALSE_POSITIVE if you are very confident it's not personal data
- When in doubt, mark as TRUE_POSITIVE to protect privacy
- Consider potential harm to individuals if this data is mishandled
- Err on the side of data protection compliance

**RESPONSE FORMAT:**
Respond with valid JSON only (no markdown formatting):

{{
  "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
  "confidence": 0.85,
  "reasoning": "Detailed explanation focusing on privacy impact (max 150 words)",
  "recommended_action": "keep" | "discard" | "flag_for_review"
}}

Provide your conservative validation response:"""
