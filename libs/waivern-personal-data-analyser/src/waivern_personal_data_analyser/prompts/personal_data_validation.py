"""LLM validation prompts for personal data findings validation."""

from typing import Any


def get_personal_data_validation_prompt(
    category: str,
    special_category: bool,
    matched_patterns: list[str],
    evidence: list[str] | None,
    source: str,
) -> str:
    """Generate a validation prompt for a personal data finding.

    This prompt is designed to help LLMs distinguish between actual personal data
    and false positives (documentation, examples, field names, etc.).

    Args:
        category: Category of personal data detected (e.g., 'email', 'phone')
        special_category: Whether this is GDPR Article 9 special category data
        matched_patterns: Patterns that were matched during detection
        evidence: List of evidence snippets where pattern was found
        source: Source location of the data (e.g., database table, file path)

    Returns:
        Formatted validation prompt for the LLM

    """
    evidence_text = (
        "\n".join(f"- {e}" for e in evidence) if evidence else "No evidence provided"
    )
    special_cat_text = "Yes (Article 9)" if special_category else "No"

    return f"""You are an expert GDPR compliance analyst. Validate whether this detected pattern represents actual personal data or a false positive.

**FINDING TO VALIDATE:**
Category: {category}
Special Category: {special_cat_text}
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

        findings_text.append(f"""
Finding [{finding["id"]}]:
  Category: {finding.get("category", "Unknown")}
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
Respond with valid JSON array only (no markdown formatting).
IMPORTANT: Echo back the exact finding_id from each Finding [...] header - do not modify it.

[
  {{
    "finding_id": "<exact UUID from Finding [UUID]>",
    "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "recommended_action": "keep" | "discard"
  }}
]

Validate all {len(findings)} findings:"""


def get_conservative_validation_prompt(
    category: str,
    special_category: bool,
    matched_patterns: list[str],
    evidence: list[str] | None,
    source: str,
) -> str:
    """Generate a conservative validation prompt for special category data.

    This prompt errs on the side of caution for sensitive personal data,
    only marking as false positive when very confident.

    Args:
        category: Category of personal data detected
        special_category: Whether this is GDPR Article 9 special category data
        matched_patterns: Patterns that were matched during detection
        evidence: List of evidence snippets where pattern was found
        source: Source location of the data

    Returns:
        Conservative validation prompt for sensitive data

    """
    evidence_text = (
        "\n".join(f"- {e}" for e in evidence) if evidence else "No evidence provided"
    )
    special_cat_text = "Yes (Article 9)" if special_category else "No"
    sensitivity_note = ""

    if special_category:
        sensitivity_note = "\n**⚠️ SPECIAL CATEGORY DATA**: This is potentially sensitive personal data under GDPR Article 9 (health, biometric, political, etc.). Use CONSERVATIVE validation."

    return f"""You are an expert GDPR compliance analyst performing CONSERVATIVE validation for sensitive personal data.

**FINDING TO VALIDATE:**
Category: {category}
Special Category: {special_cat_text}
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
