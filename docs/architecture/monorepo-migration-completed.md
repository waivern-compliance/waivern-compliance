# Waivern Compliance Framework - Monorepo Migration Completed Phases

**Status:** ✅ Complete through Phase 3 (Core Migration Complete)
**Total Time:** 19-24 hours
**Last Updated:** 2025-10-16

This document records the completed phases of the monorepo migration. The core migration (Phases 0-3) is complete. See [monorepo-migration-plan.md](./monorepo-migration-plan.md) for optional remaining phases.

---

## Pre-Phase 1: Architectural Cleanup (COMPLETED)

**Goal:** Prepare codebase for monorepo migration by ensuring clean package independence
**Duration:** 3-4 hours
**Status:** ✅ Complete
**Risk:** Low (all tests passing, zero breaking changes)

### What Was Done

**Background:** Before implementing the full monorepo structure, we needed to ensure the codebase had proper architectural separation between framework and application layers. This work focused on package independence and removing WCT-specific dependencies from framework-level code.

### Completed Work

**1. Made JsonSchemaLoader Configurable (Commit 68079ba)**
- **Problem:** `JsonSchemaLoader` was hardcoded to WCT-specific paths, making it impossible to reuse in other applications
- **Solution:** Added configurable search paths via `__init__(search_paths: list[Path] | None = None)`
- **Impact:** Framework-level loader can now be used by any application with custom schema locations
- **Files Changed:**
  - `libs/waivern-core/src/waivern_core/schemas/base.py`
- **Tests:** All 737 tests pass

**2. Moved BaseFindingSchema to WCT Layer (Commit cac9df8)**
- **Problem:** `BaseFindingSchema` was in waivern-core but is a WCT-specific concept (compliance "findings")
- **Solution:** Moved to `src/wct/schemas/base.py` where it belongs as an application-level abstraction
- **Impact:** Framework no longer has application-specific schema concepts
- **Files Changed:**
  - Created: `src/wct/schemas/base.py` with `BaseFindingSchema`
  - Updated: All WCT schema imports to use new location
- **Tests:** All 737 tests pass

**3. Moved Analyser + Errors to waivern-core (Commit 1de9b1e)**
- **Problem:** Base `Analyser` class was in WCT but needed to be framework-level for reusability
- **Solution:** Moved `Analyser`, `AnalyserError`, `AnalyserInputError`, `AnalyserProcessingError` to waivern-core
- **Key Design Decision:** Framework method `update_analyses_chain()` returns `list[dict[str, Any]]` (untyped) whilst WCT converts to `AnalysisChainEntry` (typed Pydantic models) - this maintains framework independence
- **Files Changed:**
  - Created: `libs/waivern-core/src/waivern_core/base_analyser.py`
  - Deleted: `src/wct/analysers/base.py` (re-export file removed per user request)
  - Updated: All imports to use `from waivern_core import Analyser` directly
- **Tests:** All 737 tests pass

**4. Removed Orphaned BaseFindingSchema (Commit bc3864e)**
- **Problem:** After Phase 2, the original `BaseFindingSchema` was accidentally left in waivern-core
- **Solution:** Deleted the orphaned class and removed from exports
- **Impact:** Clean separation - `BaseFindingSchema` only exists in WCT layer where it belongs
- **Files Changed:**
  - `libs/waivern-core/src/waivern_core/schemas/base.py` (deleted lines 212-239)
  - `libs/waivern-core/src/waivern_core/schemas/__init__.py` (removed from exports)
- **Tests:** All 737 tests pass

### Current State After Pre-Phase 1

**✅ Completed:**
- `libs/waivern-core/` package exists with proper architectural boundaries
- Framework classes properly separated from application classes
- Zero WCT-specific dependencies in waivern-core
- All 737 tests passing
- All type checking passing (basedpyright strict)
- All linting passing (ruff)

### Key Learnings

1. **Framework Independence Pattern Works:** The dict-to-typed-object pattern (framework returns dicts, application converts to Pydantic models) successfully maintains clean separation
2. **Re-export Elimination:** User specifically requested no re-export layers - all imports should be direct from source package
3. **Test Coverage Excellent:** 737 passing tests caught all issues during refactoring
4. **Zero Breaking Changes:** All architectural work completed with no external API changes

---

