"""LLM validation prompts for data subject findings validation."""

from waivern_data_subject_analyser.schemas import DataSubjectIndicatorModel


def get_data_subject_validation_prompt(
    findings: list[DataSubjectIndicatorModel],
    validation_mode: str = "standard",
) -> str:
    """Generate validation prompt for data subject findings.

    Args:
        findings: List of data subject findings to validate
        validation_mode: "standard" or "conservative" validation approach

    Returns:
        Formatted validation prompt for the LLM

    """
    if not findings:
        raise ValueError("At least one finding must be provided")

    findings_text = _build_findings_block(findings)
    category_guidance = _get_category_guidance()
    response_format = _get_response_format(len(findings))

    return f"""You are an expert data protection analyst. Validate data subject findings to identify false positives.

**FINDINGS TO VALIDATE:**
{findings_text}

**TASK:**
For each finding, determine if it represents an actual data subject indicator (TRUE_POSITIVE) or a false positive (FALSE_POSITIVE).

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Pattern appears in schema/code that actually stores or references data subjects
- FALSE_POSITIVE: Pattern appears in comments, documentation, or unrelated context
- **CRITICAL: Always analyse the Source field to determine context (database type, collection/table names, file paths). Source context is essential for accurate validation.**
- Prioritise compliance safety when uncertain

**CATEGORY-SPECIFIC GUIDANCE:**
{category_guidance}

**SOURCE CONTEXT GUIDELINES:**
- Database content: Likely actual data subject storage (check for test/dev indicators)
- Source code: Could be data model definition or just comments/examples
- Configuration files: Usually false positive (schema definitions, not actual subjects)
- Documentation files: Almost always false positive

**SOURCE CODE - FILE PATH INTERPRETATION:**
For source code findings, infer context from file paths in evidence:
- Test files (`test_*.py`, `*_test.js`, `__tests__/*`, `spec/*`): Usually FALSE_POSITIVE (test fixtures)
- Documentation (`README.md`, `docs/*`, `*.md`): Usually FALSE_POSITIVE
- Example/sample files (`*.example.*`, `sample/*`, `examples/*`): Usually FALSE_POSITIVE
- Model/Entity files (`models/*`, `entities/*`, `schemas/*`): Requires deeper analysis
- Migration files (`migrations/*`, `alembic/*`): Usually TRUE_POSITIVE (actual schema)
- Vendor/dependencies (`node_modules/*`, `vendor/*`): Usually FALSE_POSITIVE

**DATABASE - SOURCE METADATA INTERPRETATION:**
For database findings, parse the source field format:
`{{db_type}}_database_({{name}})_collection/table_({{name}})_field/column_({{name}})`

Database FALSE_POSITIVE indicators:
- Database name contains `test`, `dev`, `staging`, `seed`, `mock`
- Table names like `_example`, `_template`, `_sample`, `_backup`
- Clearly synthetic data patterns

Database TRUE_POSITIVE indicators:
- Production database names (`prod`, `main`, `live`, or no environment prefix)
- Core business tables: `users`, `customers`, `employees`, `patients`, `subscribers`
- Foreign key relationships to person tables

**FEW-SHOT EXAMPLES:**

Example 1 - TRUE_POSITIVE (production database table):
```
Finding:
  Subject Category: Customer
  Source: mysql_database_(prod)_table_(customers)_column_(customer_id)
  Evidence: Table contains 50,000 rows with customer data
```
→ TRUE_POSITIVE: Production database, customers table, actual customer records

Example 2 - FALSE_POSITIVE (test database):
```
Finding:
  Subject Category: Employee
  Source: mysql_database_(test_db)_table_(employees)_column_(employee_id)
  Evidence: Table contains 5 rows of test data
```
→ FALSE_POSITIVE: Test database (test_db), likely test fixtures

Example 3 - FALSE_POSITIVE (documentation):
```
Finding:
  Subject Category: Patient
  Source: source_code
  Evidence: docs/data-model.md:78: "The Patient entity stores healthcare records"
```
→ FALSE_POSITIVE: Documentation describing the data model, not actual data

Example 4 - TRUE_POSITIVE (production model definition):
```
Finding:
  Subject Category: Subscriber
  Source: source_code
  Evidence: src/models/subscriber.py:15: class Subscriber(BaseModel): email = Column(String)
```
→ TRUE_POSITIVE: Production code defining actual subscriber data model

Example 5 - FALSE_POSITIVE (test fixture):
```
Finding:
  Subject Category: User
  Source: source_code
  Evidence: tests/fixtures/users.json:1: {{"name": "Test User", "email": "test@example.com"}}
```
→ FALSE_POSITIVE: Test fixture file with mock data

Example 6 - TRUE_POSITIVE (migration file):
```
Finding:
  Subject Category: Employee
  Source: source_code
  Evidence: migrations/003_add_employees.py:8: op.create_table('employees', Column('id', Integer))
```
→ TRUE_POSITIVE: Database migration creating actual employee table

{response_format}"""


def _build_findings_block(findings: list[DataSubjectIndicatorModel]) -> str:
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
  Subject Category: {finding.subject_category}
  Patterns: {", ".join(f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns)}
  Source: {source}
  Evidence:
  {evidence_text}""")

    return "\n".join(findings_text)


def _get_category_guidance() -> str:
    """Get category-specific guidance for data subject validation."""
    return """
- Customer, Client: Core business subjects - validate source context carefully
- Employee, Staff, Worker: Internal subjects - check HR system vs documentation
- Patient, Healthcare: Sensitive subjects (health data) - conservative validation required
- Subscriber, Member: Marketing/service subjects - check for actual subscription data
- Student, Learner: Educational subjects - validate educational context
- Citizen, Resident: Government/public sector subjects - conservative validation required"""


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
