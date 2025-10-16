# Waivern Compliance Framework - Monorepo Migration Plan

**Status:** ✅ Core Migration Complete (Phases 0-3) - Optional Phases Remaining
**Created:** 2025-10-14
**Updated:** 2025-10-16

## Quick Status

| Phase | Status | Effort |
|-------|--------|--------|
| Pre-Phase 1: Architectural Cleanup | ✅ Complete | 3-4 hours |
| Phase 0: Pre-work | ✅ Complete | 1 hour |
| Phase 1: Workspace + Quality Checks | ✅ Complete | 6-8 hours |
| Phase 2: Extract waivern-llm | ✅ Complete | 2-3 hours |
| Phase 3: Create waivern-community | ✅ Complete | 4-6 hours |
| Phase 4: Individual packages (optional) | 🔵 Optional | 1-2 hours each |
| Phase 5: Dynamic plugin loading (optional) | 🔵 Optional | 3-4 hours |
| Phase 6: Contribution infrastructure (optional) | 🔵 Optional | 2-3 hours |

**Core Migration Completed:** 19-24 hours | **Optional Remaining:** 6-9 hours

---

## Vision

Transform single package into multi-package framework:

```
waivern-core         → Base abstractions (BaseConnector, Analyser, Message, Schema)
waivern-llm          → Multi-provider LLM service (Anthropic, OpenAI, Google)
waivern-community    → All built-in connectors/analysers/rulesets
waivern-*            → Individual packages (optional, e.g., waivern-mysql)
wct                  → CLI tool application
```

**Inspired by:** LangChain's proven monorepo pattern (`langchain-core`, `langchain-community`, `langchain-openai`, `langchain`)

---

## Completed Work

See **[monorepo-migration-completed.md](./monorepo-migration-completed.md)** for full details.

**Summary of completed phases:**
- ✅ UV workspace with 4 packages (waivern-core, waivern-llm, waivern-community, wct)
- ✅ Package-centric quality checks architecture
- ✅ Framework independence (waivern-core and waivern-llm have zero WCT dependencies)
- ✅ Multi-provider LLM abstraction with lazy imports (Anthropic, OpenAI, Google)
- ✅ All built-in components extracted to waivern-community package
- ✅ Component-owned schema architecture following "components own their data contracts"
- ✅ App-specific configuration architecture (`.env` in apps/wct/)
- ✅ Proper test isolation with fixture-based registry management
- ✅ 738 tests passing, all quality checks passing

---

## Phase 2: Extract waivern-llm (COMPLETE)

**Goal:** Move LLM service to standalone package

**Completed:**
- ✅ Created `libs/waivern-llm/` package with focused module structure
- ✅ Split monolithic `llm_service.py` (534 lines) into 6 focused modules
- ✅ Moved 93 tests from `apps/wct/tests/llm_service/` to `libs/waivern-llm/tests/`
- ✅ Updated all imports across codebase (`wct.llm_service` → `waivern_llm`)
- ✅ Configured workspace and added waivern-llm dependency to wct
- ✅ Updated pre-commit hooks for waivern-llm package
- ✅ Moved `.env` to app-specific location (`apps/wct/.env`)
- ✅ Created comprehensive configuration documentation
- ✅ All 749 tests passing (including 12 integration tests with real APIs)

**Additional work completed:**
- **Configuration architecture refactor:** Moved environment configuration from workspace root to application directory following 12-factor app principles
- **Documentation:** Created `docs/configuration.md` with comprehensive configuration guide
- **VS Code integration:** Updated `.vscode/settings.json` with correct schema and .env paths

**Tasks (Reference):**

### 2.1: Create Package Structure

```bash
mkdir -p libs/waivern-llm/src/waivern_llm
mkdir -p libs/waivern-llm/tests
mkdir -p libs/waivern-llm/scripts
```

### 2.2: Create pyproject.toml

```toml
[project]
name = "waivern-llm"
version = "0.1.0"
description = "Multi-provider LLM abstraction for Waivern Compliance Framework"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",
]

[dependency-groups]
dev = [
    "basedpyright>=1.29.2",
    "ruff>=0.11.12",
]
openai = ["langchain-openai>=0.2.0"]
google = ["langchain-google-genai>=2.0.0"]
all = ["waivern-llm[openai,google]"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_llm"]

[tool.basedpyright]
include = ["src"]

[tool.ruff]
target-version = "py312"
src = ["src"]
```

### 2.3: Split llm_service.py into Modules

```
libs/waivern-llm/src/waivern_llm/
├── __init__.py          # Public exports
├── errors.py            # LLM exceptions
├── base.py              # BaseLLMService ABC
├── anthropic.py         # AnthropicLLMService
├── openai.py            # OpenAILLMService
├── google.py            # GoogleLLMService
└── factory.py           # LLMServiceFactory
```

