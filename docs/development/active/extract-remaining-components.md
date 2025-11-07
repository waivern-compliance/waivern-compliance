# Implementation Plan: Extract Remaining Components from waivern-community

**Status:** Draft
**Created:** 2025-11-07
**Components to Extract:** 5 (3 connectors, 2 analysers)
**Final Step:** Complete removal of waivern-community package

---

## Overview

Extract all remaining components from waivern-community into standalone packages for minimal dependencies and independent versioning. This follows the pattern established with `waivern-personal-data-analyser` and `waivern-mysql`.

### Components Remaining in waivern-community

**Connectors:**
1. `filesystem` → `waivern-filesystem` (~604 LOC, 6 tests)
2. `sqlite` → `waivern-sqlite` (~560 LOC, 6 tests)
3. `source_code` → `waivern-source-code` (~1,658 LOC, 7 tests)

**Analysers:**
4. `data_subject_analyser` → `waivern-data-subject-analyser` (~715 LOC, 6 tests)
5. `processing_purpose_analyser` → `waivern-processing-purpose-analyser` (~1,212 LOC, 12 tests)

### Already Extracted (Re-exported from waivern-community)

- ✅ `waivern-personal-data-analyser` (PersonalDataAnalyser)
- ✅ `waivern-mysql` (MySQLConnector)
- ✅ `waivern-connectors-database` (Shared database utilities)
- ✅ `waivern-rulesets` (Shared rulesets)
- ✅ `waivern-analysers-shared` (Shared analyser utilities)

---

## Dependency Graph

```
waivern-core
    ↓
waivern-llm
    ↓
waivern-connectors-database ────→ waivern-sqlite (NEW)
    ↓
waivern-filesystem (NEW) ────────→ waivern-source-code (NEW)
    ↓                                      ↓
waivern-rulesets                  waivern-processing-purpose-analyser (NEW)
    ↓
waivern-analysers-shared
    ↓
waivern-data-subject-analyser (NEW)
    ↓
wct (imports directly from standalone packages)
```

**Critical Dependencies:**
- `source_code` depends on `filesystem` connector
- `processing_purpose_analyser` depends on `source_code.schemas`
- `wct` imports directly from all standalone packages (no waivern-community layer)

---

## Extraction Order (Phase-Based)

### Phase 1: Independent Connectors (No Internal Dependencies)

#### 1.1 Extract `waivern-filesystem`
- **Complexity:** 🟢 Low
- **Risk:** 🟢 Low
- **Dependencies:** `waivern-core` only
- **Needed By:** `waivern-source-code`

#### 1.2 Extract `waivern-sqlite`
- **Complexity:** 🟢 Low
- **Risk:** 🟢 Low
- **Dependencies:** `waivern-core`, `waivern-connectors-database`
- **Needed By:** None

### Phase 2: Source Code Connector (Depends on filesystem)

#### 2.1 Extract `waivern-source-code`
- **Complexity:** 🟡 Medium
- **Risk:** 🟡 Medium
- **Dependencies:** `waivern-core`, `waivern-filesystem`
- **Needed By:** `waivern-processing-purpose-analyser`
- **Special Notes:**
  - Has custom schema (`source_code/1.0.0`)
  - Optional dependencies: `tree-sitter>=0.21.0`, `tree-sitter-php>=0.22.0`
  - Must update import from `waivern_community.connectors.filesystem` → `waivern_filesystem`

### Phase 3: Independent Analyser

#### 3.1 Extract `waivern-data-subject-analyser`
- **Complexity:** 🟡 Medium
- **Risk:** 🟢 Low
- **Dependencies:** `waivern-core`, `waivern-llm`, `waivern-analysers-shared`, `waivern-rulesets`
- **Needed By:** None
- **Special Notes:**
  - Has custom schema (`data_subject_finding/1.0.0`)
  - Uses `"data_subjects"` ruleset from waivern-rulesets

### Phase 4: Processing Purpose Analyser (Depends on source_code)

#### 4.1 Extract `waivern-processing-purpose-analyser`
- **Complexity:** 🟠 High
- **Risk:** 🟡 Medium
- **Dependencies:** `waivern-core`, `waivern-llm`, `waivern-analysers-shared`, `waivern-rulesets`, `waivern-source-code`
- **Needed By:** None
- **Special Notes:**
  - Has custom schema (`processing_purpose_finding/1.0.0`)
  - Uses `"processing_purposes"` ruleset from waivern-rulesets
  - Supports both `standard_input` AND `source_code` schemas
  - Must update import from `waivern_community.connectors.source_code.schemas` → `waivern_source_code.schemas`
  - Must move `prompts/processing_purpose_validation.py` into this package

### Phase 5: Remove waivern-community Package

