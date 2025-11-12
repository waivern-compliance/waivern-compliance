# Task: Update Main Analyser to Handle Dict

- **Phase:** 4 - Fix ProcessingPurposeAnalyser Schema Coupling
- **Status:** TODO
- **Prerequisites:** Step 13 (Handler uses dict) and Step 14 (Reader returns dict) complete
- **Step:** 15 of 17

## Context

This is part of removing hardcoded dependencies on SourceCodeAnalyser's typed Pydantic models. Steps 13-14 updated the handler and reader to work with dicts. Now we need to update the main analyser to complete the end-to-end dict-based flow.

**See:** the parent implementation plan (`docs/development/active/phase_04_fix_processing_purpose_analyser_schema_coupling.md`) for full context.

## Purpose

Update `ProcessingPurposeAnalyser` main analyser to remove SourceCodeDataModel import and ensure `_process_source_code_data()` works correctly with TypedDict-based data from the reader (Step 14) and handler (Step 13). Verify end-to-end integration tests pass with full type safety.

## Problem

Main analyser still imports SourceCodeDataModel:

**Location:** `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py`

**Current approach (line 18):**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel
```

**Usage context:**
- Import exists but may not be actively used in current code
- Reader previously returned typed model, now returns dict
- Need to ensure `_process_source_code_data()` handles dict correctly
- Verify no other references to typed model in analyser

## Solution

Remove import and verify TypedDict-based flow:

**Changes needed:**
1. Remove `from waivern_source_code_analyser.schemas import SourceCodeDataModel`
2. Verify `_process_source_code_data()` works with TypedDict from reader (Step 14)
3. Ensure type hints don't reference Pydantic model from SourceCodeAnalyser
4. Update integration tests to verify end-to-end TypedDict flow with type safety
5. Confirm handler (Step 13) receives TypedDict from reader (Step 14)

## Implementation

### Files to Modify

**1. Analyser source code:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py`

**2. Analyser integration tests:**
`libs/waivern-processing-purpose-analyser/tests/test_analyser.py`

### Code Changes Required

#### 1. Remove Import (line 18)

**Remove:**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel
```

#### 2. Verify _process_source_code_data() Method

**Location:** Around line 100-120 (check current implementation)

**Current expected flow (after Steps 13-14):**
```python
def _process_source_code_data(self, message: Message) -> list[Finding]:
    """Process source code schema data.

    Args:
        message: Message containing source code schema data

    Returns:
        List of findings from source code analysis
    """
    # Load reader (returns TypedDict now, not Pydantic model)
    reader = self._load_reader(message.schema)
    schema_data = reader.read(message)

    # schema_data.data is SourceCodeSchemaDict (TypedDict from Step 13)
    # Type checker validates: SchemaData[SourceCodeSchemaDict]

    # Pass TypedDict to handler (Step 13 expects SourceCodeSchemaDict)
    findings = self._source_code_handler.analyse_source_code_data(schema_data.data)

    return findings
```

**Expected state after Steps 13-14:**
- Reader (Step 14) returns `SchemaData[SourceCodeSchemaDict]` (TypedDict)
- `schema_data.data` is a TypedDict-annotated dict
- Handler (Step 13) accepts `SourceCodeSchemaDict` (TypedDict)
- Type checker validates full flow: Message → Reader → Handler
- No changes needed to this method (should work as-is with TypedDict)

**Verification needed:**
- Confirm no imports of SourceCodeDataModel from waivern-source-code-analyser
- Confirm no type hints reference Pydantic models
- Confirm TypedDict flows correctly: Reader → Handler
- Run integration tests to verify end-to-end type-safe flow

#### 3. Check for Other References

**Search analyser.py for:**
- Any other imports from waivern-source-code-analyser
- Any type hints using SourceCodeDataModel
- Any isinstance checks for SourceCodeDataModel
- Any model construction code

**Expected result:** No other references should exist

### Test Changes Required

**File:** `tests/test_analyser.py`

**Focus on:** `TestProcessingPurposeAnalyserSourceCodeProcessing` class (lines 553-759)

#### 1. Remove Imports (line 22)

**Remove:**
```python
from waivern_source_code_analyser.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeImportModel,
)
```

**Add (import TypedDict from handler):**
```python
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
)
```

#### 2. Convert Test Fixtures to TypedDict

**Example test to update:**
```python
def test_process_source_code_empty_data(
    analyser: ProcessingPurposeAnalyser,
) -> None:
    """Test processing empty source code data."""
    # BEFORE: Pydantic model
    message = Message(
        schema=Schema(name="source_code", version="1.0.0"),
        data=SourceCodeDataModel(
            data=[],
            analysis_metadata=SourceCodeAnalysisMetadataModel(...)
        ).model_dump()
    )

    # AFTER: TypedDict-annotated dict
    test_data: SourceCodeSchemaDict = {
        "data": [],
        "analysis_metadata": {
            "total_files_analysed": 0,
            "analysis_timestamp": "2024-01-01T00:00:00Z"
        }
    }

    message = Message(
        schema=Schema(name="source_code", version="1.0.0"),
        data=test_data
    )

    # Rest of test unchanged
    result = analyser.process_data(message)
    assert isinstance(result, Message)
    assert len(result.data["findings"]) == 0
