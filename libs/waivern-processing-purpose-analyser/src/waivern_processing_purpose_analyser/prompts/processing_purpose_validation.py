"""LLM validation prompts for processing purpose indicator validation.

TODO: Refactor to use separate prompt strategies for different source types
(database, source_code, filesystem) when adding more connector types.
Currently this single prompt handles all source types with combined guidance.
"""

from waivern_processing_purpose_analyser.schemas import (
    ProcessingPurposeIndicatorModel,
)


def get_processing_purpose_validation_prompt(
    findings: list[ProcessingPurposeIndicatorModel],
    validation_mode: str = "standard",
    sensitive_purposes: list[str] | None = None,
) -> str:
    """Generate validation prompt for processing purpose indicators.

    This prompt is designed to help LLMs distinguish between actual business
    processing activities and false positives (documentation, examples, code comments).
    Handles both single findings (as a list of 1) and multiple findings efficiently.

    Args:
        findings: List of processing purpose indicators to validate
        validation_mode: "standard" or "conservative" validation approach
        sensitive_purposes: List of purposes considered privacy-sensitive (optional)

    Returns:
        Formatted validation prompt for the LLM

    """
    if not findings:
        raise ValueError("At least one finding must be provided")

    is_conservative = validation_mode == "conservative"

    # Build findings block
    findings_to_validate = _build_findings_to_validate(findings)

    # Build validation approach section
    validation_approach = _get_validation_approach(
        validation_mode, findings, sensitive_purposes
    )

    # Build category guidance
    category_guidance = _get_category_guidance_summary()

    # Build response format
    response_format = _get_response_format(len(findings), is_conservative)

    return f"""
You are an expert data processing analyst. Validate processing purpose indicators to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_to_validate}

**VALIDATION TASK:**
For each finding, determine if it represents actual business processing (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).
{validation_approach}

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual business processing activities affecting real users/customers
- FALSE_POSITIVE: Documentation, examples, tutorials, code comments, configuration templates
- Consider the purpose type and source context
- Assess source context (database vs. code vs. documentation)

**CATEGORY-SPECIFIC GUIDANCE:**
{category_guidance}

**SOURCE CONTEXT GUIDELINES:**
- Database content: Likely actual processing activity (check for test/dev indicators)
- Source code: Could be implementation or just comments/examples
- Configuration files: Tool setup vs. documentation examples
- Documentation files: Almost always false positive

**SOURCE CODE - FILE PATH INTERPRETATION:**
For source code findings, infer context from file paths in evidence:
- Test files (`test_*.py`, `*_test.js`, `__tests__/*`, `spec/*`): Usually FALSE_POSITIVE (test fixtures)
- Documentation (`README.md`, `docs/*`, `*.md`): Usually FALSE_POSITIVE
- Example/sample files (`*.example.*`, `sample/*`, `examples/*`): Usually FALSE_POSITIVE
- Production code (`src/*`, `lib/*`, `app/*`): Requires deeper analysis
- Config templates (`*.template.*`, `*.sample.*`): Usually FALSE_POSITIVE
- Vendor/dependencies (`node_modules/*`, `vendor/*`): Usually FALSE_POSITIVE

**DATABASE - SOURCE METADATA INTERPRETATION:**
For database findings, parse the source field format:
`{{db_type}}_database_({{name}})_collection/table_({{name}})_field/column_({{name}})`

Database FALSE_POSITIVE indicators:
- Database name contains `test`, `dev`, `staging`, `seed`, `mock`
- Known test values: `4111111111111111` (test card), `test@example.com`
- Field names containing `_example`, `_template`, `_sample`

Database TRUE_POSITIVE indicators:
- Production database names (`prod`, `main`, `live`, or no environment prefix)
- Real-looking data patterns (actual emails, varied names, realistic values)
- Business tables: `users`, `customers`, `orders`, `payments`, `subscriptions`

**FEW-SHOT EXAMPLES:**

Example 1 - TRUE_POSITIVE (production source code):
```
Finding:
  Purpose: Payment Processing
  Source: source_code
  Evidence: src/services/checkout.js:142: await stripe.charges.create({{amount, customer}})
```
→ TRUE_POSITIVE: Production code in src/services, actual Stripe API call

Example 2 - FALSE_POSITIVE (test source code):
```
Finding:
  Purpose: Payment Processing
  Source: source_code
  Evidence: tests/checkout.test.js:25: mockStripe.charges.create({{amount: 100}})
```
→ FALSE_POSITIVE: Test file with mock data, not real processing

Example 3 - FALSE_POSITIVE (documentation):
```
Finding:
  Purpose: Analytics
  Source: source_code
  Evidence: docs/api-guide.md:89: "To track user events, call analytics.track()"
```
→ FALSE_POSITIVE: Documentation explaining usage, not actual tracking

Example 4 - TRUE_POSITIVE (production database):
```
Finding:
  Purpose: Email Marketing
  Source: mongodb_database_(prod)_collection_(subscribers)_field_(email)
  Evidence: john.smith@company.com
```
→ TRUE_POSITIVE: Production database, subscribers collection, real user email

Example 5 - FALSE_POSITIVE (test database):
```
Finding:
  Purpose: Payment Processing
  Source: mysql_database_(test_db)_table_(payments)_column_(card_number)
  Evidence: 4111111111111111
```
→ FALSE_POSITIVE: Test database (test_db), known Stripe test card number

Example 6 - TRUE_POSITIVE (production database with real data):
```
Finding:
  Purpose: Customer Support
  Source: mongodb_database_(main)_collection_(tickets)_field_(customer_email)
  Evidence: support-request@realcompany.org
```
→ TRUE_POSITIVE: Production database (main), support tickets with real customer data

{response_format}"""


