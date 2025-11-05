# Step 9: Extract Schema Version Logic to Reader/Producer Modules

**Phase:** 3 - Proof of Concept Component
**Dependencies:** Step 8 complete
**Estimated Scope:** Extract and refactor version-specific logic

## Purpose

Extract version-specific input/output handling logic from PersonalDataAnalyser into separate reader and producer modules. This isolates version differences and makes them explicit.

## Current State

PersonalDataAnalyser has version-specific logic embedded in the main `process()` method:
- Input handling mixed with analysis logic
- Output formatting mixed with analysis logic
- No clear separation between versions

## Target State

Version-specific logic in separate modules:
- `schema_readers/standard_input_1_0_0.py` - Handles reading standard_input v1.0.0
- `schema_producers/personal_data_finding_1_0_0.py` - Handles producing personal_data_finding v1.0.0

## Implementation

### 1. Create Input Reader Module

Create `schema_readers/standard_input_1_0_0.py`:

```python
"""Reader for standard_input schema version 1.0.0."""

from typing import Any


def read(content: dict[str, Any]) -> dict[str, Any]:
    """Transform standard_input v1.0.0 data to internal format.

    Args:
        content: Data conforming to standard_input v1.0.0 schema

    Returns:
        Data in analyser's internal format with:
        - source: str
        - data: list of items with content and metadata
        - name: str
        - description: str | None
    """
    # Extract relevant fields from standard_input schema
    return {
        "source": content.get("source", ""),
        "name": content.get("name", ""),
        "description": content.get("description"),
        "data": content.get("data", []),
        "schemaVersion": content.get("schemaVersion", ""),
    }
```

**Key points:**
- Keep transformation simple - just extract needed fields
- Return dictionary in analyser's internal format
- Document expected input and output structure

### 2. Create Output Producer Module

Create `schema_producers/personal_data_finding_1_0_0.py`:

```python
"""Producer for personal_data_finding schema version 1.0.0."""

from typing import Any


def produce(internal_result: dict[str, Any]) -> dict[str, Any]:
    """Transform internal result to personal_data_finding v1.0.0 format.

    Args:
        internal_result: Analysis result in internal format with:
        - findings: list of personal data findings
        - summary: summary statistics
        - metadata: analysis metadata

    Returns:
        Data conforming to personal_data_finding v1.0.0 schema
    """
    findings = internal_result.get("findings", [])
    summary = internal_result.get("summary", {})
    metadata = internal_result.get("metadata", {})

    # Format according to personal_data_finding v1.0.0 schema
    return {
        "findings": [
            {
                "field_name": f.get("field_name"),
                "data_category": f.get("data_category"),
                "confidence_score": f.get("confidence_score"),
                "detection_method": f.get("detection_method"),
                "evidence": f.get("evidence", {}),
                "metadata": f.get("metadata", {}),
            }
            for f in findings
        ],
        "summary": {
            "total_fields_analyzed": summary.get("total_fields_analyzed", 0),
            "personal_data_fields_found": summary.get(
                "personal_data_fields_found", 0
            ),
            "data_categories_found": summary.get("data_categories_found", []),
        },
        "metadata": {
            "analysis_timestamp": metadata.get("analysis_timestamp"),
            "analyser_version": metadata.get("analyser_version"),
            "pattern_matching_enabled": metadata.get("pattern_matching_enabled"),
            "llm_validation_enabled": metadata.get("llm_validation_enabled"),
        },
    }
```

**Key points:**
- Transform internal result to schema-compliant format
- Handle all required fields for the schema version
- Use defensive `.get()` to handle missing fields gracefully

### 3. Define Internal Format

Document the analyser's internal format (add to analyser.py docstring):

```python
"""PersonalDataAnalyser - Detects personal data in input.

Internal Data Format:
--------------------
Input (from readers):
{
    "source": str,
    "name": str,
    "data": [{"content": str, "metadata": dict}],
    "description": str | None,
}

Output (to producers):
{
    "findings": [
        {
            "field_name": str,
            "data_category": str,
            "confidence_score": float,
            "detection_method": str,
            "evidence": dict,
            "metadata": dict,
        }
    ],
    "summary": {
        "total_fields_analyzed": int,
        "personal_data_fields_found": int,
        "data_categories_found": list[str],
    },
    "metadata": {
        "analysis_timestamp": str,
        "analyser_version": str,
        "pattern_matching_enabled": bool,
        "llm_validation_enabled": bool,
    },
}
"""
```

## Testing

### Unit Test Reader

Create `libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/schema_readers/test_standard_input_1_0_0.py`:

```python
"""Tests for standard_input v1.0.0 reader."""
from waivern_personal_data_analyser.schema_readers import standard_input_1_0_0


def test_read_transforms_standard_input():
    """Test reader transforms standard_input data correctly."""
    input_data = {
        "source": "test_db",
        "name": "test_data",
        "data": [{"content": "test@email.com", "metadata": {}}],
        "description": "Test data",
        "schemaVersion": "1.0.0",
    }

    result = standard_input_1_0_0.read(input_data)

    assert result["source"] == "test_db"
    assert result["name"] == "test_data"
    assert len(result["data"]) == 1
```

### Unit Test Producer

Create `libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/schema_producers/test_personal_data_finding_1_0_0.py`:

```python
"""Tests for personal_data_finding v1.0.0 producer."""
from waivern_personal_data_analyser.schema_producers import (
    personal_data_finding_1_0_0,
)


def test_produce_formats_findings():
    """Test producer formats internal result correctly."""
    internal_result = {
        "findings": [
            {
                "field_name": "email",
                "data_category": "email_address",
                "confidence_score": 0.95,
                "detection_method": "pattern",
                "evidence": {},
                "metadata": {},
            }
        ],
        "summary": {
            "total_fields_analyzed": 10,
            "personal_data_fields_found": 1,
            "data_categories_found": ["email_address"],
        },
        "metadata": {},
    }

    result = personal_data_finding_1_0_0.produce(internal_result)

    assert "findings" in result
    assert len(result["findings"]) == 1
    assert result["findings"][0]["field_name"] == "email"
```

Run tests:
```bash
cd libs/waivern-personal-data-analyser
uv run pytest tests/waivern_personal_data_analyser/schema_readers/ -v
uv run pytest tests/waivern_personal_data_analyser/schema_producers/ -v
```

## Key Decisions

**Internal format:**
- Define clear internal format for the analyser
- Readers transform TO internal format
- Producers transform FROM internal format
- Keeps core analysis logic version-agnostic

**Error handling:**
- Use defensive `.get()` with defaults
- Reader/producer shouldn't raise exceptions for missing optional fields
- Let schema validation catch structural issues

**Module structure:**
- One module per schema version
- Modules are completely independent
- Easy to add new versions without touching old ones

## Files Created

- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_readers/standard_input_1_0_0.py`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_producers/personal_data_finding_1_0_0.py`
- `libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/schema_readers/test_standard_input_1_0_0.py`
- `libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/schema_producers/test_personal_data_finding_1_0_0.py`

## Notes

- Actual logic needs to match existing PersonalDataAnalyser behavior
- May need to refactor analyser to expose internal format better
- Test both reader and producer in isolation before integration
- Next step: Update analyser to use dynamic loading