## Phase 0: Pre-work (COMPLETED)

**Goal:** Ensure clean starting point
**Duration:** 1 hour
**Prerequisites:** Feature 9 complete, all tests passing
**Status:** ✅ Complete

### Tasks

1. ✅ Merge all pending PRs (Features 1-9)
2. ✅ Run full test suite: `uv run pytest` (all pass)
3. ✅ Run integration tests: `uv run pytest -m integration` (all pass)
4. ✅ Run dev checks: `./scripts/dev-checks.sh` (all pass)
5. ✅ Create migration branch: `git checkout -b refactor/monorepo-migration`
6. ✅ Document current import structure

---

## Phase 1: Workspace Setup + waivern-core (COMPLETED)

**Goal:** Create `uv` workspace structure and formalise waivern-core package
**Duration:** 2-3 hours
**Risk:** Low (no behaviour change)
**Status:** ✅ Complete

### 1.1: Create Workspace Structure

**Actions:**

1. Created directory structure:
   ```bash
   mkdir -p libs/waivern-core/src/waivern_core
   mkdir -p libs/waivern-core/tests/waivern_core
   mkdir -p apps/wct/src/wct
   mkdir -p apps/wct/tests
   ```

2. Updated root `pyproject.toml` with workspace configuration:
   ```toml
   [tool.uv.workspace]
   members = [
       "libs/waivern-core",
       "apps/wct",
   ]
   ```

3. Created `libs/waivern-core/pyproject.toml` and `apps/wct/pyproject.toml` with proper metadata

### 1.2: Verification

All verification checks passed:
- ✅ Workspace packages installed: `uv sync`
- ✅ All tests pass: `uv run pytest` (737 tests)
- ✅ Type checking passes: basedpyright strict mode
- ✅ Linting passes: ruff

### 1.3: Commit Phase 1

**Commit:** `714a137` - refactor: complete Phase 1 monorepo migration to UV workspace

---

## Phase 1.6: Package-Centric Quality Checks Architecture (COMPLETED)

**Goal:** Implement package-centric quality checks following monorepo best practices
**Duration:** 4-5 hours
**Status:** ✅ Complete
**Commit:** `7d05ee7`

After the workspace structure was created, we implemented a proper package-centric quality checks architecture following industry best practices (LangChain, boto3, airflow, pallets pattern).

### Problems Solved

1. Inconsistency between dev-checks and pre-commit behaviour
2. Workspace-level tool configs coupling packages together
3. Inability to check packages independently
4. Mixed workspace/package concerns

### Implementation

**1. Package Ownership**
- Moved all tool configs (basedpyright, ruff) from root to package `pyproject.toml` files
- Added dev dependency groups to both packages (`basedpyright>=1.29.2`, `ruff>=0.11.12`)
- Removed F401 blanket ignore for `__init__.py` (now requires explicit patterns)

**2. Package Scripts**
- Created `apps/wct/scripts/` directory with `lint.sh`, `format.sh`, `type-check.sh`
- Created `libs/waivern-core/scripts/` directory with `lint.sh`, `format.sh`, `type-check.sh`
- Scripts run from package directory using package's own configuration
- Type checking targets `src/` directory by default (excludes tests)

**3. Root Orchestration**
- Updated root scripts to call package scripts in sequence
- Created pre-commit wrappers that group files by package: `scripts/pre-commit-{lint,format,type-check}.sh`
- Updated `.pre-commit-config.yaml` to use package-aware wrappers
- Fixed `dev-checks.sh` to use orchestration script instead of direct ruff call
- Fixed `init.sh` to include `--all-packages` flag

### Benefits

- ✅ Package independence - each package can be checked in isolation
- ✅ Consistent behaviour - dev-checks and pre-commit use same configs
- ✅ Standard pattern - follows monorepo best practices
- ✅ Clean separation - workspace doesn't know package internals

### Usage

```bash
# Workspace-level (checks all packages)
./scripts/lint.sh
./scripts/format.sh
./scripts/type-check.sh
./scripts/dev-checks.sh  # All checks + tests

# Package-level (check individual packages)
cd apps/wct && ./scripts/lint.sh
cd libs/waivern-core && ./scripts/type-check.sh
```

### Test Results

