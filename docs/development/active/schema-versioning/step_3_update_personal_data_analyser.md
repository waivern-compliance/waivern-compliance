# Step 3: Update Schema Instantiations in waivern-personal-data-analyser

**Phase:** 1 - Schema Infrastructure
**Dependencies:** Step 2 complete
**Estimated Scope:** Package-level changes
**Status:** ✅ Completed

## Purpose

Update all schema instantiations in waivern-personal-data-analyser to use the new `Schema(name, version)` pattern. Remove the PersonalDataFindingSchema class.

## Files to Update

### Source Files

1. **`libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schemas/personal_data_finding.py`**
   - Remove the `PersonalDataFindingSchema` class
   - Keep any Pydantic models if they exist
   - Update module docstring if needed

2. **`libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/analyser.py`**
   - Update schema imports: remove `PersonalDataFindingSchema`
   - Add import: `from waivern_core.schemas.base import Schema`
   - Update schema instantiations in class attributes or methods
   - Look for patterns like:
     - `_SUPPORTED_OUTPUT_SCHEMAS = [PersonalDataFindingSchema()]`
     - Change to: `[Schema("personal_data_finding", "1.0.0")]`

3. **`libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/factory.py`**
   - Update any schema references in factory code

### Test Files

4. **All test files in `libs/waivern-personal-data-analyser/tests/`**
   - Find all schema instantiations: `grep -r "PersonalDataFindingSchema\|StandardInputSchema" tests/`
   - Update to new pattern:
     - `PersonalDataFindingSchema()` → `Schema("personal_data_finding", "1.0.0")`
     - `StandardInputSchema()` → `Schema("standard_input", "1.0.0")`

## Search Strategy

```bash
cd libs/waivern-personal-data-analyser

# Find all old schema instantiations
grep -r "PersonalDataFindingSchema" . --include="*.py"
grep -r "StandardInputSchema" . --include="*.py"
grep -r "from waivern_core.schemas.standard_input" . --include="*.py"

# After changes, verify no old patterns remain
grep -r "Schema()" . --include="*.py"  # Check all use name+version
```

## Common Patterns to Update

### Pattern 1: Class attributes
```python
# Before
_SUPPORTED_INPUT_SCHEMAS = [StandardInputSchema()]
_SUPPORTED_OUTPUT_SCHEMAS = [PersonalDataFindingSchema()]

# After
_SUPPORTED_INPUT_SCHEMAS = [Schema("standard_input", "1.0.0")]
_SUPPORTED_OUTPUT_SCHEMAS = [Schema("personal_data_finding", "1.0.0")]
```

### Pattern 2: Method returns
```python
# Before
def get_supported_output_schemas(cls) -> list[Schema]:
    return [PersonalDataFindingSchema()]

# After
def get_supported_output_schemas(cls) -> list[Schema]:
    return [Schema("personal_data_finding", "1.0.0")]
```

### Pattern 3: Message creation
```python
# Before
return Message(
    schema=PersonalDataFindingSchema(),
    content=findings
)

# After
return Message(
    schema=Schema("personal_data_finding", "1.0.0"),
    content=findings
)
```

### Pattern 4: Test fixtures
```python
# Before
@pytest.fixture
def output_schema():
    return PersonalDataFindingSchema()

# After
@pytest.fixture
def output_schema():
    return Schema("personal_data_finding", "1.0.0")
```

## Testing

Run package tests:
```bash
cd libs/waivern-personal-data-analyser
./scripts/dev-checks.sh
```

Expected results:
- ✅ All type checks pass
- ✅ All linting passes
- ✅ All tests pass

## Key Decisions

- **Schema names:** Use exact schema names from JSON files
- **Version:** All schemas currently at 1.0.0
- **Import cleanup:** Remove unused schema class imports

## Files Modified

- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schemas/personal_data_finding.py`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/analyser.py`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/factory.py`
- All test files with schema instantiations

## Notes

- This package is relatively isolated, should be straightforward
- Keep any existing Pydantic models for type hints
- Verify JSON schema files exist in correct locations
