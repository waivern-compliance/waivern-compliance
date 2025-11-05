# Step 2: Update Schema Instantiations in waivern-core

**Phase:** 1 - Schema Infrastructure
**Dependencies:** Step 1 complete
**Estimated Scope:** Package-level changes
**Status:** ✅ Completed

## Purpose

Update all schema instantiations in waivern-core to use the new `Schema(name, version)` pattern. Remove schema subclass files.

## Current Pattern

```python
# Old way
from waivern_core.schemas.standard_input import StandardInputSchema
schema = StandardInputSchema()

# Used in components
_SUPPORTED_SCHEMAS = [StandardInputSchema()]
```

## Target Pattern

```python
# New way
from waivern_core.schemas.base import Schema
schema = Schema("standard_input", "1.0.0")

# Used in components
_SUPPORTED_SCHEMAS = [Schema("standard_input", "1.0.0")]
```

## Files to Update

### Source Files

1. **`libs/waivern-core/src/waivern_core/schemas/standard_input.py`**
   - Remove the `StandardInputSchema` class entirely
   - Keep Pydantic models (BaseMetadata, StandardInputDataModel, etc.) - these are still useful for type hints
   - Update any example code or docstrings

2. **`libs/waivern-core/src/waivern_core/base_connector.py`**
   - Update any example schemas in docstrings

3. **`libs/waivern-core/src/waivern_core/base_analyser.py`**
   - Update any example schemas in docstrings

### Test Files

4. **`libs/waivern-core/tests/waivern_core/test_schema_base.py`**
   - Update tests to use `Schema("test_schema", "1.0.0")` pattern
   - Update equality tests (now tuple-based, not type-based)
   - Update hashing tests

5. **`libs/waivern-core/tests/waivern_core/test_message.py`**
   - Update schema instantiations in test fixtures
   - May need to update schema equality assertions

## Implementation Notes

### Handling Pydantic Models

The Pydantic models in `standard_input.py` are still useful for type hints and data validation:
```python
# Keep these:
class BaseMetadata(BaseModel): ...
class StandardInputDataItemModel[MetadataT: BaseMetadata](BaseModel): ...
class StandardInputDataModel[MetadataT: BaseMetadata](BaseModel): ...

# Remove this:
class StandardInputSchema(Schema): ...  # DELETE
```

### Finding All Instantiations

Use grep to find all schema instantiations:
```bash
cd libs/waivern-core
grep -r "StandardInputSchema()" . --include="*.py"
grep -r "Schema()" . --include="*.py"
```

### Version to Use

All current schemas are version `1.0.0`. Use this version for all instantiations:
- `StandardInputSchema()` → `Schema("standard_input", "1.0.0")`

## Testing

After changes, run waivern-core tests:
```bash
cd libs/waivern-core
./scripts/dev-checks.sh
```

Expected results:
- ✅ All type checks pass
- ✅ All linting passes
- ✅ All waivern-core tests pass
- ⚠️  Other packages may still fail (will be fixed in subsequent steps)

## Key Decisions

- **Keep Pydantic models:** They're useful for type hints even without schema classes
- **Consistent versioning:** All schemas currently at 1.0.0
- **Test update strategy:** Update test assertions to match new equality semantics

## Files Modified

- `libs/waivern-core/src/waivern_core/schemas/standard_input.py` (remove class, keep models)
- `libs/waivern-core/src/waivern_core/base_connector.py` (docstrings only)
- `libs/waivern-core/src/waivern_core/base_analyser.py` (docstrings only)
- `libs/waivern-core/tests/waivern_core/test_schema_base.py`
- `libs/waivern-core/tests/waivern_core/test_message.py`

## Notes

- This step should make waivern-core internally consistent
- Other packages will still fail until their schemas are updated
- This is an atomic unit - waivern-core should pass all its own tests after this step
