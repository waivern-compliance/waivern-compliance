# Task: Update Schema Reader to Return Dict

- **Phase:** 4 - Fix ProcessingPurposeAnalyser Schema Coupling
- **Status:** TODO
- **Prerequisites:** Step 13 complete (Handler uses dict)
- **Step:** 14 of 17

## Context

This is part of removing hardcoded dependencies on SourceCodeAnalyser's typed Pydantic models. Step 13 updated the handler to accept dicts. Now we need to update the schema reader to return dicts instead of typed models.

**See:** the parent implementation plan (`docs/development/active/phase_04_fix_processing_purpose_analyser_schema_coupling.md`) for full context.

## Purpose

Update `SourceCode_1_0_0_Reader` to return TypedDict-based data instead of `SourceCodeDataModel` Pydantic model. This completes the transformation from Pydantic models to TypedDict-based schema handling in the reader layer, maintaining type safety without package dependencies.

## Problem

Current reader transforms Message data to typed model:

**Location:** `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schema_readers/source_code_1_0_0.py`

**Current approach:**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel
from waivern_core import Message, Schema
from waivern_core.schema_reader import SchemaData, SchemaReader

class SourceCode_1_0_0_Reader(SchemaReader[SourceCodeDataModel]):
    def read(self, message: Message) -> SchemaData[SourceCodeDataModel]:
        data = SourceCodeDataModel(**message.data)
        return SchemaData(schema=message.schema, data=data)
```

**Issues:**
1. Imports SourceCodeDataModel from waivern-source-code-analyser
2. Generic type parameter uses typed model
3. Constructs Pydantic model from message data
4. Adds redundant validation (Message already validates)

## Solution

Transform reader to return TypedDict-annotated data:

**New approach (with TypedDict from Step 13):**
```python
# No imports from waivern-source-code-analyser
from waivern_core import Message, Schema
from waivern_core.schema_reader import SchemaData, SchemaReader

# Import TypedDict from handler (defined in Step 13)
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
)

class SourceCode_1_0_0_Reader(SchemaReader[SourceCodeSchemaDict]):
    def read(self, message: Message) -> SchemaData[SourceCodeSchemaDict]:
        # Message already validated against schema
        # Return with TypedDict type hint for compile-time safety
        return SchemaData(schema=message.schema, data=message.data)
```

**Key changes:**
1. Remove import of SourceCodeDataModel from waivern-source-code-analyser
2. Import SourceCodeSchemaDict TypedDict from handler module (Step 13)
3. Change generic type from `SourceCodeDataModel` to `SourceCodeSchemaDict`
4. Return message data directly (already validated)
5. Remove Pydantic model construction
6. Maintain type safety via TypedDict

**Why this works:**
- Message object already validates data against source_code schema v1.0.0
- Reader's job is to wrap validated data, not re-validate
- Schema contract enforced at Message level
- TypedDict provides compile-time type safety without package dependency
- Handler (Step 13) expects SourceCodeSchemaDict type

## Implementation

### Files to Modify

**1. Reader source code:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schema_readers/source_code_1_0_0.py`

**2. Reader tests:**
`libs/waivern-processing-purpose-analyser/tests/schema_readers/test_source_code_1_0_0.py`

### Code Changes Required

#### 1. Update Imports (line 6)

**Remove:**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel
```

**Add:**
```python
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
)
```

**Rationale:**
- Import TypedDict from handler module (defined in Step 13)
- No dependency on waivern-source-code-analyser
- Maintains type safety with local TypedDict definitions
- Reader and handler use same type definitions

#### 2. Update Class Declaration (line 9)

**Before:**
```python
class SourceCode_1_0_0_Reader(SchemaReader[SourceCodeDataModel]):
    """Schema reader for source_code schema version 1.0.0."""
```

**After:**
```python
class SourceCode_1_0_0_Reader(SchemaReader[SourceCodeSchemaDict]):
    """Schema reader for source_code schema version 1.0.0.

    Returns TypedDict-annotated data that has been validated by Message
    against the source_code JSON schema contract. Uses SourceCodeSchemaDict
    from handler module for compile-time type safety.
    """
