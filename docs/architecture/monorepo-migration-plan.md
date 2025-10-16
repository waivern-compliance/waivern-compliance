# Waivern Compliance Framework - Monorepo Migration Plan

**Status:** Phase 1 Complete, Phase 2 In Progress
**Created:** 2025-10-14
**Updated:** 2025-10-16

## Quick Status

| Phase | Status | Effort |
|-------|--------|--------|
| Pre-Phase 1: Architectural Cleanup | ✅ Complete | 3-4 hours |
| Phase 0: Pre-work | ✅ Complete | 1 hour |
| Phase 1: Workspace + Quality Checks | ✅ Complete | 6-8 hours |
| **Phase 2: Extract waivern-llm** | **🔄 In Progress** | **2-3 hours** |
| Phase 3: Create waivern-community | Pending | 4-6 hours |
| Phase 4: Individual packages (optional) | Pending | 1-2 hours each |
| Phase 5: Dynamic plugin loading | Pending | 3-4 hours |
| Phase 6: Contribution infrastructure | Pending | 2-3 hours |

**Completed:** 11-13 hours | **Remaining:** 7-13 hours

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
- ✅ UV workspace with 2 packages (waivern-core, wct)
- ✅ Package-centric quality checks architecture
- ✅ Framework independence (waivern-core has zero WCT dependencies)
- ✅ 737 tests passing, all checks passing

---

## Phase 2: Extract waivern-llm (IN PROGRESS)

**Goal:** Move LLM service to standalone package

**Current state:**
- LLM service at `apps/wct/src/wct/llm_service.py` (534 lines)
- Tests at `apps/wct/tests/llm_service/`
- Supports Anthropic, OpenAI, Google providers

**Tasks:**

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

## Phase 3: Create waivern-community

**Goal:** Move all built-in connectors/analysers/rulesets to community package

**Tasks:**

### 3.1: Create Package

Similar structure to waivern-llm with:
```
libs/waivern-community/src/waivern_community/
├── connectors/      # mysql, sqlite, filesystem, source_code
├── analysers/       # personal_data, processing_purpose
├── rulesets/        # All YAML rulesets
└── prompts/         # All prompt templates
```

### 3.2: Move Components

| Current | New |
|---------|-----|
| `apps/wct/src/wct/connectors/` | `libs/waivern-community/src/waivern_community/connectors/` |
| `apps/wct/src/wct/analysers/` | `libs/waivern-community/src/waivern_community/analysers/` |
| `apps/wct/src/wct/rulesets/` | `libs/waivern-community/src/waivern_community/rulesets/` |
| `apps/wct/src/wct/prompts/` | `libs/waivern-community/src/waivern_community/prompts/` |

### 3.3: Update Imports

```python
# Before
from wct.connectors.mysql import MySQLConnector
from wct.analysers.personal_data_analyser import PersonalDataAnalyser

# After
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.analysers.personal_data import PersonalDataAnalyser
```

### 3.4: Verification & Commit

Same verification process as Phase 2.

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
│   ├── waivern-core/                 # ✅ Done
│   ├── waivern-llm/                  # 🔄 In Progress
│   └── waivern-community/            # Pending
└── apps/
    └── wct/                          # ✅ Done (partially)
```

---

## Success Criteria

**Phase 2 complete when:**
- [ ] waivern-llm package created with proper structure
- [ ] LLM service split into focused modules
- [ ] All tests moved and passing
- [ ] All imports updated
- [ ] All quality checks passing
- [ ] Committed to git

**Full migration complete when:**
- [ ] All packages in workspace
- [ ] All tests passing (737+)
- [ ] All quality checks passing
- [ ] Documentation updated
- [ ] Ready for publishing (when desired)

---

## Resources

- **LangChain monorepo:** https://github.com/langchain-ai/langchain
- **UV workspaces:** https://docs.astral.sh/uv/concepts/workspaces/
- **Completed phases:** [monorepo-migration-completed.md](./monorepo-migration-completed.md)
