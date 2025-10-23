# Analysers Shared Package Extraction Plan

**Status:** ✅ COMPLETED & MERGED
**Date:** 2025-10-21
**Completed:** 2025-10-23 (PR #161)
**Objective:** Extract shared analyser utilities into standalone waivern-analysers-shared package

---

## Executive Summary

Extract shared utilities from `waivern-community/analysers` into new `waivern-analysers-shared` package (~747 lines).

This extraction enables:
- Foundation for future analyser extractions (PersonalData, DataSubject, ProcessingPurpose)
- Eliminates code duplication across analysers
- Independent versioning and maintenance
- Cleaner architecture with clear separation of concerns

**Related Extraction:** See `.development/personal-data-analyser-extraction-plan.md` for PersonalDataAnalyser extraction (Phase 2)

---

## Architecture Overview

### Current State (Before Extraction)

```
waivern-community/
└── analysers/
    ├── personal_data_analyser/      (uses shared utilities)
    ├── data_subject_analyser/       (uses shared utilities)
    ├── processing_purpose_analyser/ (uses shared utilities)
    ├── utilities/                   (~278 lines - shared)
    ├── llm_validation/              (~469 lines - shared)
    └── types.py                     (~50 lines - shared)
```

### Target State (After Extraction)

```
waivern-analysers-shared/           (NEW - ~747 lines)
├── utilities/
│   ├── evidence_extractor.py      (181 lines)
│   ├── llm_service_manager.py     (40 lines)
│   └── ruleset_manager.py         (50 lines)
├── llm_validation/
│   ├── strategy.py                (240 lines)
│   ├── decision_engine.py         (79 lines)
│   ├── json_utils.py              (46 lines)
│   └── models.py                  (35 lines)
└── types.py                        (50 lines)

waivern-community/
└── analysers/
    ├── personal_data_analyser/       (imports from shared)
    ├── data_subject_analyser/        (imports from shared)
    └── processing_purpose_analyser/  (imports from shared)
```

### Dependency Graph

```
waivern-core
    ↓
waivern-llm, waivern-rulesets
    ↓
waivern-analysers-shared (NEW)
    ↓
waivern-community (updated)
    ↓
wct
```

---

## Code Analysis

### Shared Dependencies Across Analysers

All three current analysers (PersonalData, DataSubject, ProcessingPurpose) share:

**1. Utilities** (278 total lines):
- `EvidenceExtractor` (181L) - Evidence snippet extraction with context windows
- `LLMServiceManager` (40L) - LLM service lifecycle management
- `RulesetManager` (50L) - Ruleset loading with caching

**2. LLM Validation Framework** (469 total lines):
- `LLMValidationStrategy[T]` (240L) - Abstract base class for validation
- `ValidationDecisionEngine` (79L) - Decision logic for keeping/rejecting findings
- `extract_json_from_llm_response` (46L) - JSON extraction utility
- `LLMValidationResultModel` (35L) - Validation result types

**3. Configuration Types** (50 lines):
- `PatternMatchingConfig` - Pattern matching configuration
- `LLMValidationConfig` - LLM validation configuration

---

## Implementation Plan

### Phase 1: Create waivern-analysers-shared Package

**Status:** ✅ COMPLETED

#### 1.1 Create Package Structure

```bash
mkdir -p libs/waivern-analysers-shared/src/waivern_analysers_shared/{utilities,llm_validation}
mkdir -p libs/waivern-analysers-shared/tests/waivern_analysers_shared/{utilities,llm_validation}
mkdir -p libs/waivern-analysers-shared/scripts

# CRITICAL: Create py.typed marker INSIDE the package directory (not at package root!)
# Location: libs/waivern-analysers-shared/src/waivern_analysers_shared/py.typed
touch libs/waivern-analysers-shared/src/waivern_analysers_shared/py.typed
```

**IMPORTANT - py.typed location:**
- ✅ CORRECT: `libs/waivern-analysers-shared/src/waivern_analysers_shared/py.typed` (inside package)
- ❌ WRONG: `libs/waivern-analysers-shared/py.typed` (at package root)

The `py.typed` file MUST be inside `src/waivern_analysers_shared/` directory. Without it in the correct location, importing packages will show "Stub file not found" errors from type checkers.

#### 1.2 Copy and Update Package Scripts

Copy script templates from waivern-core (uses comprehensive type checking):

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-analysers-shared/scripts/
chmod +x libs/waivern-analysers-shared/scripts/*.sh
```

**Update package-specific comments in scripts:**

The waivern-core scripts already check everything (`.`) for comprehensive type checking. Only update the comment header in `type-check.sh`:

```bash
# Change this:
# Run static type checking for waivern-core package

# To this:
# Run static type checking for waivern-analysers-shared package
```

**All three scripts:**
- **`lint.sh`**: ✅ Ready to use (may need comment update)
- **`format.sh`**: ✅ Ready to use (may need comment update)
- **`type-check.sh`**: ⚠️ Update package name in comment

**Rationale:** Copying from waivern-core ensures we get the comprehensive type checking pattern (`.`) that provides full coverage of the package, not just `src/ tests/`.

Each script:
- Changes to the package root directory (implicitly via uv run)
- Uses `uv run --group dev` to execute tools in the package's virtual environment
- Uses the package's own `pyproject.toml` configuration
- Expects standard `src/` and `tests/` directory structure

#### 1.3 Create pyproject.toml

```toml
[project]
name = "waivern-analysers-shared"
version = "0.1.0"
description = "Shared utilities for Waivern Compliance Framework analysers"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-llm",
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

# CRITICAL: Include py.typed marker for type checking support
include = [
    "src/waivern_analysers_shared/**/*.py",
    "src/waivern_analysers_shared/py.typed",
]

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_analysers_shared"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = ["ANN", "B", "D", "F", "I", "PL", "RUF100", "S", "UP"]
ignore = ["D203", "D213"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004"]
```

#### 1.4 Copy Shared Code

**Copy (not move)** from waivern-community:

```bash
# Utilities
cp -r libs/waivern-community/src/waivern_community/analysers/utilities/* \
      libs/waivern-analysers-shared/src/waivern_analysers_shared/utilities/

# LLM validation
cp -r libs/waivern-community/src/waivern_community/analysers/llm_validation/* \
      libs/waivern-analysers-shared/src/waivern_analysers_shared/llm_validation/

# Types
cp libs/waivern-community/src/waivern_community/analysers/types.py \
   libs/waivern-analysers-shared/src/waivern_analysers_shared/
```

#### 1.5 Create Package Exports

`src/waivern_analysers_shared/__init__.py`:
```python
"""Shared utilities for Waivern Compliance Framework analysers."""

from .llm_validation import (
    LLMValidationStrategy,
    ValidationDecisionEngine,
    LLMValidationResultModel,
    RecommendedActionType,
    ValidationResultType,
    extract_json_from_llm_response,
)
from .types import LLMValidationConfig, PatternMatchingConfig
from .utilities import EvidenceExtractor, LLMServiceManager, RulesetManager

__all__ = [
    # LLM Validation
    "LLMValidationStrategy",
    "ValidationDecisionEngine",
    "LLMValidationResultModel",
    "RecommendedActionType",
    "ValidationResultType",
    "extract_json_from_llm_response",
    # Configuration
    "LLMValidationConfig",
    "PatternMatchingConfig",
    # Utilities
    "EvidenceExtractor",
    "LLMServiceManager",
    "RulesetManager",
]
```

#### 1.6 Copy and Update Tests

Copy tests from waivern-community and update imports:

```bash
# Find and copy relevant tests
cp -r libs/waivern-community/tests/waivern_community/analysers/utilities/* \
      libs/waivern-analysers-shared/tests/waivern_analysers_shared/utilities/

cp -r libs/waivern-community/tests/waivern_community/analysers/llm_validation/* \
      libs/waivern-analysers-shared/tests/waivern_analysers_shared/llm_validation/
```

Update imports in tests:
```python
# Before
from waivern_community.analysers.utilities import EvidenceExtractor

# After
from waivern_analysers_shared.utilities import EvidenceExtractor
```

#### 1.7 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    "libs/waivern-llm",
    "libs/waivern-connectors-database",
    "libs/waivern-mysql",
    "libs/waivern-rulesets",
    "libs/waivern-analysers-shared",  # ADD THIS
    "libs/waivern-community",
    "apps/wct",
]

[tool.uv.sources]
waivern-core = { workspace = true }
waivern-llm = { workspace = true }
waivern-connectors-database = { workspace = true }
waivern-mysql = { workspace = true }
waivern-rulesets = { workspace = true }
waivern-analysers-shared = { workspace = true }  # ADD THIS
waivern-community = { workspace = true }
waivern-compliance-tool = { workspace = true }
```

#### 1.8 Initial Package Installation

```bash
uv sync --package waivern-analysers-shared
uv run python -c "import waivern_analysers_shared; print('✓ Package installed')"
```

#### 1.9 Run Package Tests

```bash
cd libs/waivern-analysers-shared
uv run pytest tests/ -v
```

#### 1.10 Update Root Workspace Scripts

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add after waivern-rulesets (in dependency order)
(cd libs/waivern-analysers-shared && ./scripts/lint.sh "$@")
```

#### 1.11 Update Pre-commit Wrapper Scripts

Update `scripts/pre-commit-lint.sh`, `scripts/pre-commit-format.sh`, `scripts/pre-commit-type-check.sh`:

```bash
# Add file grouping array
analysers_shared_files=()

# Add pattern matching in the loop
elif [[ "$file" == libs/waivern-analysers-shared/* ]]; then
    analysers_shared_files+=("${file#libs/waivern-analysers-shared/}")

# Add processing block (in dependency order, after rulesets)
if [ ${#analysers_shared_files[@]} -gt 0 ]; then
    (cd libs/waivern-analysers-shared && ./scripts/lint.sh "${analysers_shared_files[@]}")
fi
```

#### 1.12 Run Dev-Checks and Fix Linting Errors

```bash
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-shared.txt
```

Fix any linting errors following the pattern from previous extractions.

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
    "waivern-analysers-shared",  # ADD
    "pyyaml>=6.0.2",
    "pydantic>=2.11.5",
    "typing-extensions>=4.14.0",
]
```

#### 2.2 Update Component Imports

Update DataSubjectAnalyser, ProcessingPurposeAnalyser, and PersonalDataAnalyser to use shared utilities:

```python
# Before
from waivern_community.analysers.utilities import LLMServiceManager
from waivern_community.analysers.types import PatternMatchingConfig

# After
from waivern_analysers_shared import (
    LLMServiceManager,
    PatternMatchingConfig,
    LLMValidationConfig,
    EvidenceExtractor,
    RulesetManager,
)
```

**Files to update:**
- `libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/analyser.py`
- `libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/pattern_matcher.py`
- `libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/types.py`
- `libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/analyser.py`
- `libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/pattern_matcher.py`
- `libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/types.py`
- `libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/llm_validation_strategy.py`
- `libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/analyser.py`
- `libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/pattern_matcher.py`
- `libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/types.py`
- `libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/llm_validation_strategy.py`

**Also update test files:**
- `libs/waivern-community/tests/waivern_community/analysers/personal_data_analyser/test_analyser.py`
- `libs/waivern-community/tests/waivern_community/analysers/personal_data_analyser/test_llm_validation_strategy.py`

**Update patch paths in waivern-analysers-shared tests:**
- `libs/waivern-analysers-shared/tests/waivern_analysers_shared/utilities/test_llm_service_manager.py`
- `libs/waivern-analysers-shared/tests/waivern_analysers_shared/utilities/test_ruleset_manager.py`

Replace `waivern_community.analysers.utilities.` with `waivern_analysers_shared.utilities.` in `@patch` decorators.

#### 2.3 Delete Extracted Code

Delete shared utilities (moved to waivern-analysers-shared):

```bash
# Delete shared utilities (moved to waivern-analysers-shared)
rm -rf libs/waivern-community/src/waivern_community/analysers/utilities
rm -rf libs/waivern-community/src/waivern_community/analysers/llm_validation
rm libs/waivern-community/src/waivern_community/analysers/types.py

# Delete related tests (moved to waivern-analysers-shared)
rm -rf libs/waivern-community/tests/waivern_community/analysers/utilities
rm -rf libs/waivern-community/tests/waivern_community/analysers/llm_validation
```

**After this step:**
- ✅ DataSubjectAnalyser: using waivern_analysers_shared
- ✅ ProcessingPurposeAnalyser: using waivern_analysers_shared
- ✅ PersonalDataAnalyser: using waivern_analysers_shared (remains in community)

#### 2.4 Run Quality Checks and Fix Errors

**CRITICAL:** After deleting old files and updating imports, verify everything still works.

```bash
# Run all tests
cd libs/waivern-community
uv run pytest tests/ -v

# Run full dev-checks
cd /Users/lwkz/Workspace/waivern-compliance
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-phase2.txt
```

**Expected results:**
- All community tests pass
- All analysers-shared tests pass (57 tests)
- Type checking passes (0 errors)
- Linting passes

---

## Results

### Completion Summary

**Date Completed:** 2025-10-23
**Pull Request:** #161
**Commit:** 6e339e0

### Test Results

- ✅ All 752 tests passing
- ✅ Type checking: 0 errors (strict mode)
- ✅ Linting: all checks passed

### Created Package

- ✅ `libs/waivern-analysers-shared/` with 57 tests
- ✅ py.typed marker for type checking support
- ✅ All three analysers updated to use shared package
- ✅ Foundation established for future analyser extractions

---

## Next Steps

See `.development/personal-data-analyser-extraction-plan.md` for extracting PersonalDataAnalyser as standalone package.

**Prerequisite:** This plan (analysers-shared) must be completed first.
