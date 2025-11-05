# Step 5: Update Schema Instantiations in Remaining Packages

**Phase:** 1 - Schema Infrastructure
**Dependencies:** Step 4 complete
**Estimated Scope:** Multiple small packages
**Status:** ✅ Completed

## Purpose

Update schema instantiations in remaining packages: waivern-mysql, waivern-rulesets, waivern-connectors-database, and wct.

## Packages to Update

### 1. waivern-mysql

**Files to update:**
- `libs/waivern-mysql/src/waivern_mysql/connector.py`
- `libs/waivern-mysql/src/waivern_mysql/factory.py`
- `libs/waivern-mysql/tests/waivern_mysql/test_connector.py`
- `libs/waivern-mysql/tests/waivern_mysql/test_factory.py`

**Pattern:**
```python
# Before
from waivern_core.schemas.standard_input import StandardInputSchema

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    return [StandardInputSchema()]

# After
from waivern_core.schemas.base import Schema

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    return [Schema("standard_input", "1.0.0")]
```

**Testing:**
```bash
cd libs/waivern-mysql
./scripts/dev-checks.sh
```

---

### 2. waivern-rulesets

**Files to check:**
- Likely no schema instantiations (just pattern definitions)
- Check anyway: `grep -r "Schema()" libs/waivern-rulesets/src/ --include="*.py"`
- If found, update to new pattern

**Testing:**
```bash
cd libs/waivern-rulesets
./scripts/dev-checks.sh
```

---

### 3. waivern-connectors-database

**Files to update:**
- `libs/waivern-connectors-database/src/waivern_connectors_database/base_connector.py`
- `libs/waivern-connectors-database/src/waivern_connectors_database/schema_utils.py`
- `libs/waivern-connectors-database/tests/waivern_connectors_database/test_base_connector.py`
- `libs/waivern-connectors-database/tests/waivern_connectors_database/test_schema_utils.py`

**Pattern:**
```python
# Before
from waivern_core.schemas.standard_input import StandardInputSchema

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    return [StandardInputSchema()]

# After
from waivern_core.schemas.base import Schema

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    return [Schema("standard_input", "1.0.0")]
```

**Testing:**
```bash
cd libs/waivern-connectors-database
./scripts/dev-checks.sh
```

---

### 4. wct (Application)

This is the application layer and may have extensive schema usage.

**Files to update:**

**Source files:**
- `apps/wct/src/wct/executor.py`
- `apps/wct/src/wct/analysis.py`
- `apps/wct/src/wct/cli.py` (if schemas used)
- `apps/wct/src/wct/schemas/runbook.py` (if schemas referenced)

**Test files:**
- `apps/wct/tests/test_executor.py`
- `apps/wct/tests/test_analysis.py`
- `apps/wct/tests/test_cli.py`
- `apps/wct/tests/schemas/test_*.py` (all schema test files)
- `apps/wct/tests/integration/test_*.py`

**Search for schema usage:**
```bash
cd apps/wct
grep -r "StandardInputSchema\|PersonalDataFindingSchema\|SourceCodeSchema\|ProcessingPurposeFindingSchema\|DataSubjectFindingSchema" . --include="*.py"
```

**Common patterns in WCT:**

Schema comparison in tests:
```python
# Before
assert message.schema == StandardInputSchema()

# After
assert message.schema == Schema("standard_input", "1.0.0")
```

Schema matching in executor:
```python
# Before
if message.schema == StandardInputSchema():
    ...

# After
if message.schema == Schema("standard_input", "1.0.0"):
    ...
```

**Testing:**
```bash
cd apps/wct
./scripts/dev-checks.sh
```

---

## Search Strategy for All Packages

```bash
# From repository root
for pkg in libs/waivern-mysql libs/waivern-rulesets libs/waivern-connectors-database apps/wct; do
    echo "=== Checking $pkg ==="
    grep -r "Schema()" "$pkg" --include="*.py" | grep -v "# " | head -20
done
```

## Testing Strategy

Test each package individually in order:

1. **waivern-mysql** (smallest, easiest)
2. **waivern-rulesets** (probably no changes)
3. **waivern-connectors-database** (medium complexity)
4. **wct** (largest, most complex)

After all packages updated, run full workspace tests:
```bash
./scripts/dev-checks.sh
```

## Expected Results

After this step:
- ✅ All packages updated to new Schema pattern
- ✅ No schema subclass imports remain
- ✅ All 845+ tests pass
- ✅ Zero type errors across workspace
- ✅ All linting passes

## Key Decisions

- **Test incrementally:** One package at a time
- **WCT is complex:** May have many schema usages, take time
- **Schema names:** Double-check against JSON files

## Notes

- WCT tests may have complex schema assertions
- Some tests may check schema metadata - update accordingly
- Integration tests in WCT may use multiple schema types
- After this step, Phase 1 (Schema Infrastructure) is complete!