#### 5.1 Update WCT Imports
- **Complexity:** 🟡 Medium
- **Risk:** 🟢 Low
- **Tasks:**
  - Update `apps/wct/pyproject.toml` to depend on all standalone packages directly
  - Find and replace all imports from `waivern_community` to standalone package imports
  - Update schema imports in WCT tests and application code
  - Verify all component discovery works

#### 5.2 Delete waivern-community
- **Tasks:**
  - Remove `waivern-community = { workspace = true }` from root `pyproject.toml`
  - Delete `libs/waivern-community/` directory
  - Run full workspace sync and tests
  - Update `CLAUDE.md` to remove waivern-community references

---

## Detailed Implementation Steps

For each component, follow the [Component Extraction Template](../guides/component-extraction-template.md).

### Component-Specific Variables

#### `waivern-filesystem`

```bash
PACKAGE_NAME="waivern-filesystem"
PACKAGE_MODULE="waivern_filesystem"
COMPONENT_TYPE="connector"
COMPONENT_NAME="FilesystemConnector"
CONFIG_NAME="FilesystemConnectorConfig"
SCHEMA_NAME="N/A"  # Uses standard_input schema
DESCRIPTION="Filesystem connector for WCF"
SHARED_PACKAGE="N/A"
CURRENT_LOCATION="connectors/filesystem/"
TEST_COUNT="~6"
```

#### `waivern-sqlite`

```bash
PACKAGE_NAME="waivern-sqlite"
PACKAGE_MODULE="waivern_sqlite"
COMPONENT_TYPE="connector"
COMPONENT_NAME="SQLiteConnector"
CONFIG_NAME="SQLiteConnectorConfig"
SCHEMA_NAME="N/A"  # Uses standard_input schema
DESCRIPTION="SQLite connector for WCF"
SHARED_PACKAGE="waivern-connectors-database"
CURRENT_LOCATION="connectors/sqlite/"
TEST_COUNT="~6"
```

#### `waivern-source-code`

```bash
PACKAGE_NAME="waivern-source-code"
PACKAGE_MODULE="waivern_source_code"
COMPONENT_TYPE="connector"
COMPONENT_NAME="SourceCodeConnector"
CONFIG_NAME="SourceCodeConnectorConfig"
SCHEMA_NAME="SourceCodeSchema"
DESCRIPTION="Source code connector for WCF"
SHARED_PACKAGE="N/A"
CURRENT_LOCATION="connectors/source_code/"
TEST_COUNT="~7"
```

**Additional dependencies for pyproject.toml:**
```toml
dependencies = [
    "waivern-core",
    "waivern-filesystem",
]

[project.optional-dependencies]
tree-sitter = [
    "tree-sitter>=0.21.0",
    "tree-sitter-php>=0.22.0",
]
```

**Import updates required:**
```python
# Before:
from waivern_community.connectors.filesystem import FilesystemConnector, FilesystemConnectorConfig

# After:
from waivern_filesystem import FilesystemConnector, FilesystemConnectorConfig
```

#### `waivern-data-subject-analyser`

```bash
PACKAGE_NAME="waivern-data-subject-analyser"
PACKAGE_MODULE="waivern_data_subject_analyser"
COMPONENT_TYPE="analyser"
COMPONENT_NAME="DataSubjectAnalyser"
CONFIG_NAME="DataSubjectAnalyserConfig"
SCHEMA_NAME="DataSubjectFindingSchema"
DESCRIPTION="Data subject analyser for WCF"
SHARED_PACKAGE="waivern-analysers-shared"
CURRENT_LOCATION="analysers/data_subject_analyser/"
TEST_COUNT="~6"
```

**Additional dependencies for pyproject.toml:**
```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-analysers-shared",
    "waivern-rulesets",
]
```

#### `waivern-processing-purpose-analyser`

```bash
PACKAGE_NAME="waivern-processing-purpose-analyser"
PACKAGE_MODULE="waivern_processing_purpose_analyser"
COMPONENT_TYPE="analyser"
COMPONENT_NAME="ProcessingPurposeAnalyser"
CONFIG_NAME="ProcessingPurposeAnalyserConfig"
SCHEMA_NAME="ProcessingPurposeFindingSchema"
DESCRIPTION="Processing purpose analyser for WCF"
SHARED_PACKAGE="waivern-analysers-shared"
CURRENT_LOCATION="analysers/processing_purpose_analyser/"
TEST_COUNT="~12"
```

**Additional dependencies for pyproject.toml:**
```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-analysers-shared",
    "waivern-rulesets",
    "waivern-source-code",  # For source code schema support
]
```

**Import updates required:**
```python
# Before:
from waivern_community.connectors.source_code.schemas import (
    SourceCodeDataModel,
    FunctionModel,
    ClassModel,
)

# After:
from waivern_source_code.schemas import (
    SourceCodeDataModel,
    FunctionModel,
    ClassModel,
)
```

