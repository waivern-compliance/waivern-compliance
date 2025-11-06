# Step 10: Update PersonalDataAnalyser to Use Dynamic Loading

**Phase:** 3 - Proof of Concept Component
**Dependencies:** Step 9 complete
**Status:** ✅ COMPLETED
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

## Actual Implementation

```python
class PersonalDataAnalyser(Analyser):
    # No manual caching needed - Python's sys.modules handles it
    # Hardcoded schema lists removed - inherited auto-discovery from base class

    def process(self, input_schema, output_schema, message):
        # Dynamically load reader for input schema
        reader = self._load_reader(input_schema)
        typed_data = reader.read(message.content)

        # Process each data item using pattern matcher (existing logic)
        findings: list[PersonalDataFindingModel] = []
        for data_item in typed_data.data:
            content = data_item.content
            item_metadata = data_item.metadata
            item_findings = self._pattern_matcher.find_patterns(content, item_metadata)
            findings.extend(item_findings)

        # Run LLM validation if enabled
        validated_findings = self._validate_findings_with_llm(findings)

        # Update analysis chain
        updated_chain_dicts = self.update_analyses_chain(message, "personal_data_analyser")
        updated_chain = [AnalysisChainEntry(**entry) for entry in updated_chain_dicts]

        # Create output using producer
        return self._create_output_message(
            findings, validated_findings, output_schema, updated_chain
        )

    def _load_reader(self, schema: Schema) -> ModuleType:
        """Dynamically import reader module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.
        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_personal_data_analyser.schema_readers.{module_name}"
        )

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module.

        Python's import system automatically caches modules in sys.modules,
        so repeated imports are fast and don't require manual caching.
        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_personal_data_analyser.schema_producers.{module_name}"
        )

    def _create_output_message(
        self,
        original_findings: list[PersonalDataFindingModel],
        validated_findings: list[PersonalDataFindingModel],
        output_schema: Schema,
        analyses_chain: list[AnalysisChainEntry],
    ) -> Message:
        """Create output message using producer."""
        # Build summary and validation summary
        summary = self._build_findings_summary(validated_findings)
        validation_summary = None
        if self._config.llm_validation.enable_llm_validation and len(original_findings) > 0:
            validation_summary = self._build_validation_summary(original_findings, validated_findings)

        # Build analysis metadata
        analysis_metadata = BaseAnalysisOutputMetadata(
            ruleset_used=self._config.pattern_matching.ruleset,
            llm_validation_enabled=self._config.llm_validation.enable_llm_validation,
            evidence_context_size=self._config.pattern_matching.evidence_context_size,
            analyses_chain=analyses_chain,
        )

        # Load producer and transform to wire format
        producer = self._load_producer(output_schema)
        result_data = producer.produce(
            findings=validated_findings,
            summary=summary,
            analysis_metadata=analysis_metadata,
            validation_summary=validation_summary,
        )

        # Create and validate output message
        output_message = Message(
            id="Personal_data_analysis",
            content=result_data,
            schema=output_schema,
        )
        output_message.validate()
        return output_message
```

## Implementation Steps Completed

### 1. Added Import

```python
import importlib
from types import ModuleType
```

### 2. Removed Hardcoded Schema Lists

Deleted class attributes and override methods - now uses inherited auto-discovery from base `Analyser` class.

### 3. ~~Added Module Caches~~ **Removed Manual Caching**

**Key Learning:** Manual caching is unnecessary because Python's `importlib.import_module()` automatically caches modules in `sys.modules`. This also eliminates test isolation issues.

### 4. Added Dynamic Loading Methods

Implemented simplified `_load_reader()` and `_load_producer()` without manual caching:

```python
def _load_reader(self, schema: Schema) -> ModuleType:
    """Dynamically import reader module."""
    module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
    return importlib.import_module(
        f"waivern_personal_data_analyser.schema_readers.{module_name}"
    )

def _load_producer(self, schema: Schema) -> ModuleType:
    """Dynamically import producer module."""
    module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
    return importlib.import_module(
        f"waivern_personal_data_analyser.schema_producers.{module_name}"
    )
```

### 5. Updated Process Method

Modified `process()` to use reader for input transformation:
```python
reader = self._load_reader(input_schema)
typed_data = reader.read(message.content)
```

### 6. Updated Output Creation

Modified `_create_output_message()` to use producer for output transformation:
```python
producer = self._load_producer(output_schema)
result_data = producer.produce(
    findings=validated_findings,
    summary=summary,
    analysis_metadata=analysis_metadata,
    validation_summary=validation_summary,
)
```

## Testing

### New Tests Added

Added 2 focused tests to verify dynamic loading mechanism:

#### 1. Test Reader Module Loading
```python
def test_reader_module_is_loaded_dynamically(
    self,
    valid_config: PersonalDataAnalyserConfig,
    mock_llm_service: Mock,
    sample_input_message: Message,
    mock_schema_modules: tuple[Mock, Mock],
) -> None:
    """Test that reader module is dynamically loaded for input schema."""
    analyser = PersonalDataAnalyser(valid_config, mock_llm_service)
    mock_reader, mock_producer = mock_schema_modules

    with patch("importlib.import_module") as mock_import:
        def import_side_effect(module_name: str) -> Mock:
            if "schema_readers" in module_name:
                return mock_reader
            elif "schema_producers" in module_name:
                return mock_producer
            return Mock()

        mock_import.side_effect = import_side_effect

        analyser.process(
            Schema("standard_input", "1.0.0"),
            Schema("personal_data_finding", "1.0.0"),
            sample_input_message,
        )

        # Verify reader module was dynamically imported
        mock_import.assert_any_call(
            "waivern_personal_data_analyser.schema_readers.standard_input_1_0_0"
        )
```

#### 2. Test Producer Module Loading
```python
def test_producer_module_is_loaded_dynamically(
    self,
    valid_config: PersonalDataAnalyserConfig,
    mock_llm_service: Mock,
    sample_input_message: Message,
    mock_schema_modules: tuple[Mock, Mock],
) -> None:
    """Test that producer module is dynamically loaded for output schema."""
    # Similar structure, verifies producer import
    mock_import.assert_any_call(
        "waivern_personal_data_analyser.schema_producers.personal_data_finding_1_0_0"
    )
```

#### Test Fixture for Mock Setup

Created pytest fixture to eliminate test duplication:
```python
@pytest.fixture
def mock_schema_modules(self) -> tuple[Mock, Mock]:
    """Create mock reader and producer modules for testing dynamic loading."""
    mock_reader = Mock()
    mock_reader.read.return_value = Mock(
        data=[],
        schemaVersion="1.0.0",
        name="test",
        description=None,
        contentEncoding=None,
        source=None,
        metadata={},
    )

    mock_producer = Mock()
    mock_producer.produce.return_value = {
        "findings": [],
        "summary": {
            "total_findings": 0,
            "high_risk_count": 0,
            "special_category_count": 0,
        },
        "analysis_metadata": {...},
    }

    return mock_reader, mock_producer
```

### Test Results

```bash
./scripts/dev-checks.sh
```

Results:
- ✅ **All 900 tests pass** (18 existing analyser tests + 2 new = 20 analyser tests total)
- ✅ **All 18 existing tests still pass** - Full backward compatibility maintained
- ✅ **0 type errors, 0 warnings**
- ✅ **Dynamic loading verified** - Reader and producer modules loaded correctly
- ✅ **No test isolation issues** - Removed manual caching eliminated shared state problems

## Key Decisions and Learnings

**No Manual Caching Needed:**
- ❌ Initially added class-level `_reader_cache` and `_producer_cache` dictionaries
- ✅ **Removed after learning:** Python's `importlib.import_module()` automatically caches in `sys.modules`
- ✅ **Benefit:** Simpler code, no test isolation issues, follows Python idioms
- ✅ **Lesson:** Check if framework/language already provides the optimization before adding it

**Error Handling:**
- Let `importlib.import_module()` raise `ModuleNotFoundError` naturally if module doesn't exist
- Clear error message: "No module named 'waivern_personal_data_analyser.schema_readers.standard_input_2_0_0'"
- Indicates missing version support - directs developer to create the missing reader/producer

**Test Design:**
- ❌ Initially cleared caches manually in each test (accessed private attributes)
- ✅ **Improved:** Removed manual caching, eliminating the need for cache clearing
- ✅ **Benefit:** Tests don't need to know about internal implementation details
- ✅ **Lesson:** If tests need to access private state, the design likely needs improvement

**Test Quality:**
- Created pytest fixture `mock_schema_modules` to eliminate 135 lines of duplication across 3 tests
- ✅ **Reduced from 195 lines to 125 lines** (36% reduction)
- ✅ **Single source of truth** for mock setup
- ✅ **Lesson:** Use fixtures for shared test setup, not manual copy-paste

**Schema Auto-Discovery:**
- Analyser now inherits `get_supported_input_schemas()` and `get_supported_output_schemas()` from base class
- File presence in `schema_readers/` and `schema_producers/` declares version support
- No manual schema list maintenance required

## Files Modified

- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/analyser.py` - Added dynamic loading methods, updated process flow
- `libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/test_analyser.py` - Added 2 tests + fixture for dynamic loading

## Notes

- ✅ **Phase 3 (Proof of Concept) COMPLETE!**
- ✅ PersonalDataAnalyser now demonstrates the full reader/producer pattern
- ✅ Schema versioning architecture validated with Pydantic models
- ✅ Pattern established for other analysers to follow
- ✅ Important lessons learned about Python caching and test design
- ✅ Code is production-ready: clean, tested, type-safe
- 📋 **Next: Executor version matching (Phase 4)**

## Related Documentation

- **Step 9:** [Extract Schema Logic to Modules](step_9_extract_schema_logic_to_modules.md) - Reader/Producer implementation
- **Decision Doc:** [Schema Versioning with Pydantic Models](../schema-versioning-pydantic-models.md) - Canonical model + adapter pattern
- **Base Class:** `libs/waivern-core/src/waivern_core/base_analyser.py` - Auto-discovery implementation
