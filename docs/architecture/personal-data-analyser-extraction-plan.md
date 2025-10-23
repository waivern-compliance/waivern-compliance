# Personal Data Analyser Extraction Plan

**Status:** ✅ COMPLETED
**Date:** 2025-10-21
**Updated:** 2025-10-23
**Completed:** 2025-10-23
**Objective:** Extract PersonalDataAnalyser from waivern-community into standalone package

---

## Executive Summary

Extract `PersonalDataAnalyser` from `waivern-community` into standalone `waivern-personal-data-analyser` package (~612 lines).

This extraction enables:
- Minimal dependencies for users wanting only PersonalDataAnalyser
- Independent versioning and maintenance
- Users can install only what they need (~612 lines vs entire community package)
- Cleaner architecture with clear separation of concerns

**Prerequisite:** `.development/analysers-shared-extraction-plan.md` must be completed first (✅ COMPLETED - PR #161)

---

## Architecture Overview

### Current State (Before Extraction)

```
waivern-analysers-shared/           ✅ EXISTS (from prerequisite)
├── utilities/
│   ├── evidence_extractor.py
│   ├── llm_service_manager.py
│   └── ruleset_manager.py
├── llm_validation/
│   ├── strategy.py
│   ├── decision_engine.py
│   ├── json_utils.py
│   └── models.py
└── types.py

waivern-community/
└── analysers/
    ├── personal_data_analyser/       (~612 lines - TO EXTRACT)
    ├── data_subject_analyser/        (using waivern-analysers-shared)
    └── processing_purpose_analyser/  (using waivern-analysers-shared)
```

### Target State (After Extraction)

```
waivern-personal-data-analyser/     (NEW - ~612 lines)
├── analyser.py                     (306 lines)
├── pattern_matcher.py              (98 lines)
├── llm_validation_strategy.py      (79 lines)
├── types.py                        (69 lines)
└── schemas/
    ├── personal_data_finding.py    (45 lines)
    └── json_schemas/
        └── personal_data_finding/1.0.0/
            ├── personal_data_finding.json
            └── personal_data_finding.sample.json

waivern-community/
└── analysers/
    ├── data_subject_analyser/       (remains in community)
    ├── processing_purpose_analyser/ (remains in community)
    └── __init__.py                  (re-exports PersonalDataAnalyser)
```

### Dependency Graph

```
waivern-core
    ↓
waivern-llm, waivern-rulesets
    ↓
waivern-analysers-shared ✅ EXISTS
    ↓
waivern-personal-data-analyser (NEW)
    ↓
waivern-community (re-exports for backward compatibility)
    ↓
wct
```

---

## Code Analysis

### PersonalDataAnalyser-Specific Code (612 lines)

**Import Dependencies:**
```python
# From waivern-analysers-shared (already exists):
from waivern_analysers_shared import (
    EvidenceExtractor,
    LLMServiceManager,
    RulesetManager,
    LLMValidationStrategy,
    LLMValidationResultModel,
    extract_json_from_llm_response,
    PatternMatchingConfig,
    LLMValidationConfig,
)

# From waivern-core:
from waivern_core import Analyser
from waivern_core.message import Message
from waivern_core.schemas import (
    StandardInputSchema,
    StandardInputDataModel,
    BaseAnalysisOutputMetadata,
    # ...
)

# From waivern-rulesets:
# (via RulesetManager)
```

**Test Coverage:**
- 38 tests in `tests/waivern_community/analysers/personal_data_analyser/`
- Tests cover: analyser logic, LLM validation strategy, pattern matching, schemas

---

## Implementation Plan

### Phase 1: Create waivern-personal-data-analyser Package

**Status:** ✅ COMPLETED

#### 1.1 Create Package Structure

```bash
mkdir -p libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schemas
mkdir -p libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser
mkdir -p libs/waivern-personal-data-analyser/scripts

# CRITICAL: Create py.typed marker INSIDE the package directory (not at package root!)
# Location: libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/py.typed
touch libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/py.typed
```

**IMPORTANT - py.typed location:**
- ✅ CORRECT: `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/py.typed` (inside package)
- ❌ WRONG: `libs/waivern-personal-data-analyser/py.typed` (at package root)

#### 1.2 Copy and Update Package Scripts

Copy script templates from waivern-core (uses comprehensive type checking):

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-personal-data-analyser/scripts/
chmod +x libs/waivern-personal-data-analyser/scripts/*.sh
```

**Update package-specific comments in scripts:**

The waivern-core scripts already check everything (`.`) for comprehensive type checking. Only update the comment header in `type-check.sh`:

```bash
# Change this:
# Run static type checking for waivern-core package

# To this:
# Run static type checking for waivern-personal-data-analyser package
```

**All three scripts:**
- **`lint.sh`**: ✅ Ready to use (may need comment update)
- **`format.sh`**: ✅ Ready to use (may need comment update)
- **`type-check.sh`**: ⚠️ Update package name in comment

**Rationale:** Copying from waivern-core ensures we get the comprehensive type checking pattern (`.`) that provides full coverage of the package, not just `src/ tests/`.

#### 1.3 Create pyproject.toml

```toml
[project]
name = "waivern-personal-data-analyser"
version = "0.1.0"
description = "Personal data analyser for Waivern Compliance Framework"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-analysers-shared",
    "waivern-rulesets",
    "pydantic>=2.11.5",
]

[dependency-groups]
dev = [
    "basedpyright>=1.29.2",
    "ruff>=0.11.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
dev-mode-dirs = ["src"]

# Include JSON schemas and py.typed marker
include = [
    "src/waivern_personal_data_analyser/**/*.py",
    "src/waivern_personal_data_analyser/**/schemas/json_schemas/**/*.json",
    "src/waivern_personal_data_analyser/py.typed",
]

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_personal_data_analyser"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "ANN",    # flake8-annotations - enforce type annotations
    "B",      # flake8-bugbear - find likely bugs and design problems
    "D",      # pydocstyle - docstring style checking
    "F",      # pyflakes - detect various errors
    "I",      # isort - import sorting
    "PL",     # pylint - comprehensive code analysis
    "RUF100", # ruff-specific - detect unused noqa directives
    "S",      # flake8-bandit - security issue detection
    "UP",     # pyupgrade - upgrade syntax for newer Python versions
]
ignore = [
    "D203",    # one-blank-line-before-class - conflicts with D211 (no-blank-line-before-class)
    "D213",    # multi-line-summary-second-line - conflicts with D212 (multi-line-summary-first-line)
]

