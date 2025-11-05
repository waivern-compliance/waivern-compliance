# Step 10: Update PersonalDataAnalyser to Use Dynamic Loading

**Phase:** 3 - Proof of Concept Component
**Dependencies:** Step 9 complete
**Estimated Scope:** Refactor main analyser class

## Purpose

Update PersonalDataAnalyser to dynamically load reader/producer modules based on schema versions. Remove hardcoded version support lists and use auto-discovery.

## Current Implementation

```python
class PersonalDataAnalyser(Analyser):
    _SUPPORTED_INPUT_SCHEMAS = [Schema("standard_input", "1.0.0")]
    _SUPPORTED_OUTPUT_SCHEMAS = [Schema("personal_data_finding", "1.0.0")]

    @classmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        return cls._SUPPORTED_INPUT_SCHEMAS

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return cls._SUPPORTED_OUTPUT_SCHEMAS

    def process(self, input_schema, output_schema, message):
        # Hardcoded input/output handling
        data = message.content  # Assume specific format
        # ... analysis logic ...
        return Message(schema=output_schema, content=results)
```

## Target Implementation

```python
class PersonalDataAnalyser(Analyser):
    # Module caches for performance
    _reader_cache: dict[str, Any] = {}
    _producer_cache: dict[str, Any] = {}

    # Remove hardcoded lists - use inherited auto-discovery

    def process(self, input_schema, output_schema, message):
        # Dynamically load reader for input schema
        reader = self._load_reader(input_schema)
        internal_data = reader.read(message.content)

        # Perform version-agnostic analysis
        internal_result = self._analyze(internal_data)

        # Dynamically load producer for output schema
        producer = self._load_producer(output_schema)
        output_content = producer.produce(internal_result)

        return Message(schema=output_schema, content=output_content)

    def _load_reader(self, schema: Schema):
        """Dynamically import and cache reader module."""
        cache_key = f"{schema.name}_{schema.version.replace('.', '_')}"

        if cache_key not in self._reader_cache:
            module_name = cache_key
            self._reader_cache[cache_key] = importlib.import_module(
                f".schema_readers.{module_name}",
                package=__package__
            )

        return self._reader_cache[cache_key]

    def _load_producer(self, schema: Schema):
        """Dynamically import and cache producer module."""
        cache_key = f"{schema.name}_{schema.version.replace('.', '_')}"

        if cache_key not in self._producer_cache:
            module_name = cache_key
            self._producer_cache[cache_key] = importlib.import_module(
                f".schema_producers.{module_name}",
                package=__package__
            )

        return self._producer_cache[cache_key]

    def _analyze(self, internal_data: dict) -> dict:
        """Version-agnostic core analysis logic.

        Args:
            internal_data: Data in internal format from reader

        Returns:
            Analysis result in internal format for producer
        """
        # Move existing analysis logic here
        # Should work with internal format, not specific schema versions
        pass
```

## Implementation Steps

### 1. Add Import

```python
import importlib
from typing import Any
```

### 2. Remove Hardcoded Schema Lists

Delete these class attributes:
```python
_SUPPORTED_INPUT_SCHEMAS = [...]  # DELETE
_SUPPORTED_OUTPUT_SCHEMAS = [...]  # DELETE
```

Delete these methods (inherited from base class):
```python
@classmethod
def get_supported_input_schemas(cls) -> list[Schema]:  # DELETE
    return cls._SUPPORTED_INPUT_SCHEMAS

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:  # DELETE
    return cls._SUPPORTED_OUTPUT_SCHEMAS
```

### 3. Add Module Caches

```python
# Add at class level
_reader_cache: dict[str, Any] = {}
_producer_cache: dict[str, Any] = {}
```

### 4. Add Dynamic Loading Methods

Implement `_load_reader()` and `_load_producer()` as shown above.

### 5. Refactor Core Analysis Logic

Extract version-agnostic analysis into `_analyze()` method:
```python
def _analyze(self, internal_data: dict) -> dict:
    """Core analysis logic working with internal format."""
    # Pattern matching
    findings = []
    for item in internal_data["data"]:
        matches = self._pattern_match(item["content"])
        if matches:
            findings.append({
                "field_name": item["metadata"].get("field_name", ""),
                "data_category": matches[0]["category"],
                "confidence_score": matches[0]["confidence"],
                "detection_method": "pattern",
                "evidence": {"patterns": matches},
                "metadata": item["metadata"],
            })

    # LLM validation if enabled
    if self.config.enable_llm_validation:
        findings = self._llm_validate(findings)

    # Build summary
    summary = {
        "total_fields_analyzed": len(internal_data["data"]),
        "personal_data_fields_found": len(findings),
        "data_categories_found": list(set(f["data_category"] for f in findings)),
    }

    return {
        "findings": findings,
        "summary": summary,
        "metadata": self._build_metadata(),
    }
```

### 6. Update Process Method

```python
def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message:
    """Process message using dynamic reader/producer loading."""
    # Load appropriate reader
    reader = self._load_reader(input_schema)
    internal_data = reader.read(message.content)

    # Version-agnostic analysis
    internal_result = self._analyze(internal_data)

    # Load appropriate producer
    producer = self._load_producer(output_schema)
    output_content = producer.produce(internal_result)

    return Message(
        schema=output_schema,
        content=output_content,
    )
```

## Testing

### Integration Tests

Update existing tests to verify auto-discovery works:

```python
def test_auto_discovery_works():
    """Test that schemas are auto-discovered from directories."""
    analyser = PersonalDataAnalyser(config=...)

    input_schemas = analyser.get_supported_input_schemas()
    assert Schema("standard_input", "1.0.0") in input_schemas

    output_schemas = analyser.get_supported_output_schemas()
    assert Schema("personal_data_finding", "1.0.0") in output_schemas


def test_dynamic_loading_works():
    """Test that reader/producer are loaded dynamically."""
    analyser = PersonalDataAnalyser(config=...)

    input_message = Message(
        schema=Schema("standard_input", "1.0.0"),
        content={...},
    )

    result = analyser.process(
        input_schema=Schema("standard_input", "1.0.0"),
        output_schema=Schema("personal_data_finding", "1.0.0"),
        message=input_message,
    )

    assert result.schema == Schema("personal_data_finding", "1.0.0")
    assert "findings" in result.content
```

### Run All Tests

```bash
cd libs/waivern-personal-data-analyser
./scripts/dev-checks.sh
```

Expected:
- ✅ All tests pass
- ✅ Auto-discovery works
- ✅ Dynamic loading works
- ✅ Module caching works

## Key Decisions

**Module cache:**
- Class-level dictionary for caching
- Persists across instances of analyser
- Keyed by `{schema_name}_{version}` string

**Error handling:**
- Let `importlib.import_module()` raise if module not found
- Clear error message: "Module schema_readers/standard_input_1_0_0.py not found"
- Indicates missing version support

**Internal format:**
- Core analysis logic uses internal format
- Decoupled from schema versions
- Makes adding new versions easier

## Files Modified

- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/analyser.py`

## Notes

- This completes Phase 3 (Proof of Concept)!
- PersonalDataAnalyser now demonstrates the full pattern
- Other components can follow this same pattern
- This establishes the template for Phase 6 migrations
- Next: Executor version matching (Phase 4)