```

#### 3. Update read() Method (lines 11-20)

**Before:**
```python
def read(self, message: Message) -> SchemaData[SourceCodeDataModel]:
    """Read source code data from message.

    Args:
        message: Message containing source code data

    Returns:
        SchemaData containing validated SourceCodeDataModel
    """
    data = SourceCodeDataModel(**message.data)
    return SchemaData(schema=message.schema, data=data)
```

**After:**
```python
def read(self, message: Message) -> SchemaData[SourceCodeSchemaDict]:
    """Read source code data from message.

    Args:
        message: Message containing source code data

    Returns:
        SchemaData containing TypedDict that has been validated by Message
        against the source_code schema contract. Type-safe via SourceCodeSchemaDict.

    Notes:
        The Message object has already validated the data against the
        source_code v1.0.0 JSON schema. We return the dict with TypedDict
        type hint for compile-time type safety without additional validation.
    """
    return SchemaData(schema=message.schema, data=message.data)
```

### Test Changes Required

**File:** `tests/schema_readers/test_source_code_1_0_0.py`

#### 1. Update Imports (line 3)

**Remove:**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel
```

**Add:**
```python
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
)
```

#### 2. Update Test Fixtures

**Current test structure:**
```python
def test_source_code_1_0_0_reader_validates_and_returns_typed_model():
    """Test reader validates and returns SourceCodeDataModel."""
    # Arrange
    message = Message(
        schema=Schema(name="source_code", version="1.0.0"),
        data={
            "data": [...],
            "analysis_metadata": {...}
        }
    )
    reader = SourceCode_1_0_0_Reader()

    # Act
    result = reader.read(message)

    # Assert
    assert isinstance(result.data, SourceCodeDataModel)
    assert result.schema.name == "source_code"
```

**Updated test structure (with TypedDict):**
```python
def test_source_code_1_0_0_reader_returns_typed_dict():
    """Test reader returns TypedDict with validated schema data."""
    # Arrange
    test_data: SourceCodeSchemaDict = {
        "data": [
            {
                "file_path": "/test/file.php",
                "raw_content": "<?php echo 'test';",
                "imports": [],
                "functions": [],
                "classes": [],
                "file_metadata": {
                    "size_bytes": 100,
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
        data=test_data
    )
    reader = SourceCode_1_0_0_Reader()

    # Act
    result = reader.read(message)

    # Assert
    assert isinstance(result.data, dict)  # Runtime: it's a dict
    # Type checker knows: result.data is SourceCodeSchemaDict
    assert result.schema.name == "source_code"
    assert result.schema.version == "1.0.0"
    assert result.data == message.data  # Returns same dict from Message
    assert "data" in result.data  # ✅ Type-safe key access
    assert "analysis_metadata" in result.data  # ✅ Type-safe key access
```

#### 3. Add Test for TypedDict Structure

**New test to add:**
```python
def test_source_code_1_0_0_reader_preserves_typed_dict_structure():
    """Test reader preserves TypedDict structure from Message."""
    # Arrange - TypedDict-annotated fixture
    message_data: SourceCodeSchemaDict = {
        "data": [
            {
                "file_path": "/app/Controller.php",
                "raw_content": "<?php class Controller {}",
                "file_metadata": {
                    "size_bytes": 50,
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
        data=message_data
    )
    reader = SourceCode_1_0_0_Reader()

    # Act
    result = reader.read(message)

    # Assert
    assert result.data is message.data  # Same object reference
    # ✅ Type-safe key access (validated by type checker)
    assert result.data["data"][0]["file_path"] == "/app/Controller.php"
    assert result.data["analysis_metadata"]["total_files_analysed"] == 1
```

## Testing

### Testing Strategy

**TDD Approach (RED-GREEN-REFACTOR):**
1. Update test to expect dict instead of typed model (test will fail - RED)
2. Update reader code to return dict (test passes - GREEN)
3. Run refactor skill if needed (REFACTOR)

### Test Scenarios to Verify

#### 1. Reader returns TypedDict-annotated dict instead of Pydantic model

**Setup:**
- Create Message with valid source_code schema data
- Call reader.read(message)