```

**Benefits:**
- ✅ Type checker validates test_data structure
- ✅ IDE autocomplete when building fixtures
- ✅ Catches fixture errors at compile-time

#### 3. Update All Source Code Tests

**Tests in TestProcessingPurposeAnalyserSourceCodeProcessing:**
- `test_process_source_code_empty_data` - Convert fixture
- `test_process_source_code_with_patterns` - Convert fixture
- `test_process_source_code_multiple_files` - Convert fixtures
- `test_process_source_code_message_structure` - Convert fixture
- Any other tests using source code schema - Convert all fixtures

#### 4. Verify Integration Tests

**Key integration test (with TypedDict):**
```python
def test_source_code_processing_end_to_end():
    """Test complete source code processing flow with TypedDict-based data."""
    # Arrange - TypedDict-annotated fixture
    test_data: SourceCodeSchemaDict = {
        "data": [
            {
                "file_path": "/app/PaymentController.php",
                "raw_content": "<?php\nclass PaymentController {\n    public function processPayment() {\n        // Stripe integration\n    }\n}",
                "imports": [
                    {"module": "Stripe\\\\StripeClient", "line": 3, "type": "use"}
                ],
                "functions": [
                    {"name": "processPayment", "line_start": 5, "line_end": 10}
                ],
                "classes": [
                    {"name": "PaymentController", "line_start": 3, "line_end": 11}
                ],
                "file_metadata": {
                    "size_bytes": 150,
                    "last_modified": "2024-01-01T00:00:00Z"
                }
            }
        ],
        "analysis_metadata": {
            "total_files_analysed": 1,
            "analysis_timestamp": "2024-01-01T00:00:00Z"
        }
    }

    message = Message(
        schema=Schema(name="source_code", version="1.0.0"),
        data=test_data  # Type-checked by Message validation
    )
    analyser = ProcessingPurposeAnalyser(config=ProcessingPurposeAnalyserConfig())

    # Act
    result = analyser.process_data(message)

    # Assert
    assert isinstance(result, Message)
    assert result.schema.name == "processing_purpose_finding"
    findings = result.data["findings"]
    assert len(findings) > 0

    # Verify payment purpose detected
    payment_findings = [f for f in findings if "payment" in f["purpose_type"].lower()]
    assert len(payment_findings) > 0

    # Verify service integration detected
    assert any("stripe" in str(f).lower() for f in findings)
