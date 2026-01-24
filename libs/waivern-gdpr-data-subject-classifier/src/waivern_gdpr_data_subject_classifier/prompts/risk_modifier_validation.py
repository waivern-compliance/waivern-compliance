"""LLM validation prompt for risk modifier detection."""

from waivern_rulesets import RiskModifier

from waivern_gdpr_data_subject_classifier.schemas import GDPRDataSubjectFindingModel


def get_risk_modifier_validation_prompt(
    findings: list[GDPRDataSubjectFindingModel],
    available_modifiers: list[RiskModifier],
) -> str:
    """Generate validation prompt for risk modifier detection.

    Args:
        findings: List of classified GDPR data subject findings to analyse.
        available_modifiers: List of risk modifiers from the ruleset.

    Returns:
        Formatted validation prompt for the LLM.

    Raises:
        ValueError: If findings list is empty.

    """
    if not findings:
        raise ValueError("At least one finding must be provided")

    findings_text = _build_findings_block(findings)
    modifier_definitions = _build_modifier_definitions(available_modifiers)
    response_format = _get_response_format(len(findings))

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


def _build_findings_block(findings: list[GDPRDataSubjectFindingModel]) -> str:
    """Build formatted findings block for the prompt."""
    findings_text: list[str] = []

    for finding in findings:
        evidence_text = (
            "\n  ".join(f"- {evidence.content}" for evidence in finding.evidence)
            if finding.evidence
            else "No evidence"
        )

        findings_text.append(f"""
Finding [{finding.id}]:
  Data Subject Category: {finding.data_subject_category}
  Source: {finding.metadata.source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _build_modifier_definitions(modifiers: list[RiskModifier]) -> str:
    """Build modifier definitions section from ruleset."""
    if not modifiers:
        return "No specific modifiers defined - use general GDPR risk assessment."

    definitions: list[str] = []
    for modifier in modifiers:
        articles = ", ".join(modifier.article_references)
        definitions.append(f"- **{modifier.modifier}** ({articles})")

    return "\n".join(definitions)


def _get_response_format(finding_count: int) -> str:
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
