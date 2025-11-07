# Step 6: Update WCT to Import Directly from Standalone Packages

**Phase:** 5 - Remove waivern-community
**Complexity:** 🟡 Medium
**Risk:** 🟢 Low
**Dependencies:** Steps 1-5 must be complete
**Needed By:** Step 7 (final removal)

---

## Purpose

Update the WCT application to import components directly from standalone packages instead of through waivern-community. This removes the dependency on waivern-community and prepares for its complete removal.

---

## Context

After extracting all components (Steps 1-5), waivern-community is currently just a re-export layer. This step removes that dependency by updating WCT to import directly from the source packages. This is a preparation step for completely removing waivern-community in Step 7.

**Files to update:**
- `apps/wct/pyproject.toml` - Dependencies
- `apps/wct/src/wct/` - All Python files with waivern_community imports
- `apps/wct/tests/` - All test files with waivern_community imports

---

## Implementation Steps

### 1. Update WCT Dependencies

Update `apps/wct/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    # Connectors
    "waivern-connectors-database",
    "waivern-mysql",
    "waivern-filesystem",  # ADD
    "waivern-sqlite",  # ADD
    "waivern-source-code",  # ADD
    # Analysers
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-personal-data-analyser",
    "waivern-data-subject-analyser",  # ADD
    "waivern-processing-purpose-analyser",  # ADD
    # Remove this:
    # "waivern-community",
]
```

### 2. Find All waivern_community Imports

Search for all waivern_community imports in WCT:

```bash
# Find all files with waivern_community imports
grep -r "from waivern_community" apps/wct/src/wct/ apps/wct/tests/
grep -r "import waivern_community" apps/wct/src/wct/ apps/wct/tests/
```

### 3. Update Component Imports

**Pattern:** Replace waivern_community imports with direct package imports

#### Connectors

```python
# Before:
from waivern_community import (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)

# After:
from waivern_filesystem import FilesystemConnector
from waivern_mysql import MySQLConnector
from waivern_source_code import SourceCodeConnector
from waivern_sqlite import SQLiteConnector
```

#### Analysers

```python
# Before:
from waivern_community import (
    DataSubjectAnalyser,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
)

# After:
from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser
```

### 4. Update Schema Imports

**Pattern:** Replace waivern_community schema paths with standalone package paths

```python
# Before:
from waivern_community.analysers.data_subject_analyser.schemas import DataSubjectFindingModel
from waivern_community.analysers.processing_purpose_analyser.schemas import ProcessingPurposeFindingModel
from waivern_community.connectors.source_code.schemas import SourceCodeDataModel

# After:
from waivern_data_subject_analyser.schemas import DataSubjectFindingModel
from waivern_processing_purpose_analyser.schemas import ProcessingPurposeFindingModel
from waivern_source_code.schemas import SourceCodeDataModel
```

### 5. Update BUILTIN References

If WCT directly references BUILTIN_CONNECTORS or BUILTIN_ANALYSERS:

```python
# Before:
from waivern_community.connectors import BUILTIN_CONNECTORS
from waivern_community.analysers import BUILTIN_ANALYSERS

# After: Build tuples directly or create in WCT
BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)

BUILTIN_ANALYSERS = (
    DataSubjectAnalyser,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
)
```

### 6. Automated Import Updates

Use this script to help update imports (review changes before committing):