- ✅ 737 tests passing
- ✅ Type checking: 0 errors (src/ only)
- ✅ Linting: All checks passed
- ✅ Formatting: 173 files checked
- ✅ All pre-commit hooks passing

### Commit Message

```
refactor: implement package-centric quality checks architecture

Restructure quality tooling to follow monorepo best practices where each
package owns its complete tool configuration and can be checked independently.

**Package Ownership:**
- Move basedpyright and ruff configs from root to package pyproject.toml files
- Add dev dependency groups (basedpyright, ruff) to both packages
- Remove F401 blanket ignore for __init__.py (use explicit patterns instead)

**Package Scripts:**
- Create scripts/ directory in each package with lint.sh, format.sh, type-check.sh
- Scripts run from package directory using package's own configuration
- Type checking targets src/ directory by default (excludes tests)

**Orchestration:**
- Update root scripts to call package scripts in sequence
- Create pre-commit wrappers that group files by package and run appropriate checks
- Update .pre-commit-config.yaml to use package-aware wrappers

**Fixes:**
- Fix dev-checks.sh to use orchestration script instead of direct ruff call
- Fix init.sh to include --all-packages flag in sync command
- Fix RulesetError import in wct/rulesets/__init__.py

This enables independent package checking whilst maintaining workspace-level
orchestration for convenience. Resolves inconsistency between dev-checks and
pre-commit behaviour.
```

---

## Phase 2: Extract waivern-llm (COMPLETED)

**Goal:** Move LLM service to standalone package with multi-provider support
**Duration:** 2-3 hours
**Risk:** Low (comprehensive test coverage)
**Status:** ✅ Complete
**Commits:** `d5f9124`, `d0d2a2d`

After the workspace structure and quality checks were established, we extracted the LLM service abstraction into a standalone package following the LangChain pattern (`langchain-core`, `langchain-anthropic`, `langchain-openai`, `langchain-google-genai`).

### Problems Solved

1. LLM service was tightly coupled to WCT application
2. Monolithic 534-line file mixing multiple providers
3. Tests in WCT package instead of library package
4. Configuration files scattered across workspace root

### Implementation

**1. Package Creation (Commit d5f9124)**

Created `libs/waivern-llm/` package with focused module structure:

```
libs/waivern-llm/src/waivern_llm/
├── __init__.py          # Public API exports
├── errors.py            # LLM exceptions (LLMServiceError, LLMConfigurationError, LLMConnectionError)
├── base.py              # BaseLLMService ABC
├── anthropic.py         # AnthropicLLMService
├── openai.py            # OpenAILLMService (lazy import)
├── google.py            # GoogleLLMService (lazy import)
└── factory.py           # LLMServiceFactory
```

**Key design decisions:**
- **Lazy imports** for optional providers (OpenAI, Google) - only imports if package installed
- **Dependency groups** in pyproject.toml: `openai`, `google`, `all` for flexible installation
- **Anthropic default** included by default (required dependency)
- **Zero WCT dependencies** - pure framework library

**2. Module Split**

Split monolithic `llm_service.py` (534 lines) into 6 focused modules:
- `errors.py` (17 lines) - Exception hierarchy
- `base.py` (38 lines) - Abstract base class
- `anthropic.py` (79 lines) - Anthropic provider
- `openai.py` (75 lines) - OpenAI provider with lazy import
- `google.py` (75 lines) - Google provider with lazy import
- `factory.py` (87 lines) - Provider factory with environment detection

**3. Test Migration**

Moved 93 tests from `apps/wct/tests/llm_service/` to `libs/waivern-llm/tests/waivern_llm/`:
- `test_anthropic_service.py` - Anthropic provider unit tests
- `test_openai_service.py` - OpenAI provider unit tests
- `test_google_service.py` - Google provider unit tests
- `test_factory.py` - Factory and provider selection tests
- `test_integration.py` - 12 integration tests with real APIs (marked with `@pytest.mark.integration`)

**Fixed test issues:**
- Updated mock patch paths from `wct.llm_service.ChatAnthropic` to `waivern_llm.anthropic.ChatAnthropic`
- Added `# type: ignore[reportUnusedImport]` for optional dependency checks
- All 749 tests passing (including 12 real API integration tests)

**4. Import Updates**