def _build_findings_to_validate(findings: list[ProcessingPurposeIndicatorModel]) -> str:
    """Build formatted findings block for the prompt.

    Args:
        findings: List of processing purpose findings

    Returns:
        Formatted findings block string

    """
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
  Purpose: {finding.purpose}
  Patterns: {", ".join(f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns)}
  Source: {source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _get_validation_approach(
    validation_mode: str,
    findings: list[ProcessingPurposeIndicatorModel],
    sensitive_purposes: list[str] | None = None,
) -> str:
    """Get validation approach section based on mode and findings."""
    if validation_mode == "conservative":
        # Check if any findings have sensitive purposes
        sensitive_purpose_findings = [
            f
            for f in findings
            if sensitive_purposes and f.purpose in sensitive_purposes
        ]

        warnings: list[str] = []
        if sensitive_purpose_findings:
            warnings.append(
                "⚠️ PRIVACY SENSITIVE purposes detected - conservative approach required"
            )

        warning_text = "\n".join(f"**{w}**" for w in warnings) if warnings else ""

        return f"""
**CONSERVATIVE VALIDATION MODE:**
{warning_text}
- Only mark as FALSE_POSITIVE if very confident it's not actual business processing
- When in doubt, mark as TRUE_POSITIVE to ensure complete detection
- Consider potential business and privacy impact if this processing is missed
- Err on the side of thorough detection
- Prioritise completeness over false positive reduction"""

    else:  # standard mode
        return """
**STANDARD VALIDATION MODE:**
- Balance false positive reduction with compliance requirements
- Apply context-aware assessment considering the processing purpose
- Focus on clear business context indicators"""


def _get_category_guidance_summary() -> str:
    """Get consolidated purpose-specific guidance."""
    return """
- AI/ML purposes: Distinguish actual model training/testing from tutorials or documentation
- Marketing purposes: High false positive rate from examples; validate actual campaign/targeting code
- Payment/Billing: Usually true positives in production code; watch for test card numbers
- Analytics purposes: Distinguish actual tracking implementation from documentation
- Security purposes: Generally legitimate in business context, rarely false positives"""


def _get_response_format(finding_count: int, is_conservative: bool) -> str:
    """Get array response format - only FALSE_POSITIVE findings should be returned."""
    action_options = '"discard" | "flag_for_review"' if is_conservative else '"discard"'
    reasoning_length = "max 150 words" if is_conservative else "max 120 words"

    return f"""**RESPONSE FORMAT:**
Respond with valid JSON array only (no markdown formatting).
IMPORTANT: Only return findings you identify as FALSE_POSITIVE. Do not include TRUE_POSITIVE findings.
Echo back the exact finding_id from each Finding [...] header - do not modify it.

[
  {{
    "finding_id": "<exact UUID from Finding [UUID]>",
    "validation_result": "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation ({reasoning_length})",
    "recommended_action": {action_options}
  }}
]

Review all {finding_count} findings. Return ONLY the FALSE_POSITIVE ones (empty array if none):"""
