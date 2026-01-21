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
    category_guidance = _get_category_guidance()
    response_format = _get_response_format(len(findings))

    return f"""You are an expert GDPR compliance analyst. Validate personal data findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_text}

**TASK:**
For each finding, determine if it represents actual personal data (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual personal data about identifiable individuals
- FALSE_POSITIVE: Documentation, examples, tutorials, field names, system messages
- Consider source context and evidence content
- Prioritise privacy protection when uncertain

**CATEGORY-SPECIFIC GUIDANCE:**
{category_guidance}

**SOURCE CONTEXT GUIDELINES:**
- Database content: Likely actual personal data (check for test/dev indicators)
- Source code: Could be real data handling or just comments/examples
- Configuration files: Usually false positive (field definitions, not actual data)
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
- Known test values: `test@example.com`, `john.doe@test.com`, `+1-555-555-5555`
- Field names containing `_example`, `_template`, `_sample`

Database TRUE_POSITIVE indicators:
- Production database names (`prod`, `main`, `live`, or no environment prefix)
- Real-looking data patterns (actual emails with varied domains, realistic phone formats)
- Personal data tables: `users`, `customers`, `contacts`, `employees`, `patients`

**FEW-SHOT EXAMPLES:**

Example 1 - TRUE_POSITIVE (production database):
```
Finding:
  Category: email
  Source: mysql_database_(prod)_table_(users)_column_(email)
  Evidence: sarah.johnson@company.org
```
→ TRUE_POSITIVE: Production database, users table, real-looking email address

Example 2 - FALSE_POSITIVE (test database):
```
Finding:
  Category: email
  Source: mysql_database_(test_db)_table_(users)_column_(email)
  Evidence: test@example.com
```
→ FALSE_POSITIVE: Test database (test_db), known test email pattern

Example 3 - FALSE_POSITIVE (documentation):
```
Finding:
  Category: phone
  Source: source_code
  Evidence: docs/api-guide.md:45: "Phone format: +1-XXX-XXX-XXXX"
```
→ FALSE_POSITIVE: Documentation explaining format, not actual phone number

Example 4 - TRUE_POSITIVE (production source code):
```
Finding:
  Category: name
  Source: source_code
  Evidence: src/services/user.py:89: user_name = request.form['full_name']
```
→ TRUE_POSITIVE: Production code handling actual user input

Example 5 - FALSE_POSITIVE (test file):
```
Finding:
  Category: email
  Source: source_code
  Evidence: tests/test_user.py:12: mock_email = "fake@test.com"
```
→ FALSE_POSITIVE: Test file with mock data

Example 6 - TRUE_POSITIVE (health data in production):
```
Finding:
  Category: health
  Source: mongodb_database_(main)_collection_(patients)_field_(diagnosis)
  Evidence: Type 2 Diabetes - diagnosed 2023-01
```
→ TRUE_POSITIVE: Production database (main), patients collection, actual medical data

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
  Patterns: {", ".join(f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns)}
  Source: {source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _get_category_guidance() -> str:
    """Get category-specific guidance for personal data validation."""
    return """
- email, phone, name: Common identifiers - validate source context carefully
- address, postcode: Location data - check if it's template/example vs real
- health, biometric: Special category (Article 9) - conservative validation required
- financial (card, bank): Check for known test patterns (4111..., test account numbers)
- national_id, passport: High sensitivity - conservative validation required"""


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