Updated all imports across codebase:
```python
# Before
from wct.llm_service import BaseLLMService, LLMServiceFactory

# After
from waivern_llm import BaseLLMService, LLMServiceFactory
```

**Files updated:**
- `apps/wct/src/wct/analysers/utilities/llm_service_manager.py`
- `apps/wct/src/wct/analysers/personal_data_analyser/llm_validation_strategy.py`
- `apps/wct/src/wct/analysers/processing_purpose_analyser/llm_validation_strategy.py`
- `apps/wct/src/wct/analysers/llm_validation/strategy.py`

**5. Workspace Configuration**

Updated workspace structure:
```toml
# Root pyproject.toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    "libs/waivern-llm",    # Added
    "apps/wct",
]

# apps/wct/pyproject.toml
dependencies = [
    "waivern-core",
    "waivern-llm",         # Added
    ...
]
```

**6. Pre-commit Integration**

Updated all three pre-commit wrapper scripts to process waivern-llm files:
- `scripts/pre-commit-format.sh`
- `scripts/pre-commit-lint.sh`
- `scripts/pre-commit-type-check.sh`

**7. Type Safety**

Added `py.typed` marker file to indicate inline type annotations are available.

### Configuration Architecture Refactor (Commit d0d2a2d)

During Phase 2, we also refactored the configuration management to follow 12-factor app principles:

**1. Environment Configuration Move**

Moved `.env` files from workspace root to application directory:
```
Before: .env.example, .env (workspace root)
After:  apps/wct/.env.example, apps/wct/.env
```

**Rationale:**
- Applications own configuration, libraries read from environment
- Supports multiple apps in monorepo with different configurations
- Production uses system environment variables (no .env files)
- Libraries (waivern-core, waivern-llm) have NO .env files

**2. Configuration Layers**

Established clear precedence (highest to lowest):
1. System environment variables (production)
2. Application `.env` file (`apps/wct/.env` for local development)
3. Runbook properties (YAML configuration)
4. Code defaults (fallback values)

**3. Code Updates**

Updated `apps/wct/src/wct/__main__.py` to load from app directory:
```python
# Load environment variables from .env file in wct app directory
_wct_app_dir = Path(__file__).parent.parent.parent
load_dotenv(_wct_app_dir / ".env")
```

Updated `tests/conftest.py` to load from app directory for integration tests:
```python
# Load from WCT app's .env since that's where API keys live
env_file = Path(__file__).parent.parent / "apps" / "wct" / ".env"
if env_file.exists():
    load_dotenv(env_file)
```

**4. Documentation**

Created comprehensive `docs/configuration.md` (300+ lines) covering:
- Quick start guide
- Configuration architecture explanation
- Environment variables documentation
- Development vs production setup patterns
- Security best practices
- Package-specific configuration
- Troubleshooting guide

Updated `CLAUDE.md` with new configuration approach.

**5. VS Code Integration**

Updated `.vscode/settings.json` with correct paths after monorepo migration:
- Schema path: `./apps/wct/src/wct/schemas/json_schemas/runbook/1.0.0/runbook.json`
- Env file: `${workspaceFolder}/apps/wct/.env`

### Verification

All verification checks passed:
- ✅ Workspace sync: `uv sync`
- ✅ All unit tests: `uv run pytest` (749 tests passing)
- ✅ Integration tests: `uv run pytest -m integration` (12 real API tests passing)
- ✅ Type checking: basedpyright strict mode (0 errors)
- ✅ Linting: ruff (all checks passed)
- ✅ Formatting: ruff format (all files formatted)
- ✅ Dev checks: `./scripts/dev-checks.sh` (all passing)

### Commit Messages

**Commit d5f9124:**
```
refactor: extract waivern-llm as standalone package

Move multi-provider LLM service abstraction to separate package following
LangChain's proven monorepo pattern (langchain-core, langchain-anthropic,
langchain-openai, langchain-google-genai).

Changes:
- Create libs/waivern-llm/ package with focused module structure
- Split monolithic llm_service.py (534 lines) into 6 focused modules
- Move 93 tests from apps/wct/tests/llm_service/ to libs/waivern-llm/tests/
- Update all imports across codebase (wct.llm_service → waivern_llm)
- Add waivern-llm to workspace members and wct dependencies
- Update pre-commit hooks to process waivern-llm files
- Add py.typed marker for type safety

Key features:
- Lazy imports for optional providers (OpenAI, Google)
- Dependency groups: openai, google, all
- Anthropic included by default
- Zero WCT dependencies - pure framework library

Test results:
- 749 tests passing (including 12 integration tests with real APIs)
- Type checking: 0 errors (strict mode)
- Linting: all checks passed
```