[tool.ruff.lint.pydocstyle]
ignore-decorators = ["typing.overload"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",    # assert-used - assert statements are standard in pytest
    "PLR2004", # magic-value-comparison - magic values are acceptable in tests
]
```

#### 1.4 Create README.md

```markdown
# waivern-personal-data-analyser

Personal data analyser for Waivern Compliance Framework.

## Overview

Identifies personal data patterns in content using:
- Pattern matching with predefined rulesets
- LLM-based validation to filter false positives
- Evidence extraction with configurable context

## Installation

```bash
pip install waivern-personal-data-analyser
```

## Usage

```python
from waivern_personal_data_analyser import PersonalDataAnalyser

# Used via WCT runbooks or programmatically
```

## Development

See [CLAUDE.md](../../CLAUDE.md) for development guidelines.
```

#### 1.5 Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/* \
      libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/
```

#### 1.6 Update Imports

Update all Python files to use new imports:

```python
# Imports already correct (updated in prerequisite extraction)
from waivern_analysers_shared import (
    LLMServiceManager,
    LLMValidationStrategy,
    PatternMatchingConfig,
    LLMValidationConfig,
    EvidenceExtractor,
    RulesetManager,
    ValidationDecisionEngine,
    LLMValidationResultModel,
    extract_json_from_llm_response,
)
```

**Files to verify (should already be correct):**
- `analyser.py`
- `pattern_matcher.py`
- `llm_validation_strategy.py`
- `types.py`