**Additional file to move:**
- Copy `libs/waivern-community/src/waivern_community/prompts/processing_purpose_validation.py`
- To `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/prompts/`
- Update import in analyser.py

---

## Special Considerations

### 1. Schema Registration

Each package with schemas must register its schema directory in `__init__.py`:

**waivern-source-code:**
```python
from pathlib import Path
from waivern_core.schemas import SchemaRegistry

_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)
```

**waivern-data-subject-analyser:**
```python
from pathlib import Path
from waivern_core.schemas import SchemaRegistry

_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)
```

**waivern-processing-purpose-analyser:**
```python
from pathlib import Path
from waivern_core.schemas import SchemaRegistry

_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)
```

### 2. Processing Purpose Prompts Migration

The `processing_purpose_validation.py` prompt currently lives in `waivern-community/prompts/`.

**Steps:**
1. Create `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/prompts/`
2. Move `processing_purpose_validation.py` to new location
3. Update import in `analyser.py`:
   ```python
   # Before:
   from waivern_community.prompts.processing_purpose_validation import PROCESSING_PURPOSE_VALIDATION_PROMPT

   # After:
   from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import PROCESSING_PURPOSE_VALIDATION_PROMPT
   ```

### 3. Optional Dependencies for Source Code Connector

The source code connector uses tree-sitter for PHP parsing. Define as optional:

```toml
[project.optional-dependencies]
tree-sitter = [
    "tree-sitter>=0.21.0",
    "tree-sitter-php>=0.22.0",
]
all = ["waivern-source-code[tree-sitter]"]
```

### 4. Workspace Sources Update

Add all new packages to root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-filesystem = { workspace = true }
waivern-sqlite = { workspace = true }
waivern-source-code = { workspace = true }
waivern-data-subject-analyser = { workspace = true }
waivern-processing-purpose-analyser = { workspace = true }
```

### 5. Remove waivern-community Package Completely

After all components are extracted, remove waivern-community entirely instead of keeping it as a re-export package.

#### 5.1 Update WCT to Import Directly from Standalone Packages

**Update `apps/wct/pyproject.toml` dependencies:**

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    # Connectors
    "waivern-connectors-database",
    "waivern-mysql",
    "waivern-filesystem",
    "waivern-sqlite",
    "waivern-source-code",
    # Analysers
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-personal-data-analyser",
    "waivern-data-subject-analyser",
    "waivern-processing-purpose-analyser",
    # Remove: "waivern-community",
]
```

**Update WCT imports throughout the application:**

Find and replace imports in `apps/wct/src/wct/`:

```python
# Before:
from waivern_community import (
    DataSubjectAnalyser,
    FilesystemConnector,
    MySQLConnector,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
    SourceCodeConnector,
    SQLiteConnector,
)

# After:
from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_filesystem import FilesystemConnector
from waivern_mysql import MySQLConnector
from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser
from waivern_source_code import SourceCodeConnector
from waivern_sqlite import SQLiteConnector
```

**Update schema imports in WCT:**

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

#### 5.2 Remove waivern-community from Workspace

**Update root `pyproject.toml`:**

```toml
[tool.uv.workspace]
members = [
    "libs/*",    # waivern-community will be deleted
    "apps/*",
]

[tool.uv.sources]
# ... keep all other sources
# Remove: waivern-community = { workspace = true }
```

#### 5.3 Delete waivern-community Package

```bash
# After verifying all tests pass with updated imports
rm -rf libs/waivern-community
```

#### 5.4 Update Documentation

**Update `CLAUDE.md` package structure:**

```markdown
libs/
├── waivern-core/
├── waivern-llm/
├── waivern-connectors-database/
├── waivern-mysql/
├── waivern-filesystem/
├── waivern-sqlite/
├── waivern-source-code/
├── waivern-rulesets/
├── waivern-analysers-shared/
├── waivern-personal-data-analyser/
├── waivern-data-subject-analyser/
└── waivern-processing-purpose-analyser/
```

**Update package descriptions in `CLAUDE.md`:**

Remove any mention of "re-exports from waivern-community" and update:

```markdown
**Framework Libraries:**
- **waivern-core**: Base abstractions (Connector, Analyser, Message, Schema)
- **waivern-llm**: Multi-provider LLM service

**Shared Utilities:**
- **waivern-connectors-database**: Shared SQL connector utilities
- **waivern-rulesets**: Shared rulesets for pattern-based analysis
- **waivern-analysers-shared**: Shared analyser utilities

**Connectors:**
- **waivern-mysql**: MySQL connector
- **waivern-filesystem**: Filesystem connector
- **waivern-sqlite**: SQLite connector
- **waivern-source-code**: Source code connector with tree-sitter parsing

**Analysers:**
- **waivern-personal-data-analyser**: Personal data detection
- **waivern-data-subject-analyser**: Data subject identification
- **waivern-processing-purpose-analyser**: Processing purpose analysis

**Applications:**
- **wct**: CLI tool for compliance analysis
```