### 2.4: Move Tests

```bash
# Move tests to waivern-llm package
mv apps/wct/tests/llm_service/* libs/waivern-llm/tests/waivern_llm/
```

Update test imports: `from wct.llm_service import ...` → `from waivern_llm import ...`

### 2.5: Update Imports Across Codebase

Find and update all imports:
```python
# Before
from wct.llm_service import BaseLLMService, LLMServiceFactory

# After
from waivern_llm import BaseLLMService, LLMServiceFactory
```

### 2.6: Create Package Scripts

Create `libs/waivern-llm/scripts/{lint.sh,format.sh,type-check.sh}` following the pattern from waivern-core.

### 2.7: Update Workspace Configuration

Add to root `pyproject.toml`:
```toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    "libs/waivern-llm",    # Add this
    "apps/wct",
]
```

Add to `apps/wct/pyproject.toml`:
```toml
dependencies = [
    "waivern-core",
    "waivern-llm",         # Add this
    ...
]
```

### 2.8: Update Pre-commit Wrappers

Update `scripts/pre-commit-{format,lint,type-check}.sh` to include waivern-llm package.

### 2.9: Verification

```bash
uv sync
uv run pytest libs/waivern-llm/tests/
uv run pytest apps/wct/tests/
uv run pytest -m integration  # LLM integration tests
./scripts/dev-checks.sh
```

### 2.10: Commit

```bash
git add -A
git commit -m "refactor: extract waivern-llm as standalone package

Move LLM service abstraction to separate waivern-llm package with
multi-provider support (Anthropic, OpenAI, Google).

Changes:
- Create libs/waivern-llm/ package
- Split llm_service.py into focused modules
- Move tests to waivern-llm package
- Update imports across codebase
- Add waivern-llm to workspace members

Test results:
- All unit tests pass
- All integration tests pass
- Type checking passes
- Linting passes

Breaking changes: None (import paths updated)"
```

---

## Phase 3: Create waivern-community + Schema Architecture (COMPLETE)

**Goal:** Move all built-in connectors/analysers/rulesets to community package and establish clean schema architecture
**Status:** ✅ Complete
**Commits:** `75df22c`, `78b886d`, `9ae22dc`, `9d79217`