#### 1.7 Package Exports

`src/waivern_personal_data_analyser/__init__.py`:
```python
"""Personal data analyser for Waivern Compliance Framework."""

from .analyser import PersonalDataAnalyser
from .schemas import PersonalDataFindingModel, PersonalDataFindingSchema
from .types import PersonalDataAnalyserConfig

__all__ = [
    "PersonalDataAnalyser",
    "PersonalDataFindingModel",
    "PersonalDataFindingSchema",
    "PersonalDataAnalyserConfig",
]
```

#### 1.8 Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/analysers/personal_data_analyser/* \
   libs/waivern-personal-data-analyser/tests/waivern_personal_data_analyser/
```

Update test imports:
```python
# Before
from waivern_community.analysers.personal_data_analyser import PersonalDataAnalyser

# After
from waivern_personal_data_analyser import PersonalDataAnalyser
```

#### 1.9 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    # ... existing packages
    "libs/waivern-analysers-shared",
    "libs/waivern-personal-data-analyser",  # ADD THIS
    "libs/waivern-community",
    # ...
]

[tool.uv.sources]
# ... existing sources
waivern-analysers-shared = { workspace = true }
waivern-personal-data-analyser = { workspace = true }  # ADD THIS
```

#### 1.10 Initial Package Installation

```bash
uv sync --package waivern-personal-data-analyser
uv run python -c "import waivern_personal_data_analyser; print('✓ Package installed')"
```

#### 1.11 Run Package Tests

```bash
cd libs/waivern-personal-data-analyser
uv run pytest tests/ -v
# Expected: 38 tests passing
```

#### 1.12 Update Root Workspace Scripts

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add after waivern-analysers-shared (in dependency order)
(cd libs/waivern-personal-data-analyser && ./scripts/lint.sh "$@")
```

#### 1.13 Update Pre-commit Wrapper Scripts

Update `scripts/pre-commit-lint.sh`, `scripts/pre-commit-format.sh`, `scripts/pre-commit-type-check.sh`:

```bash
# Add file grouping array
personal_data_analyser_files=()