#### 5.5 Verification After Removal

```bash
# 1. Verify workspace sync works without waivern-community
uv sync

# 2. Verify WCT can import all components
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

# 3. Verify component discovery
uv run wct ls-connectors
uv run wct ls-analysers

# 4. Run all tests
./scripts/dev-checks.sh

# 5. Validate and run sample runbooks
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

---

## Verification Steps

After each extraction, verify:

### Package-Level Verification

```bash
# 1. Package installation
uv sync --package {PACKAGE_NAME}
uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"

# 2. Package tests
cd libs/{PACKAGE_NAME}
uv run pytest tests/ -v

# 3. Package quality checks
cd libs/{PACKAGE_NAME}
./scripts/lint.sh
./scripts/format.sh
./scripts/type-check.sh
```

### Workspace-Level Verification

```bash
# 4. Full workspace sync
uv sync

# 5. Full test suite
uv run pytest

# 6. All quality checks
./scripts/dev-checks.sh

# 7. Component registration (connectors)
uv run wct ls-connectors

# 8. Component registration (analysers)
uv run wct ls-analysers
```

### Integration Verification

```bash
# 9. Validate sample runbooks
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml

# 10. Run sample runbooks
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

---

## Expected Outcomes

### After All Extractions and Removal

**Standalone packages (total: 12):**

*Framework Libraries:*
1. waivern-core
2. waivern-llm

*Shared Utilities:*
3. waivern-connectors-database
4. waivern-rulesets
5. waivern-analysers-shared

*Connectors:*
6. waivern-mysql
7. waivern-filesystem (NEW)
8. waivern-sqlite (NEW)
9. waivern-source-code (NEW)

*Analysers:*
10. waivern-personal-data-analyser
11. waivern-data-subject-analyser (NEW)
12. waivern-processing-purpose-analyser (NEW)

**waivern-community:**
- ❌ **REMOVED** - No longer exists
- No backward compatibility layer
- Clean architecture with direct imports

**Benefits:**
- Users can install only needed components
- Independent versioning for each component
- Clearer dependency graph (no intermediary layer)
- Easier third-party contributions
- Smaller package sizes
- Simpler architecture without re-export complexity
- WCT has explicit dependencies on what it uses

---

## Success Criteria

- [ ] All 5 components extracted as standalone packages
- [ ] All package tests passing (~37 tests total)
- [ ] waivern-community completely removed from workspace
- [ ] WCT updated to import directly from standalone packages
- [ ] All WCT tests passing with new imports
- [ ] All quality checks passing (`./scripts/dev-checks.sh`)
- [ ] All sample runbooks validate and execute successfully
- [ ] Component discovery works in WCT (`wct ls-connectors`, `wct ls-analysers`)
- [ ] No references to waivern-community remain in codebase
- [ ] Documentation updated (CLAUDE.md, README.md files, migration docs)
- [ ] All changes committed with conventional commit messages
- [ ] Workspace contains exactly 12 standalone packages (no waivern-community)

---

## Rollback Plan

If issues arise during extraction:

1. **Per-component rollback:**
   - Delete standalone package directory
   - Restore component in waivern-community from git
   - Remove `[tool.uv.sources]` entry
   - Run `uv sync`

2. **Full rollback:**
   ```bash
   git reset --hard <commit-before-extractions>
   uv sync
   ./scripts/dev-checks.sh
   ```

---

## Notes

- Follow the extraction order strictly due to cross-component dependencies
- Run `./scripts/dev-checks.sh` after EACH extraction (including Phase 5)
- Fix all errors before proceeding to next component
- Each extraction should be a separate commit
- Consider creating a feature branch for the entire extraction effort
- Phase 5 (removing waivern-community) is the final cleanup step
- After Phase 5, verify NO references to waivern-community remain in:
  - `apps/wct/src/wct/` - Application code
  - `apps/wct/tests/` - Test code
  - `apps/wct/pyproject.toml` - Dependencies
  - Root `pyproject.toml` - Workspace configuration
  - `CLAUDE.md` - Documentation
- This completes the monorepo migration to fully independent packages

---

## References

- [Component Extraction Template](../guides/component-extraction-template.md)
- [Shared Package Extraction Template](../guides/shared-package-extraction-template.md)
- [Monorepo Migration Completed](../../roadmaps/monorepo-migration/monorepo-migration-completed.md)