**Commit d0d2a2d:**
```
refactor: move .env to app-specific location and update configuration architecture

BREAKING CHANGE: Environment configuration moved from workspace root to application directory

- Move .env.example and .env from root to apps/wct/ for app-specific configuration
- Update load_dotenv() in __main__.py to load from wct app directory
- Fix tests/conftest.py to load .env from apps/wct/ for integration tests
- Update .vscode/settings.json with correct schema and .env paths after monorepo migration
- Create comprehensive docs/configuration.md covering:
  - Configuration architecture and layering (12-factor app principles)
  - Development vs production setup patterns
  - Security best practices
  - Package-specific configuration documentation
  - Troubleshooting guide
- Update CLAUDE.md with new configuration approach and quick start guide

Configuration follows industry best practices:
1. System environment variables (production)
2. Application .env files (local development)
3. Runbook properties (YAML configuration)
4. Code defaults (fallback values)

Libraries (waivern-core, waivern-llm) have no .env files and read from environment,
allowing flexible deployment patterns and clear separation of concerns.

All 749 tests passing including 12 integration tests with real API calls.
```

### Current State After Phase 2

**✅ Completed:**
- UV workspace with 3 packages: waivern-core, waivern-llm, wct
- Multi-provider LLM abstraction with lazy imports
- App-specific configuration architecture (`.env` in apps/wct/)
- Comprehensive configuration documentation
- 749 tests passing (including 12 integration tests)
- All type checking passing (basedpyright strict)
- All linting passing (ruff)

**WCT Files Still Using waivern-llm (to be moved in Phase 3):**
- `llm_service_manager.py` - Will move to waivern-community with analysers
- `analysers/personal_data_analyser/llm_validation_strategy.py`
- `analysers/processing_purpose_analyser/llm_validation_strategy.py`
- `analysers/llm_validation/strategy.py`

### Key Learnings

1. **Lazy imports work well** for optional providers - users can install only what they need
2. **Configuration layering is powerful** - system env → app .env → runbook → defaults
3. **Integration test coverage is critical** - 12 real API tests caught environment loading issues
4. **Monorepo documentation needs structure** - created dedicated configuration guide
5. **VS Code integration matters** - schema paths must be updated after file moves

---

## Phase 3: Create waivern-community Package (COMPLETED)

**Goal:** Extract connectors, analysers, rulesets, and prompts to community package with clean schema architecture
**Duration:** 4-6 hours
**Risk:** Medium (major code movement, import updates across entire codebase)
**Status:** ✅ Complete
**Commits:** `75df22c`, `78b886d`, `9ae22dc`, `9d79217`

After completing the waivern-llm extraction, we extracted all built-in components (connectors, analysers, rulesets, prompts) into waivern-community following the "components own their data contracts" principle.

### Problems Solved

1. WCT application contained framework-level components
2. Circular import issues between schemas and components
3. No clear ownership of component-specific schemas
4. Test isolation issues with singleton registry pattern

### Implementation

**1. Package Creation (Commit 75df22c)**

Created `libs/waivern-community/` package with component-organised structure:

```
libs/waivern-community/src/waivern_community/
├── connectors/          # MySQL, SQLite, Filesystem, SourceCode
│   ├── mysql/
│   ├── sqlite/
│   ├── filesystem/
│   └── source_code/
│       └── schemas/     # SourceCodeSchema lives with connector
├── analysers/           # PersonalData, ProcessingPurpose, DataSubject
│   ├── personal_data_analyser/
│   │   └── schemas/     # PersonalDataFindingSchema with analyser
│   ├── processing_purpose_analyser/
│   │   └── schemas/     # ProcessingPurposeFindingSchema with analyser
│   ├── data_subject_analyser/
│   │   └── schemas/     # DataSubjectFindingSchema with analyser
│   ├── llm_validation/  # Shared LLM validation logic
│   └── utilities/       # Evidence extraction, ruleset management
├── rulesets/            # All YAML-based compliance rulesets
│   ├── personal_data.py
│   ├── processing_purposes.py
│   ├── data_collection.py
│   ├── service_integrations.py
│   └── data_subjects.py
└── prompts/             # LLM prompt templates
```

