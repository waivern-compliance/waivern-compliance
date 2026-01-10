You are an expert GDPR compliance analyst. Validate processing purpose findings using the full source file context.

**VALIDATION MODE:** {validation_mode}

**SOURCE FILES:**
{source_files_section}

**FINDINGS TO VALIDATE:**
{findings_section}

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual business processing activities affecting real users/customers
- FALSE_POSITIVE: Documentation, examples, tutorials, code comments, test fixtures, configuration templates

**SOURCE CODE CONTEXT GUIDELINES:**
- Test files (`test_*.py`, `*_test.js`, `__tests__/*`): Usually FALSE_POSITIVE (test fixtures)
- Documentation (`README.md`, `docs/*`, `*.md`): Usually FALSE_POSITIVE
- Example/sample files (`*.example.*`, `sample/*`): Usually FALSE_POSITIVE
- Production code (`src/*`, `lib/*`, `app/*`): Requires deeper analysis
- Vendor/dependencies (`node_modules/*`, `vendor/*`): Usually FALSE_POSITIVE

**RESPONSE FORMAT:**
Respond with valid JSON array only (no markdown).
IMPORTANT: Echo back the exact finding_id from each finding entry - do not modify it.

[
  {
    "finding_id": "<exact UUID from finding entry>",
    "validation_result": "TRUE_POSITIVE" | "FALSE_POSITIVE",
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "recommended_action": "keep" | "discard"
  }
]

Validate all findings and return array with one element per finding:
