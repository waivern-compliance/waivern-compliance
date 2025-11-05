# Step 4: Update Schema Instantiations in waivern-community

**Phase:** 1 - Schema Infrastructure
**Dependencies:** Step 3 complete
**Estimated Scope:** Large package with multiple schemas
**Status:** ✅ Completed

## Purpose

Update all schema instantiations in waivern-community to use the new `Schema(name, version)` pattern. Remove all schema subclass files.

## Schema Classes to Remove

waivern-community contains several schema classes that need to be removed:

1. **`SourceCodeSchema`** - in `connectors/source_code/schemas/source_code.py`
2. **`ProcessingPurposeFindingSchema`** - in `analysers/processing_purpose_analyser/schemas/processing_purpose_finding.py`
3. **`DataSubjectFindingSchema`** - in `analysers/data_subject_analyser/schemas/data_subject_finding.py`

## Schema Name Mappings

Ensure correct schema names match JSON files:
- `SourceCodeSchema()` → `Schema("source_code", "1.0.0")`
- `ProcessingPurposeFindingSchema()` → `Schema("processing_purpose_finding", "1.0.0")`
- `DataSubjectFindingSchema()` → `Schema("data_subject_finding", "1.0.0")`
- `StandardInputSchema()` → `Schema("standard_input", "1.0.0")`

## Files to Update

### Schema Definition Files (Remove Classes)

1. **`libs/waivern-community/src/waivern_community/connectors/source_code/schemas/source_code.py`**
   - Remove `SourceCodeSchema` class
   - Keep Pydantic models for type hints

2. **`libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/schemas/processing_purpose_finding.py`**
   - Remove `ProcessingPurposeFindingSchema` class
   - Keep Pydantic models

3. **`libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/schemas/data_subject_finding.py`**
   - Remove `DataSubjectFindingSchema` class
   - Keep Pydantic models

### Connector Source Files

4. **Filesystem Connector:**
   - `connectors/filesystem/connector.py`
   - `connectors/filesystem/factory.py`

5. **SQLite Connector:**
   - `connectors/sqlite/connector.py`
   - `connectors/sqlite/factory.py`

6. **Source Code Connector:**
   - `connectors/source_code/connector.py`
   - `connectors/source_code/factory.py`

7. **Database Base Connector:**
   - `connectors/database/base_connector.py`

### Analyser Source Files

8. **Processing Purpose Analyser:**
   - `analysers/processing_purpose_analyser/analyser.py`
   - `analysers/processing_purpose_analyser/factory.py`
   - `analysers/processing_purpose_analyser/source_code_schema_input_handler.py`

9. **Data Subject Analyser:**
   - `analysers/data_subject_analyser/analyser.py`
   - `analysers/data_subject_analyser/factory.py`

### Test Files

10. **All test files** - Find and update:
```bash
cd libs/waivern-community
grep -r "Schema()" tests/ --include="*.py" | grep -v "# "
```

## Search Strategy

```bash
cd libs/waivern-community

# Find all old schema class instantiations
grep -r "SourceCodeSchema()" . --include="*.py"
grep -r "ProcessingPurposeFindingSchema()" . --include="*.py"
grep -r "DataSubjectFindingSchema()" . --include="*.py"
grep -r "StandardInputSchema()" . --include="*.py"
grep -r "PersonalDataFindingSchema()" . --include="*.py"

# Find imports to update
grep -r "from.*schemas.*import.*Schema" . --include="*.py"
```

## Common Update Patterns

### Connector Pattern
```python
# Before
from waivern_community.connectors.source_code.schemas.source_code import SourceCodeSchema

class SourceCodeConnector(Connector):
    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [SourceCodeSchema()]

# After
from waivern_core.schemas.base import Schema

class SourceCodeConnector(Connector):
    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("source_code", "1.0.0")]
```

### Analyser Pattern
```python
# Before
from waivern_community.analysers.processing_purpose_analyser.schemas.processing_purpose_finding import ProcessingPurposeFindingSchema
from waivern_core.schemas.standard_input import StandardInputSchema

class ProcessingPurposeAnalyser(Analyser):
    @classmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [StandardInputSchema(), SourceCodeSchema()]

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [ProcessingPurposeFindingSchema()]

# After
from waivern_core.schemas.base import Schema

class ProcessingPurposeAnalyser(Analyser):
    @classmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        return [
            Schema("standard_input", "1.0.0"),
            Schema("source_code", "1.0.0"),
        ]

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("processing_purpose_finding", "1.0.0")]
```

### Test Pattern
```python
# Before
def test_analyser_output():
    expected_schema = ProcessingPurposeFindingSchema()
    assert result.schema == expected_schema

# After
def test_analyser_output():
    expected_schema = Schema("processing_purpose_finding", "1.0.0")
    assert result.schema == expected_schema
```

## Testing Strategy

This is a large package, so test incrementally:

1. **Update one component at a time** (e.g., all filesystem connector files)
2. **Run tests after each component:**
   ```bash
   cd libs/waivern-community
   uv run pytest tests/waivern_community/connectors/filesystem/ -v
   ```
3. **Run full package tests at end:**
   ```bash
   cd libs/waivern-community
   ./scripts/dev-checks.sh
   ```

## Expected Results

- ✅ All type checks pass
- ✅ All linting passes
- ✅ All tests pass (hundreds of tests)
- ✅ No schema subclass imports remain

## Key Decisions

- **Schema names from JSON:** Verify schema names match JSON file names
- **Keep Pydantic models:** Still useful for type validation
- **Incremental testing:** Test each component before moving to next

## Notes

- This is the largest update - take time to be careful
- Some tests may have schema equality assertions that need updating
- Watch for tests that check schema types (now tuple-based equality)
- Database utilities may have schema handling logic to update