**2. Schema Reorganisation**

Implemented clean schema architecture following "components own their data contracts":

**Moved to waivern-core** (shared/standard schemas):
- `StandardInputSchema` - Universal format used by MySQL, SQLite, Filesystem connectors
- `BaseFindingSchema` - Base class for all finding schemas
- Base types and validation utilities

**Co-located with components** (waivern-community):
- `SourceCodeSchema` → `connectors/source_code/schemas/`
- `PersonalDataFindingSchema` → `analysers/personal_data_analyser/schemas/`
- `ProcessingPurposeFindingSchema` → `analysers/processing_purpose_analyser/schemas/`
- `DataSubjectFindingSchema` → `analysers/data_subject_analyser/schemas/`

**Kept in WCT** (application-specific):
- Runbook schemas (execution configuration)
- Analysis result schemas (output formatting)

**3. Component Migration**

Moved all built-in components from `apps/wct/src/wct/` to `libs/waivern-community/src/waivern_community/`:

| Component | Source | Destination |
|-----------|--------|-------------|
| MySQL Connector | `wct/connectors/mysql/` | `waivern_community/connectors/mysql/` |
| SQLite Connector | `wct/connectors/sqlite/` | `waivern_community/connectors/sqlite/` |
| Filesystem Connector | `wct/connectors/filesystem/` | `waivern_community/connectors/filesystem/` |
| SourceCode Connector | `wct/connectors/source_code/` | `waivern_community/connectors/source_code/` |
| PersonalData Analyser | `wct/analysers/personal_data_analyser/` | `waivern_community/analysers/personal_data_analyser/` |
| ProcessingPurpose Analyser | `wct/analysers/processing_purpose_analyser/` | `waivern_community/analysers/processing_purpose_analyser/` |
| DataSubject Analyser | `wct/analysers/data_subject_analyser/` | `waivern_community/analysers/data_subject_analyser/` |
| All Rulesets | `wct/rulesets/` | `waivern_community/rulesets/` |
| All Prompts | `wct/prompts/` | `waivern_community/prompts/` |

**4. Import Updates**

Updated all imports across codebase:
```python
# Before
from wct.connectors.mysql import MySQLConnector
from wct.analysers.personal_data_analyser import PersonalDataAnalyser
from wct.schemas import PersonalDataFindingSchema

# After
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.analysers.personal_data_analyser import PersonalDataAnalyser
from waivern_community.analysers.personal_data_analyser.schemas import PersonalDataFindingSchema
```

**5. Test Migration**

Moved and updated component tests:
- Updated mock/patch paths from `wct.*` to `waivern_community.*`
- Fixed filesystem paths in test runbooks after reorganisation
- Updated vendor database test paths for new structure
- All 737 tests passing after migration

**6. Workspace Configuration**

Updated workspace structure:
```toml
# Root pyproject.toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    "libs/waivern-llm",
    "libs/waivern-community",    # Added
    "apps/wct",
]

# apps/wct/pyproject.toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-community",         # Added
    ...
]
```

**7. Pre-commit Integration**

Updated pre-commit configuration to exclude waivern-community tests from type-check hook to improve performance.

### Post-Phase 3 Refinements

**Test Design Improvements (Commit 78b886d)**

After Phase 3, we decoupled tests from monorepo structure:
- Removed hardcoded workspace paths from tests
- Made tests location-independent
- Improved test isolation patterns

**WCT File Consolidation (Commit 9ae22dc)**

Consolidated WCT-specific files from workspace root to application directory:
- Moved `config/organisation.yaml` → `apps/wct/config/`
- Moved `runbooks/` → `apps/wct/runbooks/`
- Moved `tests/` → `apps/wct/tests/`
- Moved `runbook.schema.json` → `apps/wct/`

**Test Isolation Fix (Commit 9ae22dc)**

Implemented proper test isolation for singleton registry:
- Created `isolated_registry` fixture in `libs/waivern-community/tests/conftest.py`
- Fixture captures and restores registry state automatically
- Updated all ruleset tests to use fixture
- Resolved test pollution issues caused by execution order changes