# Add pattern matching
elif [[ "$file" == libs/waivern-personal-data-analyser/* ]]; then
    personal_data_analyser_files+=("${file#libs/waivern-personal-data-analyser/}")

# Add processing block (after analysers-shared)
if [ ${#personal_data_analyser_files[@]} -gt 0 ]; then
    (cd libs/waivern-personal-data-analyser && ./scripts/lint.sh "${personal_data_analyser_files[@]}")
fi
```

#### 1.14 Run Dev-Checks and Fix Linting Errors

```bash
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-personal-data.txt
```

---

### Phase 2: Update waivern-community

**Status:** ✅ COMPLETED

#### 2.1 Update Dependencies

Update `libs/waivern-community/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-connectors-database",
    "waivern-mysql",
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-personal-data-analyser",  # ADD THIS
    "pyyaml>=6.0.2",
    "pydantic>=2.11.5",
    "typing-extensions>=4.14.0",
]
```

#### 2.2 Update Component Exports

Update `src/waivern_community/analysers/__init__.py`:

```python
"""WCT analysers."""

from waivern_core import (
    Analyser,
    AnalyserError,
    AnalyserInputError,
    AnalyserProcessingError,
)

# Import from standalone packages
from waivern_personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFindingModel,
)

# Import from waivern_community
from waivern_community.analysers.data_subject_analyser import (
    DataSubjectAnalyser,
    DataSubjectFindingModel,
)
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeFindingModel,
)

# Re-export shared types for convenience
from waivern_analysers_shared import LLMValidationConfig, PatternMatchingConfig

__all__ = (
    "Analyser",
    "AnalyserError",
    "AnalyserInputError",
    "AnalyserProcessingError",
    "DataSubjectAnalyser",
    "DataSubjectFindingModel",
    "PersonalDataAnalyser",  # Re-exported from standalone package
    "PersonalDataFindingModel",
    "ProcessingPurposeAnalyser",
    "ProcessingPurposeFindingModel",
    "LLMValidationConfig",
    "PatternMatchingConfig",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (
    DataSubjectAnalyser,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
)
```

#### 2.3 Delete Extracted Code

Remove PersonalDataAnalyser from waivern-community:

```bash
# Delete personal_data_analyser (now in standalone package)
rm -rf libs/waivern-community/src/waivern_community/analysers/personal_data_analyser
rm -rf libs/waivern-community/tests/waivern_community/analysers/personal_data_analyser
```

#### 2.4 Run Quality Checks and Fix All Errors

**CRITICAL:** Run dev-checks and fix ALL errors immediately, including downstream errors in WCT or other packages. Do not leave broken tests for later phases.

```bash
# Run full workspace dev-checks
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-phase2.txt
```

**Fix errors as they appear:**

1. **waivern-community errors:**
   - Update any remaining imports in `src/waivern_community/__init__.py`
   - Fix any references to old package paths

2. **WCT errors (if dev-checks reveals them):**
   - Update `apps/wct/src/wct/schemas/__init__.py` to import from standalone package:
     ```python
     from waivern_personal_data_analyser.schemas import PersonalDataFindingSchema
     ```
   - Update any WCT test files that import from old paths:
     ```python
     # Before
     from waivern_community.analysers.personal_data_analyser.types import ...
     # After
     from waivern_personal_data_analyser.types import ...
     ```
   - Fix any patch paths in tests:
     ```python
     # Before
     @patch("waivern_community.analysers.personal_data_analyser.analyser.personal_data_validation_strategy")
     # After
     @patch("waivern_personal_data_analyser.analyser.personal_data_validation_strategy")
     ```

3. **Re-run dev-checks until all pass:**
   ```bash
   ./scripts/dev-checks.sh
   # Expected: All tests passing (752 tests), 0 type errors, all lint checks passed
   ```

**Expected results:**
- ✅ All waivern-community tests pass
- ✅ All WCT tests pass
- ✅ Type checking passes (0 errors)
- ✅ Linting passes
- ✅ Total: 752 tests passing

**Do not proceed to Phase 3 if any errors remain!**

---

### Phase 3: Update WCT Application

**Status:** ✅ COMPLETED

**Note:** If you followed Phase 2.4 correctly, WCT imports and tests were already fixed during quality checks. This phase is primarily for adding dependencies if not already done.

#### 3.1 Update Dependencies (if needed)

Check if `apps/wct/pyproject.toml` needs updating:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-analysers-shared",        # May already be present
    "waivern-personal-data-analyser",  # ADD if not present
    "waivern-community",
    # ... rest
]
```

**Note:** waivern-community already depends on waivern-personal-data-analyser, so WCT gets it transitively. Only add explicit dependency if needed for direct imports.

#### 3.2 Verify WCT Still Works

```bash
# Verify analyser is registered
uv run wct ls-analysers | grep personal

# Expected output shows: personal_data_analyser
```

---

### Phase 4: Verification & Testing

**Status:** ✅ COMPLETED

#### 4.1 Workspace Sync

```bash
uv sync
```

#### 4.2 Test New Package

```bash
cd libs/waivern-personal-data-analyser
uv run pytest tests/ -v
# Expected: 38 tests passing
```

#### 4.3 Full Test Suite

```bash
cd /Users/lwkz/Workspace/waivern-compliance
uv run pytest
# Expected: 752 tests passing (same count, different package locations)
```

#### 4.4 Quality Checks

```bash
./scripts/dev-checks.sh
# Expected: All checks passing
```

#### 4.5 Verify Integration

```bash
# List analysers
uv run wct ls-analysers | grep personal_data_analyser

# Validate sample runbook
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml

# Run sample analysis
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
```

---

### Phase 5: Update Documentation

**Status:** ✅ COMPLETED

#### 5.1 Update CLAUDE.md

Update package structure:

```markdown
libs/
├── waivern-core/
├── waivern-llm/
├── waivern-connectors-database/
├── waivern-mysql/
├── waivern-rulesets/
├── waivern-analysers-shared/
├── waivern-personal-data-analyser/  # NEW
└── waivern-community/
```

Update package descriptions:

```markdown
**Framework Libraries:**
- **waivern-core**: Base abstractions
- **waivern-llm**: Multi-provider LLM service
- **waivern-connectors-database**: Shared SQL connector utilities
- **waivern-mysql**: MySQL connector (standalone)
- **waivern-rulesets**: YAML-based rulesets
- **waivern-analysers-shared**: Shared analyser utilities
- **waivern-personal-data-analyser**: Personal data analyser (standalone)
- **waivern-community**: Built-in components (re-exports standalone packages)
```

#### 5.2 Update Migration Documentation

Update:
- `docs/architecture/monorepo-migration-plan.md` - Mark Phase 5 complete
- `docs/architecture/monorepo-migration-completed.md` - Add Phase 5 details

#### 5.3 Create Package README

**`libs/waivern-personal-data-analyser/README.md`:**
```markdown
# waivern-personal-data-analyser

Personal data analyser for Waivern Compliance Framework.

## Overview

Identifies personal data patterns in content using:
- Pattern matching with predefined rulesets
- LLM-based validation to filter false positives
- Evidence extraction with configurable context

## Installation

```bash
pip install waivern-personal-data-analyser
```

## Usage

```python
from waivern_personal_data_analyser import PersonalDataAnalyser

# Used via WCT runbooks or programmatically
```

## Development

See [CLAUDE.md](../../CLAUDE.md) for development guidelines.
```

---

### Phase 6: Commit Changes

**Status:** ✅ COMPLETED

#### 6.1 Commit Message

```
refactor: extract PersonalDataAnalyser as standalone package

Extract PersonalDataAnalyser from waivern-community into standalone
waivern-personal-data-analyser package for minimal dependencies and
independent versioning.

Architecture:
- Create libs/waivern-personal-data-analyser/ package
  * PersonalDataAnalyser and PersonalDataAnalyserConfig
  * Depends on waivern-analysers-shared for shared utilities
  * ~612 lines of component-specific code
  * 38 tests
- Update waivern-community
  * Imports and re-exports PersonalDataAnalyser from standalone package
  * Maintains backward compatibility via re-exports
- Update WCT
  * Add waivern-personal-data-analyser dependency

Dependency graph:
  waivern-core
      ↓
  waivern-llm, waivern-rulesets
      ↓
  waivern-analysers-shared
      ↓
  waivern-personal-data-analyser (NEW)
      ↓
  waivern-community (re-exports)
      ↓
  wct

Benefits:
- Minimal dependencies: Users wanting only PersonalDataAnalyser get ~1,359 lines
  (analyser + shared) vs entire community package
- Independent versioning and maintenance
- Enables third-party contributions

Test results:
- All 752 tests passing
- Type checking: 0 errors (strict mode)
- Linting: all checks passed
- file_content_analysis.yaml validates successfully
```

---

## Success Criteria Checklist

- [ ] waivern-personal-data-analyser package created with all tests passing (38 tests)
- [ ] waivern-community updated (imports from new package)
- [ ] WCT dependencies updated
- [ ] Pre-commit scripts updated
- [ ] Orchestration scripts updated (lint, format, type-check)
- [ ] All 752 tests passing
- [ ] All quality checks passing (dev-checks.sh)
- [ ] Sample runbook verified (file_content_analysis.yaml)
- [ ] Documentation updated (CLAUDE.md, migration docs, package README)
- [ ] Changes committed to git

---

## Notes

- Prerequisite `.development/analysers-shared-extraction-plan.md` completed (PR #161)
- PersonalDataAnalyser already uses waivern-analysers-shared utilities (imports updated in prerequisite)
- Test count should remain 752 (same tests, different package locations)
- Maintains backward compatibility via waivern-community re-exports