```bash
#!/bin/bash
# Save as scripts/update-wct-imports.sh

# Component imports
find apps/wct -name "*.py" -type f -exec sed -i '' \
  -e 's/from waivern_community import FilesystemConnector/from waivern_filesystem import FilesystemConnector/g' \
  -e 's/from waivern_community import MySQLConnector/from waivern_mysql import MySQLConnector/g' \
  -e 's/from waivern_community import SourceCodeConnector/from waivern_source_code import SourceCodeConnector/g' \
  -e 's/from waivern_community import SQLiteConnector/from waivern_sqlite import SQLiteConnector/g' \
  -e 's/from waivern_community import DataSubjectAnalyser/from waivern_data_subject_analyser import DataSubjectAnalyser/g' \
  -e 's/from waivern_community import PersonalDataAnalyser/from waivern_personal_data_analyser import PersonalDataAnalyser/g' \
  -e 's/from waivern_community import ProcessingPurposeAnalyser/from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser/g' \
  {} +

# Schema imports
find apps/wct -name "*.py" -type f -exec sed -i '' \
  -e 's|from waivern_community\.analysers\.data_subject_analyser\.schemas import|from waivern_data_subject_analyser.schemas import|g' \
  -e 's|from waivern_community\.analysers\.processing_purpose_analyser\.schemas import|from waivern_processing_purpose_analyser.schemas import|g' \
  -e 's|from waivern_community\.connectors\.source_code\.schemas import|from waivern_source_code.schemas import|g' \
  {} +

echo "✓ Imports updated - review changes with: git diff apps/wct"
```

**IMPORTANT:** Review all changes manually before proceeding.

### 7. Workspace Sync

```bash
uv sync
```

### 8. Verify Imports Work

```bash
# Test that all components are importable
uv run python -c "
from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_filesystem import FilesystemConnector
from waivern_mysql import MySQLConnector
from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser
from waivern_source_code import SourceCodeConnector
from waivern_sqlite import SQLiteConnector
print('✓ All components importable')
"
```

---

## Testing

### Component Discovery

```bash
# Verify all connectors are discoverable
uv run wct ls-connectors
# Expected: filesystem, mysql, source_code, sqlite

# Verify all analysers are discoverable
uv run wct ls-analysers
# Expected: data_subject, personal_data, processing_purpose
```

### Run All Tests

```bash
# WCT tests
cd apps/wct
uv run pytest tests/ -v

# Full workspace tests
cd /Users/lwkz/Workspace/waivern-compliance
uv run pytest
```

### Run Quality Checks

```bash
./scripts/dev-checks.sh
```

### Integration Tests

```bash
# Validate sample runbooks
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml

# Run sample runbooks
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

---

## Verification Checklist

After completing updates, verify:

- [ ] `apps/wct/pyproject.toml` lists all 5 new packages as dependencies
- [ ] `apps/wct/pyproject.toml` does NOT list waivern-community
- [ ] No imports from waivern_community in `apps/wct/src/wct/`
- [ ] No imports from waivern_community in `apps/wct/tests/`
- [ ] All WCT tests passing
- [ ] All workspace tests passing
- [ ] Component discovery works (`wct ls-connectors`, `wct ls-analysers`)
- [ ] Sample runbooks validate and run successfully
- [ ] No references to waivern_community.connectors.* paths
- [ ] No references to waivern_community.analysers.* paths

### Find Remaining References

```bash
# Should return NO results after Step 6 is complete:
grep -r "waivern_community" apps/wct/src/wct/ apps/wct/tests/

# Check pyproject.toml
grep "waivern-community" apps/wct/pyproject.toml
# Should return NO results
```

---

## Success Criteria

- [ ] WCT dependencies updated to include all 5 new standalone packages
- [ ] waivern-community removed from WCT dependencies
- [ ] All waivern_community imports replaced with standalone package imports
- [ ] All WCT tests passing
- [ ] All workspace tests passing
- [ ] Component discovery working
- [ ] Sample runbooks working
- [ ] No remaining references to waivern_community in WCT code
- [ ] Changes committed with message: `refactor: update WCT to import from standalone packages`

---

## Decisions Made

1. **Direct imports:** WCT imports components directly from source packages
2. **No BUILTIN re-exports:** If needed, WCT defines its own BUILTIN tuples
3. **Schema imports:** Updated to use standalone package schema paths
4. **Dependency list:** Explicit dependencies on all required packages
5. **No backward compatibility layer:** Clean break from waivern-community

---

## Notes

- This step can only be done after Steps 1-5 are complete
- Automated sed script provided but manual review is CRITICAL
- After this step, WCT no longer depends on waivern-community
- Step 7 will remove waivern-community entirely
- If issues arise, can temporarily revert by re-adding waivern-community dependency