See [monorepo-migration-completed.md](./monorepo-migration-completed.md#phase-3-create-waivern-community-package-completed) for full details.

**Completed:**
- ✅ Created `libs/waivern-community/` package with component-organised structure
- ✅ Implemented "components own their data contracts" schema architecture
- ✅ Moved all connectors, analysers, rulesets, and prompts to community package
- ✅ Co-located component-specific schemas with their components
- ✅ Updated all imports across codebase
- ✅ Migrated and updated all component tests
- ✅ Fixed test isolation issues with singleton registry
- ✅ Consolidated WCT files from workspace root to app directory
- ✅ All 738 tests passing, all quality checks passing

**Tasks (Reference):**

**Key Architectural Decision - Schema Ownership:**

Following the principle "components own their data contracts":

**waivern-core** (shared/standard schemas):
- `StandardInputSchema` - Universal format used by MySQL, SQLite, Filesystem connectors
- Base types and utilities (BaseFindingModel, validation utils)

**waivern-community** (component-specific schemas):
- `SourceCodeSchema` - Belongs with SourceCodeConnector (its only producer)
- `PersonalDataFindingSchema` - Belongs with PersonalDataAnalyser (its output contract)
- `ProcessingPurposeFindingSchema` - Belongs with ProcessingPurposeAnalyser
- `DataSubjectFindingSchema` - Belongs with DataSubjectAnalyser

**wct** (application-specific):
- Runbook schemas (ExecutionStep, AnalyserConfig, ConnectorConfig)
- Output formatting (AnalysisResult JSON serialization)

**Rationale:**
- **Shared formats → core**: StandardInputSchema is used by 3+ connectors
- **Component-specific → with component**: Each connector/analyser owns its unique data format
- **Self-contained components**: Import analyser, get its output schema automatically
- **Enables third-party packages**: Can depend on waivern-core for shared schemas only

**Tasks:**

### 3.1: Create Package Structure

```
libs/waivern-community/src/waivern_community/
├── connectors/      # mysql, sqlite, filesystem, source_code
│   └── source_code/
│       └── schemas/ # SourceCodeSchema lives here
├── analysers/       # personal_data, processing_purpose, data_subject
│   ├── personal_data_analyser/
│   │   └── schemas/ # PersonalDataFindingSchema lives here
│   └── processing_purpose_analyser/
│       └── schemas/ # ProcessingPurposeFindingSchema lives here
├── rulesets/        # All YAML rulesets
└── prompts/         # All prompt templates
```

### 3.2: Move Schemas to Correct Locations

**To waivern-core:**
```bash
# Move shared schemas
mv apps/wct/src/wct/schemas/standard_input.py libs/waivern-core/src/waivern_core/schemas/
mv apps/wct/src/wct/schemas/{base.py,types.py,validation.py} libs/waivern-core/src/waivern_core/schemas/
```

**To waivern-community:**
```bash
# SourceCodeSchema stays with its connector
# Finding schemas stay with their analysers
mv apps/wct/src/wct/schemas/personal_data_finding.py \
   libs/waivern-community/src/waivern_community/analysers/personal_data_analyser/schemas/

mv apps/wct/src/wct/schemas/processing_purpose_finding.py \
   libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/schemas/
```

### 3.3: Move Components

| Current | New |
|---------|-----|
| `apps/wct/src/wct/connectors/` | `libs/waivern-community/src/waivern_community/connectors/` |
| `apps/wct/src/wct/analysers/` | `libs/waivern-community/src/waivern_community/analysers/` |
| `apps/wct/src/wct/rulesets/` | `libs/waivern-community/src/waivern_community/rulesets/` |
| `apps/wct/src/wct/prompts/` | `libs/waivern-community/src/waivern_community/prompts/` |

### 3.4: Update Imports

```python
# Shared schema from waivern-core
from waivern_core.schemas import StandardInputSchema

# Component-specific schema from waivern-community
from waivern_community.connectors.source_code.schemas import SourceCodeSchema
from waivern_community.analysers.personal_data_analyser.schemas import PersonalDataFindingSchema

# Components from waivern-community
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.analysers.personal_data_analyser import PersonalDataAnalyser
```

### 3.5: Verification & Commit

```bash
uv sync
uv run pytest
./scripts/dev-checks.sh
```

---

## Phase 4: Individual Packages (Optional)

**When needed:**
- User wants minimal dependencies
- Component becomes popular standalone
- Third party wants to maintain separately

**Example:** Extract `waivern-mysql` from `waivern-community`

Keep community package as re-export for backward compatibility.

---

## Phase 5: Dynamic Plugin Loading

**Goal:** Implement plugin system in WCT executor

**Key features:**
- Load components from waivern-community (default)
- Load from standalone packages (`package:waivern-mysql`)
- Extensible for remote components (future)

**Runbook example:**
```yaml
connectors:
  - name: "db"
    type: "mysql"
    source: "community"  # Optional, default
    properties: {...}

  - name: "custom"
    type: "custom_db"
    source: "package:acme-custom-connector"
    properties: {...}
```

---

## Phase 6: Contribution Infrastructure

**Goal:** Documentation and tooling for third-party contributors

**Deliverables:**
- `docs/contributing/create-connector.md`
- `docs/contributing/create-analyser.md`
- `docs/examples/` with working templates
- `scripts/publish-packages.sh`
- Updated README with ecosystem overview

---

## Current Package Structure

```
waivern-compliance/
├── pyproject.toml                    # Workspace config
├── libs/
│   ├── waivern-core/                 # ✅ Complete (Phase 1)
│   ├── waivern-llm/                  # ✅ Complete (Phase 2)
│   └── waivern-community/            # ✅ Complete (Phase 3)
└── apps/
    └── wct/                          # ✅ Complete (CLI app)
        ├── .env                      # App-specific configuration
        ├── config/                   # App-specific config files
        ├── runbooks/                 # Runbook configurations
        └── tests/                    # Application tests
```

---

## Success Criteria

**Phase 2 complete when:**
- [x] waivern-llm package created with proper structure
- [x] LLM service split into focused modules
- [x] All tests moved and passing
- [x] All imports updated
- [x] All quality checks passing
- [x] Committed to git

**Core migration complete when:**
- [x] waivern-core package extracted (Phase 1)
- [x] waivern-llm package extracted (Phase 2)
- [x] waivern-community package created (Phase 3)
- [x] All tests passing (738 tests)
- [x] All quality checks passing
- [x] Documentation updated
- [x] Ready for publishing (when desired)

**✅ Core migration is complete!** Optional phases remain for enhanced functionality.

---

## Resources

- **LangChain monorepo:** https://github.com/langchain-ai/langchain
- **UV workspaces:** https://docs.astral.sh/uv/concepts/workspaces/
- **Completed phases:** [monorepo-migration-completed.md](./monorepo-migration-completed.md)
