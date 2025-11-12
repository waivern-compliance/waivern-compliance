# Task: Update SourceCodeSchemaInputHandler to Use Dict

- **Phase:** 4 - Fix ProcessingPurposeAnalyser Schema Coupling
- **Status:** TODO
- **Prerequisites:** Phase 3 complete (SourceCodeAnalyser refactoring done)
- **Step:** 13 of 17

## Context

This is part of removing hardcoded dependencies on SourceCodeAnalyser's typed Pydantic models from ProcessingPurposeAnalyser. This step focuses on transforming the input handler to work with dict-based data instead of typed models.

**See:** the parent implementation plan (`docs/development/active/phase_04_fix_processing_purpose_analyser_schema_coupling.md`) for full context.

## Purpose

Update `SourceCodeSchemaInputHandler` to accept and process dictionary-based data with TypedDict type hints instead of importing `SourceCodeDataModel` from SourceCodeAnalyser. This eliminates the package dependency while maintaining compile-time type safety and all functionality.

## Problem

Current implementation has tight coupling to SourceCodeAnalyser's typed models:

**Location:** `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/source_code_schema_input_handler.py`

**Current approach:**
```python
from waivern_source_code_analyser.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

def analyse_source_code_data(self, data: SourceCodeDataModel) -> list[Finding]:
    for file_data in data.data:  # Typed model access
        file_path = file_data.file_path
        raw_content = file_data.raw_content
        imports = file_data.imports
        functions = file_data.functions
        classes = file_data.classes
```

**Issues:**
1. Direct import from waivern-source-code-analyser package
2. Method signature requires typed model
3. Field access assumes model attributes
4. Tests require constructing typed models

## Solution

Transform handler to use TypedDict-based schema definitions:

**New approach (with TypedDict for type safety):**
```python
# No imports from waivern-source-code-analyser
from typing import Any, NotRequired, TypedDict

# Define local TypedDict mirroring source_code schema structure
class SourceCodeImportDict(TypedDict):
    module: str
    alias: NotRequired[str | None]
    line: int
    type: str

class SourceCodeFunctionDict(TypedDict):
    name: str
    line_start: int
    line_end: int

class SourceCodeClassDict(TypedDict):
    name: str
    line_start: int
    line_end: int

class SourceCodeFileMetadataDict(TypedDict):
    size_bytes: int
    last_modified: str

class SourceCodeFileDict(TypedDict):
    file_path: str
    raw_content: str
    imports: NotRequired[list[SourceCodeImportDict]]
    functions: NotRequired[list[SourceCodeFunctionDict]]
    classes: NotRequired[list[SourceCodeClassDict]]
    file_metadata: SourceCodeFileMetadataDict

class SourceCodeAnalysisMetadataDict(TypedDict):
    total_files_analysed: int
    analysis_timestamp: str

class SourceCodeSchemaDict(TypedDict):
    data: list[SourceCodeFileDict]
    analysis_metadata: SourceCodeAnalysisMetadataDict

def analyse_source_code_data(self, data: SourceCodeSchemaDict) -> list[Finding]:
    for file_data in data["data"]:  # ✅ Type-checked dict access
        file_path = file_data["file_path"]  # ✅ IDE autocomplete
        raw_content = file_data["raw_content"]
        imports = file_data.get("imports", [])  # ✅ Type-safe optional
        functions = file_data.get("functions", [])
        classes = file_data.get("classes", [])
```

**Key changes:**
1. Remove import of SourceCodeDataModel and SourceCodeFileDataModel
2. Add TypedDict definitions mirroring source_code schema structure (local to package)
3. Change method signature to accept `SourceCodeSchemaDict` (TypedDict, not Pydantic)
4. Replace attribute access with dict key access
5. Use `.get()` for optional fields (imports, functions, classes)
6. Get compile-time type safety + IDE support without package dependency

**Benefits of TypedDict approach:**
- ✅ No dependency on waivern-source-code-analyser package
- ✅ Compile-time type checking (basedpyright validates dict structure)
- ✅ IDE autocomplete and IntelliSense
- ✅ No runtime overhead (TypedDict is pure type hints)
- ✅ Architectural independence maintained
- ✅ Type-safe refactoring support

## Implementation

### Files to Modify

**1. Handler source code:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/source_code_schema_input_handler.py`

**2. Handler tests:**
`libs/waivern-processing-purpose-analyser/tests/test_source_code_schema_input_handler.py`

### Code Changes Required

#### 1. Update Imports (lines 9-12)

**Remove:**
```python
from waivern_source_code_analyser.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)
```

**Add:**
```python
from typing import Any, NotRequired, TypedDict
```

#### 2. Add TypedDict Definitions (new section after imports)

**Add after imports, before class definition:**
```python
# TypedDict definitions for source_code schema v1.0.0
# These mirror the JSON schema structure without importing from SourceCodeAnalyser

class SourceCodeImportDict(TypedDict):
    """Import statement in source code."""
    module: str
    alias: NotRequired[str | None]
    line: int
    type: str  # "require", "require_once", "include", "include_once", "use", "import"


class SourceCodeFunctionDict(TypedDict):
    """Function definition in source code."""
    name: str
    line_start: int
    line_end: int
    # Additional fields omitted for brevity (parameters, return_type, etc.)


class SourceCodeClassDict(TypedDict):
    """Class definition in source code."""
    name: str
    line_start: int
    line_end: int
    # Additional fields omitted for brevity (extends, implements, properties, methods)


class SourceCodeFileMetadataDict(TypedDict):
    """Metadata for a source code file."""
    size_bytes: int
    last_modified: str


class SourceCodeFileDict(TypedDict):
    """Individual source code file data."""
    file_path: str
    raw_content: str
    imports: NotRequired[list[SourceCodeImportDict]]
    functions: NotRequired[list[SourceCodeFunctionDict]]
    classes: NotRequired[list[SourceCodeClassDict]]
    file_metadata: SourceCodeFileMetadataDict


class SourceCodeAnalysisMetadataDict(TypedDict):
    """Metadata for source code analysis."""
    total_files_analysed: int
    analysis_timestamp: str


class SourceCodeSchemaDict(TypedDict):
    """Top-level source_code schema structure (v1.0.0)."""
    data: list[SourceCodeFileDict]
    analysis_metadata: SourceCodeAnalysisMetadataDict
```

**Rationale:**
- TypedDict provides compile-time type safety without runtime overhead
- Definitions are local to ProcessingPurposeAnalyser (no imports from SourceCodeAnalyser)
- Mirrors source_code JSON schema structure
- `NotRequired` marks optional fields (Python 3.11+)
- Type checker validates dict key access
- IDE provides autocomplete for dict keys

#### 3. Update Method Signature (line 50)

**Before:**
```python
def analyse_source_code_data(self, data: SourceCodeDataModel) -> list[Finding]:
```

**After:**
```python
def analyse_source_code_data(self, data: SourceCodeSchemaDict) -> list[Finding]:
    """Analyse source code data for processing purposes.

    Args:
        data: Dict conforming to source_code schema v1.0.0.
              Type-checked via TypedDict for compile-time safety.
              Data has already been validated by Message against JSON schema.

    Returns:
        List of Finding objects representing detected processing purposes
    """
```

#### 4. Update Data Iteration (line 52)

**Before:**
```python
for file_data in data.data:
```

**After:**
```python
for file_data in data["data"]:  # TypedDict ensures "data" key exists
```

#### 5. Update Field Access

**Required fields (TypedDict marks these as required, type checker validates):**
```python
file_path = file_data["file_path"]  # ✅ Type-checked
raw_content = file_data["raw_content"]  # ✅ Type-checked
```

**Optional fields (use .get() with defaults, TypedDict marks as NotRequired):**
```python
imports = file_data.get("imports", [])  # ✅ Type-safe: list[SourceCodeImportDict]
functions = file_data.get("functions", [])  # ✅ Type-safe: list[SourceCodeFunctionDict]
classes = file_data.get("classes", [])  # ✅ Type-safe: list[SourceCodeClassDict]
```

**Nested field access in loops:**
```python
# Import modules (line 155) - TypedDict knows structure
for import_item in imports:
    module = import_item["module"]  # ✅ Type-checked

# Function names (line 175) - TypedDict knows structure
for function in functions:
    name = function["name"]  # ✅ Type-checked

# Class names (line 195) - TypedDict knows structure
for class_item in classes:
    name = class_item["name"]  # ✅ Type-checked
```

#### 6. Update Metadata Access

**Analysis metadata (TypedDict ensures structure):**
```python
# Access with TypedDict type safety
metadata = data["analysis_metadata"]  # ✅ Type: SourceCodeAnalysisMetadataDict
total_files = metadata["total_files_analysed"]  # ✅ Type-checked
timestamp = metadata["analysis_timestamp"]  # ✅ Type-checked
```

### Test Changes Required

**File:** `tests/test_source_code_schema_input_handler.py`

#### 1. Remove Imports (line 11)

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

**Add (import TypedDict types from handler module):**
```python
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
    SourceCodeFileDict,
    SourceCodeImportDict,
    SourceCodeFunctionDict,
    SourceCodeClassDict,
)
```

**Note:** Tests can import TypedDict definitions from handler module for type-safe test fixtures.

#### 2. Convert Test Fixtures to Dicts (with TypedDict hints)

**Pattern to follow:**

**Before (typed model):**
```python
data = SourceCodeDataModel(
    data=[
        SourceCodeFileDataModel(
            file_path="/path/to/file.php",
            raw_content="<?php ...",
            imports=[
                SourceCodeImportModel(module="Stripe\\StripeClient")
            ],
            functions=[
                SourceCodeFunctionModel(name="processPayment")
            ],
            classes=[],
            file_metadata=SourceCodeFileMetadataModel(...)
        )
    ],
    analysis_metadata=SourceCodeAnalysisMetadataModel(...)
)
```

**After (TypedDict-annotated dict):**
```python
# Type-safe dict construction (type checker validates structure)
data: SourceCodeSchemaDict = {
    "data": [
        {
            "file_path": "/path/to/file.php",
            "raw_content": "<?php ...",
            "imports": [
                {"module": "Stripe\\StripeClient", "line": 5, "type": "use"}
            ],
            "functions": [
                {"name": "processPayment", "line_start": 10, "line_end": 20}
            ],
            "classes": [],
            "file_metadata": {
                "size_bytes": 1024,
                "last_modified": "2024-01-01T00:00:00Z"
            }
        }
    ],
    "analysis_metadata": {
        "total_files_analysed": 1,
        "analysis_timestamp": "2024-01-01T00:00:00Z"
    }
}
```

**Benefits in tests:**
- ✅ Type checker validates test fixture structure
- ✅ IDE autocomplete when building fixtures
- ✅ Catches typos in dict keys at compile-time
- ✅ Ensures test data matches actual schema structure

#### 3. Update All Test Methods

**Tests to convert (633 lines total):**
- `test_init` - No changes needed
- `test_analyse_empty_source_code_data` - Convert fixture to dict
- `test_analyse_source_code_with_payment_patterns` - Convert fixture to dict
- `test_analyse_source_code_with_support_patterns` - Convert fixture to dict
- `test_analyse_source_code_with_service_integrations` - Convert fixture to dict
- `test_analyse_source_code_multiple_files` - Convert fixtures to dicts
- `test_analyse_source_code_creates_correct_metadata` - Convert fixture to dict
- `test_analyse_source_code_service_integration_categorical_data` - Convert fixtures to dicts
- `test_analyse_source_code_data_collection_categorical_data` - Convert fixtures to dicts
- All other test methods - Convert all typed model fixtures to dicts

## Testing

### Testing Strategy

**TDD Approach (RED-GREEN-REFACTOR):**
1. Convert test fixtures to dicts (tests will fail - RED)
2. Update handler code to use dict access (tests pass - GREEN)
3. Run refactor skill to improve code quality (REFACTOR)

### Test Scenarios to Verify

#### 1. Handler processes dict data correctly

**Setup:**
- Create dict fixture with all fields (file_path, raw_content, imports, functions, classes)
- Call `analyse_source_code_data(data)`

**Expected behaviour:**
- Returns list of Finding objects
- Pattern matching works on raw_content
- Service integration detection works on imports
- Function/class name analysis works

#### 2. Handler handles missing optional fields

**Setup:**
- Create dict fixture with only required fields (file_path, raw_content)
- Omit imports, functions, classes

**Expected behaviour:**
- No KeyError raised
- Analysis completes successfully
- Findings created from raw_content only

#### 3. Handler handles empty data

**Setup:**
- Create dict with empty data list: `{"data": []}`

**Expected behaviour:**
- Returns empty findings list
- No errors raised

#### 4. Handler creates correct metadata

**Setup:**
- Create dict fixture with file_metadata and analysis_metadata

**Expected behaviour:**
- Finding metadata populated with timestamps
- File paths tracked correctly
- Metadata structure identical to before

#### 5. Multiple file processing

**Setup:**
- Create dict with multiple files in data list

**Expected behaviour:**
- All files processed
- Findings from all files returned
- No data mixing between files

#### 6. Categorical data fields populated

**Setup:**
- Create dict with service integration patterns

**Expected behaviour:**
- `service_category` field populated in findings
- `collection_type` field populated
- `data_source` field populated

#### 7. Evidence structure preserved

**Setup:**
- Create dict with pattern matches

**Expected behaviour:**
- Evidence list contains correct snippets
- Line numbers accurate
- Context preserved in evidence

### Quality Checks

**Must pass before marking step complete:**
- [ ] All 633 lines of handler tests pass
- [ ] Type checking passes (basedpyright strict mode)
- [ ] Linting passes (ruff)
- [ ] Formatting passes (ruff format)
- [ ] No functional regressions
- [ ] `./scripts/dev-checks.sh` passes for processing-purpose-analyser package

## Success Criteria

**Functional:**
- [x] TypedDict definitions added for source_code schema structure
- [x] Handler accepts `SourceCodeSchemaDict` (TypedDict) instead of Pydantic model
- [x] All field access converted to dict key access (type-checked)
- [x] Optional fields use `.get()` with defaults (TypedDict marks as NotRequired)
- [x] All pattern matching functionality preserved
- [x] Evidence extraction unchanged
- [x] Metadata creation identical
- [x] No imports from waivern-source-code-analyser

**Type Safety:**
- [x] Compile-time type checking works (basedpyright validates TypedDict)
- [x] IDE autocomplete works for dict keys
- [x] Type checker catches incorrect key access
- [x] Type checker validates nested structure
- [x] No loss of type safety compared to Pydantic models

**Testing:**
- [x] All handler tests converted to TypedDict-annotated dict fixtures
- [x] All handler tests pass
- [x] Test coverage maintained (100% of handler)
- [x] Edge cases tested (empty data, missing fields)
- [x] Type checker validates test fixtures

**Quality:**
- [x] Type checking passes (strict mode with TypedDict)
- [x] Linting passes
- [x] Formatting passes
- [x] `./scripts/dev-checks.sh` passes

## Implementation Notes

### Design Considerations

**Why TypedDict instead of plain dict[str, Any]:**
- ✅ Provides compile-time type safety without package imports
- ✅ IDE autocomplete and IntelliSense support
- ✅ Type checker validates dict key access
- ✅ No runtime overhead (pure type hints)
- ✅ Catches typos and structural errors at compile-time
- ✅ Better developer experience than plain dicts
- ✅ Aligns with modern Python best practices (FastAPI, SQLAlchemy 2.0)

**Why TypedDict instead of importing Pydantic models:**
- ✅ No package dependency on waivern-source-code-analyser
- ✅ Definitions local to ProcessingPurposeAnalyser
- ✅ Architectural independence maintained
- ✅ Type safety at compile-time, validation at runtime (Message)

**Why .get() for optional fields:**
- Source code schema marks imports/functions/classes as optional
- Files without these structures won't have the keys
- .get() prevents KeyError for legitimate empty cases
- Matches schema contract (optional fields)

**Error handling:**
- Required fields (file_path, raw_content) will raise KeyError if missing
- This is acceptable because Message validation should catch schema violations
- Tests verify handler behavior with valid schema-compliant data

### Refactoring Opportunities

**After GREEN state:**
1. Consider extracting TypedDict definitions to separate module if reused
2. Add helper methods for common dict access patterns if needed
3. Document TypedDict definitions reference the JSON schema version
4. Add validation that TypedDict matches JSON schema structure (future tooling)

**TypedDict maintenance:**
- Keep TypedDict definitions in sync with source_code JSON schema
- Document which schema version TypedDict represents (v1.0.0)
- When schema evolves, update TypedDict or create new version-specific TypedDict
- Consider code generation from JSON Schema to TypedDict (future enhancement)

## Next Steps

After this step is complete:
- **Step 14:** Update Schema Reader to Return Dict
- Remove SourceCodeDataModel import from reader
- Return dict instead of typed model from `read()` method