```

**Type safety verification:**
- ✅ test_data validated by type checker as SourceCodeSchemaDict
- ✅ Message validates test_data against JSON schema
- ✅ Reader returns SchemaData[SourceCodeSchemaDict]
- ✅ Handler receives SourceCodeSchemaDict
- ✅ Full pipeline type-safe from input to output

## Testing

### Testing Strategy

**TDD Approach (RED-GREEN-REFACTOR):**
1. Remove import (tests may fail if references exist - RED)
2. Convert test fixtures to dicts (tests should pass - GREEN)
3. Run refactor skill if needed (REFACTOR)

### Test Scenarios to Verify

#### 1. End-to-end source code processing with TypedDict

**Setup:**
- Create Message with source_code schema TypedDict data
- Call analyser.process_data(message)

**Expected behaviour:**
- Message flows through reader → handler with TypedDict
- Type checker validates TypedDict flow
- Dict processed correctly
- Findings returned in proper schema
- No Pydantic model references anywhere

#### 2. Message validation catches schema violations

**Setup:**
- Create Message with invalid source_code schema data (e.g., missing required field)

**Expected behaviour:**
- Message construction raises validation error
- Error caught before reaching analyser
- Clear error message about schema violation

#### 3. TypedDict structure preserved through pipeline

**Setup:**
- Create Message with source_code TypedDict data
- Trace data through: Message → Reader → Handler

**Expected behaviour:**
- Reader returns same dict from Message (TypedDict-annotated)
- Handler receives TypedDict from reader
- Type checker validates structure at each step
- No data transformation occurs
- Dict keys type-safe and accessible in handler

#### 4. Integration tests pass

**Setup:**
- Run full test suite for ProcessingPurposeAnalyser

**Expected behaviour:**
- All integration tests pass
- No typed model import errors
- End-to-end flow works with dicts
- Findings output identical to before

#### 5. Pattern matching still works

**Setup:**
- Process source code dict with various patterns (payment, support, service integrations)

**Expected behaviour:**
- All patterns detected correctly
- Evidence extracted properly
- Categorical data populated
- Findings structure correct

### Quality Checks

**Must pass before marking step complete:**
- [ ] Analyser tests pass (focus on TestProcessingPurposeAnalyserSourceCodeProcessing)
- [ ] Handler tests still pass (from Step 13)
- [ ] Reader tests still pass (from Step 14)
- [ ] Type checking passes (basedpyright strict mode)
- [ ] Linting passes (ruff)
- [ ] Formatting passes (ruff format)
- [ ] `./scripts/dev-checks.sh` passes for processing-purpose-analyser package
- [ ] Full package test suite passes (all 882+ tests)

## Success Criteria

**Functional:**
- [x] SourceCodeDataModel import removed from analyser.py
- [x] No other imports from waivern-source-code-analyser in analyser.py
- [x] `_process_source_code_data()` works with TypedDict from reader (Step 14)
- [x] End-to-end TypedDict flow verified (Message → Reader → Handler → Findings)
- [x] All pattern matching functionality preserved

**Type Safety:**
- [x] TypedDict flows through full pipeline (Reader → Handler)
- [x] Type checker validates full pipeline
- [x] No loss of type safety compared to Pydantic models
- [x] IDE autocomplete works throughout pipeline

**Testing:**
- [x] Integration tests converted to TypedDict fixtures
- [x] All source code processing tests pass
- [x] End-to-end integration tests pass
- [x] Type checker validates test fixtures
- [x] No test imports from waivern-source-code-analyser (except conftest if needed)

**Quality:**
- [x] Type checking passes
- [x] Linting passes
- [x] Formatting passes
- [x] `./scripts/dev-checks.sh` passes
- [x] Full test suite passes (882+ tests)

## Implementation Notes

### Design Considerations

**Verification checklist:**
1. Analyser doesn't need to know about TypedDict structure
2. Reader (Step 14) handles transformation from Message to TypedDict
3. Handler (Step 13) handles TypedDict processing
4. Analyser just orchestrates the flow
5. Type checker validates TypedDict flow at compile-time

**Key principle:**
- Analyser is the orchestrator, not the processor
- Reader abstracts data transformation (Message → TypedDict)
- Handler performs actual analysis (TypedDict → Findings)
- Each layer has single responsibility
- TypedDict provides type safety without coupling

### Validation Flow

**Current architecture (with TypedDict):**
```
Message (schema validation)
  ↓
Reader (wraps as SourceCodeSchemaDict) ← TypedDict type hint
  ↓
Handler (processes SourceCodeSchemaDict) ← TypedDict parameter
  ↓
Findings (output schema)
```

**Validation responsibilities:**
- **Message:** Validates input against source_code JSON schema (runtime)
- **Reader:** Wraps as TypedDict (compile-time type safety)
- **Handler:** Processes TypedDict (compile-time type checking)
- **Output:** Validates against processing_purpose_finding schema (runtime)

**Type safety layers:**
- **Compile-time:** TypedDict provides type checking
- **Runtime:** Message/Schema provide JSON schema validation
- **Best of both worlds:** Type safety + schema validation

### Integration Points

**Touch points to verify:**
1. **Message → Reader:** Message.data (dict) passed to reader
2. **Reader → Handler:** SchemaData.data (dict) passed to handler
3. **Handler → Analyser:** List[Finding] returned to analyser
4. **Analyser → Output:** Findings wrapped in output Message

### Refactoring Opportunities

**After GREEN state:**
1. Add docstring explaining dict-based schema handling
2. Document reliance on Message validation
3. Add type hints for dict structure (TypedDict in future)
4. Consider adding integration test specifically for dict flow

## Next Steps

After this step is complete:
- **Step 16:** Remove Package Dependency
- Remove `waivern-source-code-analyser` from pyproject.toml
- Update test conftest.py to remove schema registration import
- Verify all tests pass without the dependency
