"""LLM validation prompts for processing purpose findings validation."""

import re

from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeFindingModel,
)


def get_processing_purpose_validation_prompt(
    findings: list[ProcessingPurposeFindingModel], validation_mode: str = "standard"
) -> str:
    """Generate validation prompt for processing purpose findings.

    This prompt is designed to help LLMs distinguish between actual business
    processing activities and false positives (documentation, examples, code comments).
    Handles both single findings (as a list of 1) and multiple findings efficiently.

    Args:
        findings: List of processing purpose findings to validate
        validation_mode: "standard" or "conservative" validation approach

    Returns:
        Formatted validation prompt for the LLM

    """
    if not findings:
        raise ValueError("At least one finding must be provided")

    is_conservative = validation_mode == "conservative"

    # Build findings block
    findings_to_validate = _build_findings_to_validate(findings)

    # Build validation approach section
    validation_approach = _get_validation_approach(validation_mode, findings)

    # Build category guidance
    category_guidance = _get_category_guidance_summary()

    # Build response format
    response_format = _get_response_format(len(findings), is_conservative)

    return f"""
You are an expert GDPR compliance analyst. Validate processing purpose findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_to_validate}

**VALIDATION TASK:**
For each finding, determine if it represents actual business processing (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).
{validation_approach}

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual business processing activities affecting real users/customers
- FALSE_POSITIVE: Documentation, examples, tutorials, code comments, configuration templates
- Consider purpose category, risk level, and source context
- Assess source context (database vs. code vs. documentation)

**CATEGORY-SPECIFIC GUIDANCE:**
{category_guidance}

**SOURCE CONTEXT GUIDELINES:**
- Database content: Likely actual processing activity
- Source code: Could be implementation or just comments/examples
- Configuration files: Tool setup vs. documentation examples
- Documentation files: Almost always false positive

{response_format}"""


def _build_findings_to_validate(findings: list[ProcessingPurposeFindingModel]) -> str:
    """Build formatted findings block for the prompt.

    Args:
        findings: List of processing purpose findings

    Returns:
        Formatted findings block string

    """
    findings_text: list[str] = []
    for i, finding in enumerate(findings):
        evidence_text = (
            "\n  ".join(f"- {evidence.content}" for evidence in finding.evidence)
            if finding.evidence
            else "No evidence"
        )

        source = finding.metadata.source if finding.metadata else "Unknown"

        findings_text.append(f"""
Finding {i}:
  Purpose: {finding.purpose}
  Category: {finding.purpose_category}
  Risk: {finding.risk_level}
  Pattern: {finding.matched_pattern}
  Source: {source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _get_validation_approach(
    validation_mode: str, findings: list[ProcessingPurposeFindingModel]
) -> str:
    """Get validation approach section based on mode and findings."""
    if validation_mode == "conservative":
        # Check if any findings are high-risk or sensitive categories
        high_risk_findings = [f for f in findings if f.risk_level == "high"]
        sensitive_categories = [
            f
            for f in findings
            if f.purpose_category
            in ["AI_AND_ML", "ANALYTICS", "MARKETING_AND_ADVERTISING"]
        ]

        warnings: list[str] = []
        if high_risk_findings:
            warnings.append(
                "⚠️ HIGH RISK PROCESSING detected - use CONSERVATIVE validation"
            )
        if sensitive_categories:
            warnings.append(
                "⚠️ PRIVACY SENSITIVE categories detected - conservative approach required"
            )

        warning_text = "\n".join(f"**{w}**" for w in warnings) if warnings else ""

        return f"""
**CONSERVATIVE VALIDATION MODE:**
{warning_text}
- Only mark as FALSE_POSITIVE if very confident it's not actual business processing
- When in doubt, mark as TRUE_POSITIVE to protect privacy and compliance
- Consider potential regulatory impact if this processing is mishandled
- Err on the side of data protection compliance
- Prioritize regulatory compliance over false positive reduction"""

    else:  # standard mode
        return """
**STANDARD VALIDATION MODE:**
- Balance false positive reduction with compliance requirements
- Apply context-aware assessment considering purpose category and risk level
- Focus on clear business context indicators"""


def _get_category_guidance_summary() -> str:
    """Get consolidated category-specific guidance."""
    return """
- AI_AND_ML: Conservative validation, distinguish actual implementation from discussion/tutorials
- OPERATIONAL: Generic terms need strong context validation, check for real customer interactions
- ANALYTICS: High privacy impact, conservative validation for actual data collection vs. theoretical discussion
- MARKETING_AND_ADVERTISING: High privacy risk, conservative validation for personalization/targeting
- SECURITY: Generally legitimate in business context, rarely false positives"""


def _get_response_format(finding_count: int, is_conservative: bool) -> str:
    """Get array response format for all cases (single finding returns array with one element)."""
    action_options = (
        '"keep" | "discard" | "flag_for_review"'
        if is_conservative
        else '"keep" | "discard"'
    )
    reasoning_length = "max 150 words" if is_conservative else "max 120 words"

    # Always use array format for consistency
    example_second = ""
    if finding_count > 1:
        example_second = """,
  {
    "finding_index": 1,
    "validation_result": "FALSE_POSITIVE",
    "confidence": 0.95,
    "reasoning": "Documentation example with no business impact",
    "recommended_action": "discard"
  }"""

    return f"""**RESPONSE FORMAT:**
Respond with valid JSON array only (no markdown formatting):

[
  {{
    "finding_index": 0,
    "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation with category/risk context ({reasoning_length})",
    "recommended_action": {action_options}
  }}{example_second}
]

Validate all {finding_count} findings and return array with {finding_count} element(s):"""


def extract_json_from_response(llm_response: str) -> str:
    """Extract JSON from LLM response that may be wrapped in markdown.

    Claude often returns JSON wrapped in ```json``` blocks. This function
    extracts the clean JSON for parsing.

    Args:
        llm_response: Raw response from LLM

    Returns:
        Clean JSON string

    """
    # Remove markdown code block wrapper if present
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", llm_response, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    # Also try to extract JSON array for batch responses
    array_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", llm_response, re.DOTALL)
    if array_match:
        return array_match.group(1).strip()

    # If no markdown wrapper, return the response as-is
    return llm_response.strip()


# Validation result constants for type safety
class ValidationResult:
    """Constants for validation results."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class RecommendedAction:
    """Constants for recommended actions."""

    KEEP = "keep"
    DISCARD = "discard"
    FLAG_FOR_REVIEW = "flag_for_review"