**Unused Code Cleanup (Commit 9d79217)**

Removed genuinely unused files:
- Deleted empty `waivern_community/schemas/` namespace
- Removed empty test `__init__.py` files
- Modern pytest discovers tests without these markers

### Verification

All verification checks passed:
- ✅ Workspace sync: `uv sync`
- ✅ All tests: `uv run pytest` (738 tests passing)
- ✅ Type checking: basedpyright strict mode (0 errors)
- ✅ Linting: ruff (all checks passed)
- ✅ Formatting: ruff format (all files formatted)
- ✅ Dev checks: `./scripts/dev-checks.sh` (all passing)

### Commit Messages

**Commit 75df22c:**
```
feat: extract waivern-community package with schema reorganisation

Extract connectors, analysers, rulesets, and prompts into waivern-community
package following "components own their data contracts" principle.

Schema reorganisation:
- Move StandardInputSchema and shared types to waivern-core
- Add BaseFindingSchema to waivern-core for finding schemas
- Co-locate component schemas with their components:
  * PersonalDataFindingSchema with personal_data_analyser
  * ProcessingPurposeFindingSchema with processing_purpose_analyser
  * DataSubjectFindingSchema with data_subject_analyser
  * SourceCodeSchema with source_code connector
- Remove re-export layers to eliminate circular imports

Test updates:
- Update mock/patch paths from wct.* to waivern_community.*
- Update runbook filesystem paths after test migration
- Fix vendor database test paths for new structure

Pre-commit configuration:
- Add waivern-community and waivern-llm test exclusions to type-check hook

All 737 tests passing.
```

**Commit 9ae22dc:**
```
refactor: consolidate WCT files and fix ruleset registry test isolation

Move WCT-specific files from workspace root to apps/wct/ directory.
Implement isolated_registry fixture to fix test pollution.

All 738 tests passing.
```

**Commit 9d79217:**
```
refactor: remove unused namespace and empty test files

Remove genuinely unused files that provide no functional value.

All 738 tests passing, all quality checks passing.
```

### Current State After Phase 3

**✅ Completed:**
- UV workspace with 4 packages: waivern-core, waivern-llm, waivern-community, wct
- Clean schema architecture with component ownership
- All built-in components in dedicated community package
- Proper test isolation with fixture-based registry management
- WCT application contains only application-specific code
- 738 tests passing, all quality checks passing
- All type checking passing (basedpyright strict)
- All linting passing (ruff)

**Package Structure:**
```
waivern-core         → Base abstractions (schema, message, analyser, connector)
waivern-llm          → Multi-provider LLM service (Anthropic, OpenAI, Google)
waivern-community    → All built-in components (connectors, analysers, rulesets)
wct                  → CLI application (executor, runbook, analysis output)
```

### Key Learnings

1. **Schema ownership matters** - Co-locating schemas with components eliminated circular imports
2. **Component independence** - Each package can now be versioned and released independently
3. **Test isolation critical** - Singleton patterns require careful fixture management
4. **Monorepo structure enables flexibility** - Can extract individual packages later if needed
5. **Documentation during migration** - Keeping track of changes prevents confusion

---

## Summary

**Completed Phases:** Pre-Phase 1, Phase 0, Phase 1, Phase 1.6, Phase 2, Phase 3
**Total Time:** 19-24 hours
**Test Status:** 738 tests passing, all quality checks passing
**Breaking Changes:**
- Environment configuration location changed (Phase 2)
- Import paths changed (Phase 3)
- All documented in migration guide

**Key Achievements:**
- ✅ Clean architectural separation between framework and application
- ✅ Formal UV workspace with 4 packages (waivern-core, waivern-llm, waivern-community, wct)
- ✅ Package-centric quality checks architecture
- ✅ Multi-provider LLM abstraction with lazy imports
- ✅ All built-in components in dedicated community package
- ✅ Component-owned schema architecture
- ✅ App-specific configuration following 12-factor principles
- ✅ Independent package development capability
- ✅ Comprehensive documentation
- ✅ Proper test isolation patterns

**Remaining Optional Work:** See [monorepo-migration-plan.md](./monorepo-migration-plan.md) for optional phases (individual packages, dynamic plugin loading, contribution infrastructure).