**Expected behaviour:**
- Returns SchemaData with TypedDict-annotated dict data
- Dict contains all fields from message.data
- Schema preserved in SchemaData
- Type checker validates return type as SourceCodeSchemaDict

#### 2. Reader preserves dict structure

**Setup:**
- Create Message with source_code data
- Call reader.read(message)

**Expected behaviour:**
- Returned dict is same object as message.data
- No data transformation occurs
- All nested structures preserved

#### 3. Reader does not re-validate

**Setup:**
- Create Message (which validates against schema)
- Call reader.read(message)

**Expected behaviour:**
- No Pydantic validation occurs in reader
- Reader trusts Message validation
- No validation errors raised in reader

#### 4. Reader works with handler (integration)

**Setup:**
- Create Message with source_code data
- Pass through reader then handler

**Expected behaviour:**
- Reader returns dict
- Handler processes dict successfully
- End-to-end flow works

### Quality Checks

**Must pass before marking step complete:**
- [ ] Reader tests pass (54 lines updated)
- [ ] Handler tests still pass (rely on reader)
- [ ] Type checking passes (basedpyright strict mode)
- [ ] Linting passes (ruff)
- [ ] Formatting passes (ruff format)
- [ ] `./scripts/dev-checks.sh` passes for processing-purpose-analyser package

## Success Criteria

**Functional:**
- [x] Reader returns `SchemaData[SourceCodeSchemaDict]` (TypedDict) instead of Pydantic model
- [x] Reader does not import from waivern-source-code-analyser
- [x] Reader imports TypedDict from handler module (Step 13)
- [x] Reader returns message.data directly (no transformation)
- [x] Reader relies on Message validation (no Pydantic)
- [x] Dict structure preserved from Message

**Type Safety:**
- [x] TypedDict provides compile-time type checking
- [x] Type checker validates return type
- [x] IDE autocomplete works with returned data
- [x] No loss of type safety compared to Pydantic model

**Testing:**
- [x] Reader tests updated to expect dict
- [x] Reader tests verify dict structure
- [x] Integration with handler verified
- [x] All tests pass

**Quality:**
- [x] Type checking passes
- [x] Linting passes
- [x] Formatting passes
- [x] `./scripts/dev-checks.sh` passes

## Implementation Notes

### Design Considerations

**Why return message.data directly:**
- Message already validated data against JSON schema
- No need for additional Pydantic validation
- Reduces computational overhead
- Simplifies reader implementation
- Trusts schema contract enforced by Message

**Why SourceCodeSchemaDict (TypedDict) instead of dict[str, Any]:**
- ✅ Provides compile-time type safety
- ✅ IDE autocomplete for dict keys
- ✅ Type checker validates structure
- ✅ No runtime overhead (pure type hints)
- ✅ Reuses TypedDict definitions from handler module (Step 13)
- ✅ Single source of truth for type definitions

**Why TypedDict instead of Pydantic model:**
- ✅ No package dependency on waivern-source-code-analyser
- ✅ Definitions local to ProcessingPurposeAnalyser
- ✅ Type safety without redundant validation
- ✅ Architectural independence maintained

**Validation responsibility:**
- **Message object:** Validates against JSON schema (wire format)
- **Reader:** Wraps validated data (no additional validation)
- **Handler:** Processes dict data (trusts schema validation)

### Performance Benefits

**Before (with Pydantic validation):**
1. Message validates against JSON schema
2. Reader constructs Pydantic model (re-validates)
3. Handler accesses model attributes

**After (dict-based):**
1. Message validates against JSON schema
2. Reader returns dict directly
3. Handler accesses dict keys

**Improvement:**
- Eliminates redundant Pydantic validation
- Reduces object construction overhead
- Faster data flow through pipeline

### Refactoring Opportunities

**After GREEN state:**
1. Document reader's reliance on Message validation
2. Add docstring explaining schema contract approach
3. Consider adding type hints for dict structure (future TypedDict)

## Next Steps

After this step is complete:
- **Step 15:** Update Main Analyser to Handle Dict
- Update `_process_source_code_data()` to work with dict from reader
- Remove SourceCodeDataModel import from analyser.py
- Verify end-to-end integration tests pass
