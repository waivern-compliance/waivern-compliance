# Waivern Compliance Framework - Monorepo Migration Plan

**Status:** In Progress (Phase 1 Complete, Quality Checks Complete)
**Created:** 2025-10-14
**Updated:** 2025-10-15
**Target:** Transform single package into multi-package monorepo following LangChain pattern

## Table of Contents

1. [Current Status Summary](#current-status-summary)
2. [Vision & Goals](#vision--goals)
3. [Architecture Overview](#architecture-overview)
4. [Package Structure](#package-structure)
5. [Migration Phases](#migration-phases)
6. [Dynamic Plugin Loading](#dynamic-plugin-loading)
7. [Third-Party Contribution Model](#third-party-contribution-model)
8. [Remote Components](#remote-components)
9. [Testing Strategy](#testing-strategy)
10. [Implementation Checklists](#implementation-checklists)
11. [Code Examples](#code-examples)

---

## Current Status Summary

**Migration Progress:** Phase 1 Complete ✅ (includes workspace setup + quality checks architecture)

### What's Been Completed

**Completed:** Pre-Phase 1, Phase 0, Phase 1, Phase 1.6 (11-13 hours total)

See **[monorepo-migration-completed.md](./monorepo-migration-completed.md)** for full details of completed phases.

**Quick Summary:**
- ✅ **Pre-Phase 1:** Architectural cleanup - framework independence
- ✅ **Phase 0:** Pre-work - migration branch setup
- ✅ **Phase 1:** UV workspace structure with 2 packages (waivern-core, wct)
- ✅ **Phase 1.6:** Package-centric quality checks architecture

**Current State:**
- ✅ 737 tests passing
- ✅ UV workspace with 2 packages (waivern-core, wct)
- ✅ Package-centric quality checks architecture
- ✅ Independent package checking capability
- ✅ All pre-commit hooks passing
- ✅ Zero breaking changes to external APIs

### What's Next

**Subsequent Phases:**
- Phase 2: Extract waivern-llm
- Phase 3: Create waivern-community
- Phase 4: Individual packages (optional)
- Phase 5: Dynamic plugin loading
- Phase 6: Contribution infrastructure

**Total Remaining Effort:** ~7-13 hours

### Quick Reference

| Component | Current Location | Target Location | Status |
|-----------|-----------------|-----------------|--------|
| BaseConnector | libs/waivern-core/ | libs/waivern-core/ | ✅ Done |
| Analyser | libs/waivern-core/ | libs/waivern-core/ | ✅ Done |
| Message | libs/waivern-core/ | libs/waivern-core/ | ✅ Done |
| Schema | libs/waivern-core/ | libs/waivern-core/ | ✅ Done |
| BaseRuleset | src/wct/rulesets/ | libs/waivern-core/ | ⚠️ TODO |
| WCT Code | src/wct/ | apps/wct/ | ⚠️ TODO |
| LLM Service | src/wct/ | libs/waivern-llm/ | ⚠️ TODO |
| Connectors | src/wct/connectors/ | libs/waivern-community/ | ⚠️ TODO |
| Analysers | src/wct/analysers/ | libs/waivern-community/ | ⚠️ TODO |

---

## Vision & Goals

### The Waivern Compliance Framework Ecosystem

**Current state:** Single monolithic package (`waivern-compliance-tool`)

**Target state:** Multi-package framework where:
- **WCT** is just one CLI tool in the ecosystem
- **Core abstractions** define contracts for extensibility
- **Community package** provides batteries-included implementations
- **Individual packages** allow minimal dependency installation
- **Third-party contributors** can easily create connectors/analysers/rulesets
- **Remote components** enable platform-as-a-service model
- **Future tools** (web UI, API, SDK) can reuse core packages

### Key Goals

1. ✅ **Modularity** - Clear separation of concerns, reusable components
2. ✅ **Extensibility** - Easy for third parties to add connectors/analysers/rulesets
3. ✅ **Dynamic loading** - Runbooks specify components, executor loads them dynamically
4. ✅ **Minimal dependencies** - Users install only what they need
5. ✅ **Platform model** - Support for remote analysers/rulesets (future)
6. ✅ **Community growth** - Low barrier to contribution

---

## Architecture Overview

### Inspiration: LangChain Pattern

Following LangChain's proven monorepo structure:

- **`langchain-core`** → **`waivern-core`** - Base abstractions only
- **`langchain-community`** → **`waivern-community`** - All built-in implementations
- **`langchain-openai`** → **`waivern-mysql`** - Individual packages for specific integrations
- **`langchain` (CLI/chains)** → **`wct`** - Orchestration tool

### Three-Tier Package Strategy

```
┌─────────────────────────────────────────────────────────────┐
│ Tier 3: Individual Packages (Optional, Minimal Dependencies)│
│  waivern-mysql, waivern-postgres, waivern-personal-data     │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ Tier 2: Community Package (Batteries Included)              │
│  waivern-community (all connectors/analysers/rulesets)      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ Tier 1: Core Package (Base Abstractions Only)               │
│  waivern-core (BaseConnector, BaseAnalyser, BaseRuleset)    │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Graph

```
waivern-core (Pydantic, typing only)
    ↑
    ├── waivern-llm (depends on core)
    │       ↑
    ├── waivern-community (depends on core + llm)
    │       ↑
    ├── waivern-mysql (depends on core)
    ├── waivern-postgres (depends on core)
    ├── waivern-personal-data (depends on core + llm)
    │       ↑
    ├── wct (depends on core + community) [CLI tool]
    └── waivern-web (depends on core + community) [Future: Web UI]
```

---

## Package Structure

### Complete Directory Structure

```
waivern-compliance/                          # Monorepo root
├── pyproject.toml                           # Workspace configuration
├── uv.lock                                  # Workspace lockfile
├── README.md                                # Ecosystem overview
│
├── libs/                                    # Library packages
│   ├── waivern-core/                        # Tier 1: Base abstractions
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── waivern_core/
│   │   │       ├── __init__.py
│   │   │       ├── base_connector.py        # BaseConnector ABC
│   │   │       ├── base_analyser.py         # BaseAnalyser ABC
│   │   │       ├── base_ruleset.py          # BaseRuleset ABC
│   │   │       ├── message.py               # Message protocol
│   │   │       ├── errors.py                # Core exceptions
│   │   │       ├── schemas/                 # Schema types
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py
│   │   │       │   ├── runbook.py
│   │   │       │   └── types.py
│   │   │       └── utils.py
│   │   └── tests/
│   │       └── waivern_core/
│   │
│   ├── waivern-llm/                         # LLM abstraction layer
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── waivern_llm/
│   │   │       ├── __init__.py
│   │   │       ├── base.py                  # BaseLLMService
│   │   │       ├── factory.py               # LLMServiceFactory
│   │   │       ├── anthropic.py             # AnthropicLLMService
│   │   │       ├── openai.py                # OpenAILLMService
│   │   │       ├── google.py                # GoogleLLMService (future)
│   │   │       ├── cohere.py                # CohereLLMService (future)
│   │   │       └── errors.py                # LLM exceptions
│   │   └── tests/
│   │       └── waivern_llm/
│   │
│   ├── waivern-community/                   # Tier 2: All built-in implementations
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── waivern_community/
│   │   │       ├── __init__.py
│   │   │       ├── connectors/              # All built-in connectors
│   │   │       │   ├── __init__.py
│   │   │       │   ├── mysql/
│   │   │       │   │   ├── __init__.py
│   │   │       │   │   ├── connector.py
│   │   │       │   │   └── config.py
│   │   │       │   ├── sqlite/
│   │   │       │   ├── postgres/            # Future
│   │   │       │   ├── filesystem/
│   │   │       │   └── source_code/
│   │   │       ├── analysers/               # All built-in analysers
│   │   │       │   ├── __init__.py
│   │   │       │   ├── personal_data/
│   │   │       │   │   ├── __init__.py
│   │   │       │   │   ├── analyser.py
│   │   │       │   │   ├── llm_validation_strategy.py
│   │   │       │   │   └── pattern_matcher.py
│   │   │       │   ├── processing_purpose/
│   │   │       │   ├── data_subject/
│   │   │       │   └── utilities/           # Shared analyser utilities
│   │   │       │       ├── llm_service_manager.py
│   │   │       │       ├── ruleset_manager.py
│   │   │       │       └── evidence_extractor.py
│   │   │       └── rulesets/                # All built-in rulesets
│   │   │           ├── __init__.py
│   │   │           ├── data/                # YAML ruleset files
│   │   │           ├── personal_data.py
│   │   │           ├── processing_purposes.py
│   │   │           ├── data_subjects.py
│   │   │           └── service_integrations.py
│   │   └── tests/
│   │       └── waivern_community/
│   │
│   ├── waivern-mysql/                       # Tier 3: Individual connector (optional)
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── waivern_mysql/
│   │   │       ├── __init__.py
│   │   │       ├── connector.py
│   │   │       └── config.py
│   │   └── tests/
│   │
│   ├── waivern-postgres/                    # Tier 3: Individual connector (future)
│   │   └── ...
│   │
│   └── waivern-personal-data/               # Tier 3: Individual analyser (future)
│       └── ...
│
├── apps/                                    # Application packages
│   ├── wct/                                 # CLI tool
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/
│   │   │   └── wct/
│   │   │       ├── __init__.py
│   │   │       ├── __main__.py
│   │   │       ├── cli.py                   # CLI commands
│   │   │       ├── executor.py              # Runbook executor
│   │   │       ├── plugin_loader.py         # Dynamic component loading
│   │   │       ├── logging.py
│   │   │       └── config/
│   │   └── tests/
│   │
│   └── waivern-web/                         # Future: Web UI
│       └── ...
│
├── docs/                                    # Documentation
│   ├── architecture/
│   │   ├── monorepo-migration-plan.md       # This document
│   │   └── plugin-system.md
│   ├── contributing/
│   │   ├── create-connector.md
│   │   ├── create-analyser.md
│   │   ├── create-ruleset.md
│   │   └── package-publishing.md
│   └── examples/
│       ├── custom-connector/
│       ├── custom-analyser/
│       └── remote-component/
│
├── runbooks/                                # Example runbooks
│   └── samples/
│
└── scripts/                                 # Development scripts
    ├── dev-checks.sh
    └── publish-packages.sh
```

---

## Migration Phases

### Overview Timeline

| Phase | Effort | Risk | Status |
|-------|--------|------|--------|
| Pre-Phase 1: Architectural Cleanup | 3-4 hours | Low | ✅ Complete |
| Phase 0: Pre-work | 1 hour | Low | ✅ Complete |
| Phase 1: Workspace Setup + waivern-core | 2-3 hours | Low | ✅ Complete |
| Phase 1.6: Package-Centric Quality Checks | 4-5 hours | Low | ✅ Complete |
| Phase 2: Extract waivern-llm (PoC) | 2-3 hours | Low | Pending |
| Phase 3: Create waivern-community | 4-6 hours | Medium | Pending |
| Phase 4: Extract individual packages | 1-2 hours each | Low | Pending |
| Phase 5: Dynamic plugin loading | 3-4 hours | Medium | Pending |
| Phase 6: Contribution infrastructure | 2-3 hours | Low | Pending |

**Total estimated effort:** 18-26 hours (**11-13 hours completed**, 7-13 hours remaining)

---

### Completed Phases

See **[monorepo-migration-completed.md](./monorepo-migration-completed.md)** for detailed documentation of:
- Pre-Phase 1: Architectural Cleanup
- Phase 0: Pre-work
- Phase 1: Workspace Setup
- Phase 1.6: Package-Centric Quality Checks

---

### Phase 1: Quick Reference (Completed)

**Goal:** Create UV workspace structure and formalise waivern-core package
**Status:** ✅ Complete
**Commits:** 714a137, 7d05ee7

**Key Achievements:**
- UV workspace with 2 packages (waivern-core, wct)
- Package-centric quality checks architecture
- Independent package development capability

**Next Actions:**

1. Create directory structure:
   ```bash
   mkdir -p libs/waivern-core/src/waivern_core
   mkdir -p libs/waivern-core/tests/waivern_core
   mkdir -p apps/wct/src/wct
   mkdir -p apps/wct/tests
   ```

2. Update root `pyproject.toml`:
   ```toml
   [tool.uv.workspace]
   members = [
       "libs/waivern-core",
       "libs/waivern-llm",
       "libs/waivern-community",
       "apps/wct",
   ]
   ```

3. Create `libs/waivern-core/pyproject.toml`:
   ```toml
   [project]
   name = "waivern-core"
   version = "0.1.0"
   description = "Core abstractions for Waivern Compliance Framework"
   readme = "README.md"
   requires-python = ">=3.12"
   dependencies = [
       "pydantic>=2.11.5",
       "typing-extensions>=4.14.0",
       "annotated-types>=0.7.0",
   ]

   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [tool.hatch.build.targets.wheel]
   packages = ["src/waivern_core"]
   ```

#### 1.2: Verify Base Classes in waivern-core

**✅ Already Done in Pre-Phase 1:**

| Current Location | Status | Notes |
|------------------|--------|-------|
| `libs/waivern-core/src/waivern_core/base_connector.py` | ✅ Exists | `BaseConnector`, `ConnectorError` |
| `libs/waivern-core/src/waivern_core/base_analyser.py` | ✅ Exists | `Analyser`, `AnalyserError`, `AnalyserInputError`, `AnalyserProcessingError` |
| `libs/waivern-core/src/waivern_core/base_ruleset.py` | ⚠️ TODO | Needs extraction from WCT |
| `libs/waivern-core/src/waivern_core/message.py` | ✅ Exists | `Message` protocol |
| `libs/waivern-core/src/waivern_core/schemas/base.py` | ✅ Exists | `Schema`, `SchemaLoader`, `JsonSchemaLoader`, `SchemaLoadError` |

**Remaining Work:**
- Extract `BaseRuleset` from `src/wct/rulesets/base.py` to `libs/waivern-core/src/waivern_core/base_ruleset.py`
- Update imports for `BaseRuleset` across codebase

**Example: `libs/waivern-core/src/waivern_core/base_connector.py`**

```python
"""Base connector abstraction for Waivern Compliance Framework."""

from __future__ import annotations

from abc import ABC, abstractmethod

from waivern_core.message import Message


class BaseConnector(ABC):
    """Abstract base class for data source connectors.

    All connectors must implement this interface to be compatible with
    the Waivern Compliance Framework.
    """

    @abstractmethod
    def get_output_schema(self) -> str:
        """Return the output schema name this connector produces.

        Returns:
            Schema name (e.g., "standard_input", "source_code")
        """
        pass

    @abstractmethod
    def extract(self) -> Message:
        """Extract data from the source and return as a Message.

        Returns:
            Message containing extracted data conforming to output schema

        Raises:
            ConnectorError: If extraction fails
        """
        pass
```

#### 1.3: Update Imports in Current Codebase

**✅ Already Done in Pre-Phase 1:**

All imports for `BaseConnector`, `Analyser` (formerly `BaseAnalyser`), `Message`, and schema classes have been updated to use `waivern_core` directly.

**Current import pattern (already implemented):**
```python
# Connectors
from waivern_core.base_connector import BaseConnector, ConnectorError

# Analysers
from waivern_core import Analyser, AnalyserError, AnalyserInputError, AnalyserProcessingError

# Message
from waivern_core.message import Message

# Schemas
from waivern_core.schemas import Schema, SchemaLoader, JsonSchemaLoader, SchemaLoadError
```

**⚠️ Remaining Work:**
- Update imports for `BaseRuleset` once extracted to waivern-core
- No re-export layers - all imports must be direct from waivern_core (per user requirement)

#### 1.4: Verification

```bash
# Install workspace packages
uv sync

# Run all tests (should all pass)
uv run pytest

# Run type checking (should pass)
uv run basedpyright

# Run linting (should pass)
uv run ruff check
```

#### 1.5: Commit Phase 1

```bash
git add -A
git commit -m "refactor: create uv workspace and extract waivern-core

Create monorepo workspace structure with waivern-core package containing
base abstractions for connectors, analysers, and rulesets.

Changes:
- Add uv workspace configuration to root pyproject.toml
- Create libs/waivern-core/ with base abstractions
- Extract BaseConnector, BaseAnalyser, BaseRuleset to waivern-core
- Move Message protocol to waivern-core
- Update all imports to use waivern-core

Test results:
- All 726 unit tests pass
- All 8 integration tests pass
- Type checking passes
- Linting passes

Breaking changes: None (internal refactoring only)
"
```

#### 1.6: Package-Centric Quality Checks Architecture (COMPLETED)

**Goal:** Implement package-centric quality checks following monorepo best practices
**Duration:** 4-5 hours
**Status:** ✅ Complete
**Commit:** `7d05ee7`

After the workspace structure was created, we implemented a proper package-centric quality checks architecture following industry best practices (LangChain, boto3, airflow, pallets pattern).

**Problems Solved:**
1. Inconsistency between dev-checks and pre-commit behaviour
2. Workspace-level tool configs coupling packages together
3. Inability to check packages independently
4. Mixed workspace/package concerns

**Implementation:**

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

**Benefits:**
- ✅ Package independence - each package can be checked in isolation
- ✅ Consistent behaviour - dev-checks and pre-commit use same configs
- ✅ Standard pattern - follows monorepo best practices
- ✅ Clean separation - workspace doesn't know package internals

**Usage:**
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

**Test Results:**
- ✅ 737 tests passing
- ✅ Type checking: 0 errors (src/ only)
- ✅ Linting: All checks passed
- ✅ Formatting: 173 files checked
- ✅ All pre-commit hooks passing

---

### Phase 2: Extract waivern-llm (Proof of Concept)

**Goal:** Move LLM service to standalone package, prove dynamic loading works
**Duration:** 2-3 hours
**Risk:** Low

#### 2.1: Create waivern-llm Package

**Create `libs/waivern-llm/pyproject.toml`:**

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
openai = ["langchain-openai>=0.2.0"]
google = ["langchain-google-genai>=2.0.0"]
cohere = ["langchain-cohere>=0.3.0"]
all = ["waivern-llm[openai,google,cohere]"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_llm"]
```

#### 2.2: Move LLM Service Files

| Current Location | New Location |
|------------------|--------------|
| `src/wct/llm_service.py` | `libs/waivern-llm/src/waivern_llm/` |
| `tests/wct/llm_service/` | `libs/waivern-llm/tests/waivern_llm/` |

**Split `llm_service.py` into modules:**

```
libs/waivern-llm/src/waivern_llm/
├── __init__.py
├── base.py                # BaseLLMService
├── factory.py             # LLMServiceFactory
├── anthropic.py           # AnthropicLLMService
├── openai.py              # OpenAILLMService
├── google.py              # GoogleLLMService (future)
├── cohere.py              # CohereLLMService (future)
└── errors.py              # LLM exceptions
```

#### 2.3: Update Imports

```python
# Before
from wct.llm_service import BaseLLMService, LLMServiceFactory, AnthropicLLMService

# After
from waivern_llm import BaseLLMService, LLMServiceFactory, AnthropicLLMService
```

#### 2.4: Verification

```bash
uv sync
uv run pytest
uv run pytest -m integration
./scripts/dev-checks.sh
```

#### 2.5: Commit Phase 2

```bash
git add -A
git commit -m "refactor: extract waivern-llm as standalone package

Move LLM service abstraction to separate waivern-llm package with
multi-provider support (Anthropic, OpenAI, Google, Cohere).

Changes:
- Create libs/waivern-llm/ package
- Split llm_service.py into focused modules
- Move tests to waivern-llm package
- Update imports across codebase

Test results:
- All 726 unit tests pass
- All 8 integration tests pass
- Type checking passes
- Linting passes

Breaking changes: None (import paths updated)
"
```

---

### Phase 3: Create waivern-community

**Goal:** Move all built-in connectors/analysers/rulesets to community package
**Duration:** 4-6 hours
**Risk:** Medium (large refactor)

#### 3.1: Create waivern-community Package

**Create `libs/waivern-community/pyproject.toml`:**

```toml
[project]
name = "waivern-community"
version = "0.1.0"
description = "Built-in connectors, analysers, and rulesets for Waivern Compliance Framework"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-llm",
    "jsonschema>=4.25.0",
    "pydantic>=2.11.5",
    "pyyaml>=6.0.2",
    "cryptography>=45.0.5",
    "pymysql>=1.1.1",
    "tree-sitter>=0.21.0",
    "tree-sitter-php>=0.22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_community"]
```

#### 3.2: Move Components

**Connectors:**

| Current | New |
|---------|-----|
| `src/wct/connectors/mysql/` | `libs/waivern-community/src/waivern_community/connectors/mysql/` |
| `src/wct/connectors/sqlite/` | `libs/waivern-community/src/waivern_community/connectors/sqlite/` |
| `src/wct/connectors/filesystem/` | `libs/waivern-community/src/waivern_community/connectors/filesystem/` |
| `src/wct/connectors/source_code/` | `libs/waivern-community/src/waivern_community/connectors/source_code/` |

**Analysers:**

| Current | New |
|---------|-----|
| `src/wct/analysers/personal_data_analyser/` | `libs/waivern-community/src/waivern_community/analysers/personal_data/` |
| `src/wct/analysers/processing_purpose_analyser/` | `libs/waivern-community/src/waivern_community/analysers/processing_purpose/` |
| `src/wct/analysers/data_subject_analyser/` | `libs/waivern-community/src/waivern_community/analysers/data_subject/` |
| `src/wct/analysers/utilities/` | `libs/waivern-community/src/waivern_community/analysers/utilities/` |

**Rulesets:**

| Current | New |
|---------|-----|
| `src/wct/rulesets/` | `libs/waivern-community/src/waivern_community/rulesets/` |

**Prompts:**

| Current | New |
|---------|-----|
| `src/wct/prompts/` | `libs/waivern-community/src/waivern_community/prompts/` |

#### 3.3: Update Package Exports

**`libs/waivern-community/src/waivern_community/__init__.py`:**

```python
"""Waivern Community - Built-in connectors, analysers, and rulesets."""

__version__ = "0.1.0"

# Connectors
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.connectors.sqlite import SQLiteConnector
from waivern_community.connectors.filesystem import FilesystemConnector
from waivern_community.connectors.source_code import SourceCodeConnector

# Analysers
from waivern_community.analysers.personal_data import PersonalDataAnalyser
from waivern_community.analysers.processing_purpose import ProcessingPurposeAnalyser
from waivern_community.analysers.data_subject import DataSubjectAnalyser

# Rulesets
from waivern_community.rulesets.personal_data import PersonalDataRuleset
from waivern_community.rulesets.processing_purposes import ProcessingPurposeRuleset
from waivern_community.rulesets.data_subjects import DataSubjectRuleset

__all__ = [
    # Connectors
    "MySQLConnector",
    "SQLiteConnector",
    "FilesystemConnector",
    "SourceCodeConnector",
    # Analysers
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",
    "DataSubjectAnalyser",
    # Rulesets
    "PersonalDataRuleset",
    "ProcessingPurposeRuleset",
    "DataSubjectRuleset",
]
```

#### 3.4: Update Imports Throughout Codebase

```python
# Before
from wct.connectors.mysql import MySQLConnector
from wct.analysers.personal_data_analyser import PersonalDataAnalyser

# After
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.analysers.personal_data import PersonalDataAnalyser
```

#### 3.5: Move Tests

Move all component tests to waivern-community:

```
libs/waivern-community/tests/
├── waivern_community/
│   ├── connectors/
│   │   ├── test_mysql.py
│   │   ├── test_sqlite.py
│   │   ├── test_filesystem.py
│   │   └── test_source_code.py
│   ├── analysers/
│   │   ├── test_personal_data.py
│   │   ├── test_processing_purpose.py
│   │   └── test_data_subject.py
│   └── rulesets/
│       └── test_rulesets.py
```

#### 3.6: Verification

```bash
uv sync
uv run pytest libs/waivern-community/tests/
uv run pytest apps/wct/tests/
./scripts/dev-checks.sh
```

#### 3.7: Commit Phase 3

```bash
git add -A
git commit -m "refactor: create waivern-community with all built-in components

Move all connectors, analysers, and rulesets to waivern-community package
for batteries-included experience.

Changes:
- Create libs/waivern-community/ package
- Move all connectors (mysql, sqlite, filesystem, source_code)
- Move all analysers (personal_data, processing_purpose, data_subject)
- Move all rulesets and prompts
- Update imports across codebase
- Move tests to respective packages

Test results:
- All 726 unit tests pass
- All 8 integration tests pass
- Type checking passes
- Linting passes

Breaking changes: None (import paths updated)
"
```

---

### Phase 4: Extract Individual Packages (Optional)

**Goal:** Create standalone packages for popular components
**Duration:** 1-2 hours per package
**Risk:** Low

#### 4.1: Example - Extract waivern-mysql

**Create `libs/waivern-mysql/pyproject.toml`:**

```toml
[project]
name = "waivern-mysql"
version = "0.1.0"
description = "MySQL connector for Waivern Compliance Framework"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "pymysql>=1.1.1",
    "cryptography>=45.0.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_mysql"]
```

**Copy from waivern-community:**

```bash
cp -r libs/waivern-community/src/waivern_community/connectors/mysql \
      libs/waivern-mysql/src/waivern_mysql/

cp -r libs/waivern-community/tests/waivern_community/connectors/test_mysql.py \
      libs/waivern-mysql/tests/waivern_mysql/
```

**Update imports in waivern-mysql:**

```python
# Change package references
from waivern_community.connectors.mysql import MySQLConnector
# to
from waivern_mysql import MySQLConnector
```

**Keep waivern-community version as re-export:**

```python
# libs/waivern-community/src/waivern_community/connectors/mysql/__init__.py
"""MySQL connector - re-exported from waivern-mysql package."""

try:
    from waivern_mysql import MySQLConnector
except ImportError:
    # Fallback to bundled version if waivern-mysql not installed
    from waivern_community.connectors.mysql.connector import MySQLConnector

__all__ = ["MySQLConnector"]
```

#### 4.2: Repeat for Other Popular Components

Priority order:
1. ✅ `waivern-mysql` (most common connector)
2. `waivern-postgres` (common connector)
3. `waivern-personal-data` (most used analyser)
4. Others as needed

---

### Phase 5: Dynamic Plugin Loading

**Goal:** Implement plugin system in WCT executor for dynamic component loading
**Duration:** 3-4 hours
**Risk:** Medium

#### 5.1: Create WCT Application Package

**Create `apps/wct/pyproject.toml`:**

```toml
[project]
name = "waivern-compliance-tool"
version = "0.1.0"
description = "CLI tool for Waivern Compliance Framework"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-community",  # Includes all built-in components
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "typer>=0.16.0",
]

[project.scripts]
wct = "wct.__main__:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wct"]
```

#### 5.2: Implement PluginLoader

**Create `apps/wct/src/wct/plugin_loader.py`:**

```python
"""Dynamic plugin loading for Waivern components."""

from __future__ import annotations

import logging
from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from waivern_core.base_analyser import BaseAnalyser
    from waivern_core.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class PluginLoader:
    """Dynamically load connectors and analysers from installed packages."""

    @staticmethod
    def load_connector(
        connector_type: str,
        source: str = "community",
        **kwargs: Any,
    ) -> BaseConnector:
        """Load connector by type from specified source.

        Args:
            connector_type: Connector type (e.g., "mysql", "postgres")
            source: Package source:
                - "community" (default): Load from waivern-community
                - "package:name": Load from specific package
                - "remote:url": Load from remote registry (future)
            **kwargs: Configuration parameters for connector

        Returns:
            Connector instance

        Raises:
            ImportError: If connector package not found
            ValueError: If connector type not supported

        Examples:
            # Load from community package
            connector = PluginLoader.load_connector("mysql", source="community")

            # Load from standalone package
            connector = PluginLoader.load_connector(
                "postgres",
                source="package:waivern-postgres"
            )

            # Load from remote (future)
            connector = PluginLoader.load_connector(
                "custom_db",
                source="remote:https://plugins.waivern.com/connectors/custom_db"
            )
        """
        logger.debug(f"Loading connector: type={connector_type}, source={source}")

        # Parse source
        if source == "community":
            return PluginLoader._load_from_community("connectors", connector_type, **kwargs)
        elif source.startswith("package:"):
            package_name = source.split(":", 1)[1]
            return PluginLoader._load_from_package(package_name, **kwargs)
        elif source.startswith("remote:"):
            url = source.split(":", 1)[1]
            return PluginLoader._load_from_remote(url, **kwargs)
        else:
            raise ValueError(f"Unknown source type: {source}")

    @staticmethod
    def load_analyser(
        analyser_type: str,
        source: str = "community",
        **kwargs: Any,
    ) -> BaseAnalyser:
        """Load analyser by type from specified source.

        Args:
            analyser_type: Analyser type (e.g., "personal_data", "processing_purpose")
            source: Package source (see load_connector for options)
            **kwargs: Configuration parameters for analyser

        Returns:
            Analyser instance

        Raises:
            ImportError: If analyser package not found
            ValueError: If analyser type not supported
        """
        logger.debug(f"Loading analyser: type={analyser_type}, source={source}")

        # Parse source
        if source == "community":
            return PluginLoader._load_from_community("analysers", analyser_type, **kwargs)
        elif source.startswith("package:"):
            package_name = source.split(":", 1)[1]
            return PluginLoader._load_from_package(package_name, **kwargs)
        elif source.startswith("remote:"):
            url = source.split(":", 1)[1]
            return PluginLoader._load_from_remote(url, **kwargs)
        else:
            raise ValueError(f"Unknown source type: {source}")

    @staticmethod
    def _load_from_community(
        component_type: str,
        component_name: str,
        **kwargs: Any,
    ) -> BaseConnector | BaseAnalyser:
        """Load component from waivern-community package.

        Args:
            component_type: "connectors" or "analysers"
            component_name: Component name (e.g., "mysql", "personal_data")
            **kwargs: Configuration parameters

        Returns:
            Component instance

        Raises:
            ImportError: If component not found in community package
        """
        try:
            # Import module
            module_path = f"waivern_community.{component_type}.{component_name}"
            module = import_module(module_path)

            # Get class (convention: PascalCase version of component_name)
            class_name = "".join(word.capitalize() for word in component_name.split("_"))
            if component_type == "connectors":
                class_name += "Connector"
            elif component_type == "analysers":
                class_name += "Analyser"

            component_class = getattr(module, class_name)
            logger.info(f"Loaded {class_name} from waivern-community")

            # Instantiate with kwargs
            return component_class(**kwargs)

        except ImportError as e:
            logger.error(
                f"Failed to load {component_name} from waivern-community: {e}\n"
                f"Ensure waivern-community is installed: uv add waivern-community"
            )
            raise

    @staticmethod
    def _load_from_package(package_name: str, **kwargs: Any) -> BaseConnector | BaseAnalyser:
        """Load component from standalone package.

        Args:
            package_name: Package name (e.g., "waivern-mysql")
            **kwargs: Configuration parameters

        Returns:
            Component instance

        Raises:
            ImportError: If package not found
        """
        try:
            # Import package
            module = import_module(package_name.replace("-", "_"))

            # Get component class (convention: exported in __init__.py)
            # Assume package exports single main class
            if hasattr(module, "Connector"):
                component_class = module.Connector
            elif hasattr(module, "Analyser"):
                component_class = module.Analyser
            else:
                # Try to find first BaseConnector/BaseAnalyser subclass
                from waivern_core.base_analyser import BaseAnalyser
                from waivern_core.base_connector import BaseConnector

                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, type) and (
                        issubclass(obj, BaseConnector) or issubclass(obj, BaseAnalyser)
                    ):
                        component_class = obj
                        break
                else:
                    raise ValueError(f"No connector/analyser found in {package_name}")

            logger.info(f"Loaded {component_class.__name__} from {package_name}")

            # Instantiate with kwargs
            return component_class(**kwargs)

        except ImportError as e:
            logger.error(
                f"Failed to load {package_name}: {e}\n"
                f"Ensure package is installed: uv add {package_name}"
            )
            raise

    @staticmethod
    def _load_from_remote(url: str, **kwargs: Any) -> BaseConnector | BaseAnalyser:
        """Load component from remote registry (future feature).

        Args:
            url: Remote component URL
            **kwargs: Configuration parameters

        Returns:
            Component instance

        Raises:
            NotImplementedError: Remote loading not yet implemented
        """
        raise NotImplementedError(
            "Remote component loading is not yet implemented. "
            "This is a planned feature for platform-as-a-service model."
        )


class PluginRegistry:
    """Registry of available plugins (future feature)."""

    @staticmethod
    def list_available_connectors() -> list[str]:
        """List all available connector types.

        Returns:
            List of connector type names
        """
        # Future: Query registry API
        return [
            "mysql",
            "sqlite",
            "postgres",
            "filesystem",
            "source_code",
        ]

    @staticmethod
    def list_available_analysers() -> list[str]:
        """List all available analyser types.

        Returns:
            List of analyser type names
        """
        # Future: Query registry API
        return [
            "personal_data",
            "processing_purpose",
            "data_subject",
        ]

    @staticmethod
    def search_plugins(query: str) -> list[dict[str, Any]]:
        """Search for plugins in registry (future feature).

        Args:
            query: Search query

        Returns:
            List of plugin metadata

        Raises:
            NotImplementedError: Plugin search not yet implemented
        """
        raise NotImplementedError("Plugin search is not yet implemented.")
```

#### 5.3: Update Executor to Use PluginLoader

**Update `apps/wct/src/wct/executor.py`:**

```python
"""Runbook executor with dynamic plugin loading."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from wct.plugin_loader import PluginLoader

if TYPE_CHECKING:
    from waivern_core.base_analyser import BaseAnalyser
    from waivern_core.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class Executor:
    """Execute runbooks with dynamic component loading."""

    def __init__(self, runbook: dict) -> None:
        """Initialise executor with runbook configuration.

        Args:
            runbook: Parsed runbook dictionary
        """
        self.runbook = runbook
        self.connectors: dict[str, BaseConnector] = {}
        self.analysers: dict[str, BaseAnalyser] = {}

    def load_connectors(self) -> None:
        """Load all connectors defined in runbook."""
        for connector_config in self.runbook.get("connectors", []):
            name = connector_config["name"]
            connector_type = connector_config["type"]
            source = connector_config.get("source", "community")
            properties = connector_config.get("properties", {})

            logger.info(f"Loading connector: {name} (type={connector_type}, source={source})")

            # Load connector dynamically
            connector = PluginLoader.load_connector(
                connector_type=connector_type,
                source=source,
                **properties,
            )

            self.connectors[name] = connector
            logger.info(f"Loaded connector: {name}")

    def load_analysers(self) -> None:
        """Load all analysers defined in runbook."""
        for analyser_config in self.runbook.get("analysers", []):
            name = analyser_config["name"]
            analyser_type = analyser_config["type"]
            source = analyser_config.get("source", "community")
            properties = analyser_config.get("properties", {})

            logger.info(f"Loading analyser: {name} (type={analyser_type}, source={source})")

            # Load analyser dynamically
            analyser = PluginLoader.load_analyser(
                analyser_type=analyser_type,
                source=source,
                **properties,
            )

            self.analysers[name] = analyser
            logger.info(f"Loaded analyser: {name}")

    def execute(self) -> None:
        """Execute runbook with dynamically loaded components."""
        # Load components
        self.load_connectors()
        self.load_analysers()

        # Execute steps
        for step in self.runbook.get("execution", []):
            self._execute_step(step)

    def _execute_step(self, step: dict) -> None:
        """Execute a single runbook step.

        Args:
            step: Step configuration
        """
        connector_name = step["connector"]
        analyser_name = step["analyser"]

        logger.info(f"Executing step: {step['name']}")

        # Get components
        connector = self.connectors[connector_name]
        analyser = self.analysers[analyser_name]

        # Extract data
        logger.debug(f"Extracting data with {connector_name}")
        message = connector.extract()

        # Analyse data
        logger.debug(f"Analysing data with {analyser_name}")
        result = analyser.process(message)

        # Store result
        logger.info(f"Step completed: {step['name']}")
        # TODO: Store result in output
```

#### 5.4: Update Runbook Schema to Support Source

**Example runbook with source specification:**

```yaml
name: "Multi-source Example"
description: "Demonstrates loading components from different sources"

connectors:
  # Load from community (default)
  - name: "mysql_db"
    type: "mysql"
    source: "community"  # Optional, this is default
    properties:
      host: "localhost"
      database: "mydb"

  # Load from standalone package
  - name: "postgres_db"
    type: "postgres"
    source: "package:waivern-postgres"
    properties:
      host: "localhost"
      database: "mydb"

  # Future: Load from remote
  - name: "custom_api"
    type: "custom_api"
    source: "remote:https://plugins.waivern.com/connectors/custom_api"
    properties:
      api_key: "${CUSTOM_API_KEY}"

analysers:
  # Load from community
  - name: "pii_analyser"
    type: "personal_data"
    source: "community"
    properties:
      enable_llm_validation: true

  # Load from standalone package
  - name: "custom_analyser"
    type: "custom_compliance"
    source: "package:acme-compliance-analyser"
    properties:
      ruleset: "financial"

execution:
  - name: "Analyse MySQL database"
    connector: "mysql_db"
    analyser: "pii_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_findings"
```

#### 5.5: Verification

**Test plugin loading:**

```python
# Test loading from community
from wct.plugin_loader import PluginLoader

connector = PluginLoader.load_connector("mysql", source="community", host="localhost")
assert connector is not None

analyser = PluginLoader.load_analyser("personal_data", source="community")
assert analyser is not None

# Test loading from standalone package
connector = PluginLoader.load_connector("postgres", source="package:waivern-postgres")
assert connector is not None
```

**Run integration tests:**

```bash
uv run pytest apps/wct/tests/test_plugin_loader.py
```

#### 5.6: Commit Phase 5

```bash
git add -A
git commit -m "feat: implement dynamic plugin loading system

Add plugin loader to WCT executor for dynamic component discovery and loading
from multiple sources (community, standalone packages, remote).

Changes:
- Create apps/wct/ as standalone application package
- Implement PluginLoader with multi-source support
- Update Executor to use dynamic loading
- Add 'source' field to runbook schema
- Support loading from waivern-community, standalone packages, remote (future)

Features:
- Load connectors/analysers from community package (default)
- Load from standalone packages (e.g., waivern-postgres)
- Extensible for remote plugin registry (future)
- Helpful error messages for missing packages

Test results:
- All plugin loading tests pass
- Integration tests with dynamic loading pass
- Type checking passes
- Linting passes

Breaking changes: None (backward compatible, 'source' is optional)
"
```

---

### Phase 6: Contribution Infrastructure

**Goal:** Create guides, templates, and tooling for third-party contributors
**Duration:** 2-3 hours
**Risk:** Low

#### 6.1: Create Contribution Guides

**Create `docs/contributing/create-connector.md`:**

```markdown
# Creating a Connector for Waivern Compliance Framework

This guide walks you through creating a custom connector for Waivern.

## Two Approaches

### Option A: Add to waivern-community (Recommended for most)

**Best for:**
- Standard data sources (databases, APIs, filesystems)
- Want connector available to all users by default
- Want to contribute to core framework

**Process:**
1. Fork `waivern-compliance` repository
2. Add connector to `libs/waivern-community/src/waivern_community/connectors/`
3. Add tests to `libs/waivern-community/tests/`
4. Submit PR

### Option B: Create standalone package

**Best for:**
- Proprietary/specialised connectors
- Want independent versioning
- Want to maintain separately

**Process:**
1. Create new repository: `waivern-{connector-name}`
2. Implement connector following interface
3. Publish to PyPI
4. Users install with: `uv add waivern-{connector-name}`

## Step-by-Step Guide

### 1. Install waivern-core

```bash
uv add waivern-core
```

### 2. Create Connector Class

```python
# src/waivern_myconnector/connector.py
from waivern_core.base_connector import BaseConnector
from waivern_core.message import Message


class MyConnector(BaseConnector):
    """Connector for MyDataSource."""

    def __init__(self, host: str, api_key: str):
        """Initialise connector.

        Args:
            host: Data source host
            api_key: API authentication key
        """
        self.host = host
        self.api_key = api_key

    def get_output_schema(self) -> str:
        """Return output schema name."""
        return "standard_input"

    def extract(self) -> Message:
        """Extract data from source."""
        # Your extraction logic here
        data = self._fetch_data()

        return Message(
            data=data,
            metadata={
                "source": "myconnector",
                "schema": self.get_output_schema(),
            }
        )

    def _fetch_data(self) -> dict:
        """Fetch data from source (implementation detail)."""
        # Your implementation
        pass
```

### 3. Add Tests

```python
# tests/test_connector.py
import pytest
from waivern_myconnector import MyConnector


def test_connector_extraction():
    """Test connector extracts data correctly."""
    connector = MyConnector(host="localhost", api_key="test-key")
    message = connector.extract()

    assert message is not None
    assert message.data is not None
```

### 4. Package Configuration

```toml
# pyproject.toml
[project]
name = "waivern-myconnector"
version = "0.1.0"
description = "MyDataSource connector for Waivern Compliance Framework"
dependencies = [
    "waivern-core",
    # Your connector dependencies
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 5. Usage in Runbook

```yaml
connectors:
  - name: "my_source"
    type: "myconnector"
    source: "package:waivern-myconnector"
    properties:
      host: "data.example.com"
      api_key: "${MY_API_KEY}"
```

## Examples

See `docs/examples/custom-connector/` for complete examples.

## Getting Help

- GitHub Discussions: https://github.com/waivern-compliance/waivern-compliance/discussions
- Documentation: https://docs.waivern.com
```

**Create similar guides:**
- `docs/contributing/create-analyser.md`
- `docs/contributing/create-ruleset.md`
- `docs/contributing/package-publishing.md`

#### 6.2: Create Example Template

**Create `docs/examples/custom-connector/` with complete working example:**

```
docs/examples/custom-connector/
├── README.md
├── pyproject.toml
├── src/
│   └── waivern_example/
│       ├── __init__.py
│       └── connector.py
├── tests/
│   └── test_connector.py
└── example-runbook.yaml
```

#### 6.3: Create Package Publishing Script

**Create `scripts/publish-packages.sh`:**

```bash
#!/bin/bash
# Publish all workspace packages to PyPI

set -e

PACKAGES=(
    "libs/waivern-core"
    "libs/waivern-llm"
    "libs/waivern-community"
    "libs/waivern-mysql"
    "apps/wct"
)

for package in "${PACKAGES[@]}"; do
    echo "Publishing $package..."
    cd "$package"
    uv build
    uv publish
    cd -
done

echo "All packages published successfully!"
```

#### 6.4: Update Main README

**Update `README.md` with ecosystem overview:**

```markdown
# Waivern Compliance Framework

Modern, extensible compliance analysis framework for GDPR and beyond.

## Packages

### Core Libraries

- **waivern-core** - Base abstractions for connectors, analysers, rulesets
- **waivern-llm** - Multi-provider LLM abstraction (Anthropic, OpenAI, Google, Cohere)
- **waivern-community** - Built-in connectors, analysers, and rulesets

### Applications

- **wct** - Command-line tool for running compliance analysis
- **waivern-web** - Web UI (coming soon)

### Standalone Connectors

- **waivern-mysql** - MySQL database connector
- **waivern-postgres** - PostgreSQL database connector

## Quick Start

```bash
# Install CLI tool (includes waivern-community)
uv add waivern-compliance-tool

# Run analysis
wct run runbooks/my-runbook.yaml
```

## Creating Custom Components

See [Contributing Guide](docs/contributing/) for how to create:
- Custom connectors
- Custom analysers
- Custom rulesets

## Architecture

See [Architecture Documentation](docs/architecture/) for details on:
- Monorepo structure
- Plugin system
- Remote components
```

#### 6.5: Commit Phase 6

```bash
git add -A
git commit -m "docs: add contribution infrastructure and guides

Create comprehensive guides and templates for third-party contributors
to build custom connectors, analysers, and rulesets.

Changes:
- Add docs/contributing/create-connector.md
- Add docs/contributing/create-analyser.md
- Add docs/contributing/create-ruleset.md
- Add docs/contributing/package-publishing.md
- Create example templates in docs/examples/
- Add package publishing script
- Update main README with ecosystem overview

Breaking changes: None (documentation only)
"
```

---

## Dynamic Plugin Loading

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WCT Executor                            │
│                     (Runbook Runner)                         │
└────────────┬────────────────────────────────────────────────┘
             │
             │ Uses PluginLoader
             ▼
┌─────────────────────────────────────────────────────────────┐
│                     PluginLoader                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Community   │  │  Standalone  │  │   Remote     │     │
│  │   Package    │  │   Package    │  │  (Future)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
             │                │                │
             ▼                ▼                ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│ waivern-community│ │ waivern-mysql│ │ Remote API   │
└──────────────────┘ └──────────────┘ └──────────────┘
```

### Loading Strategy

**Priority order for component loading:**

1. **Check runbook `source` field** - Use specified source if provided
2. **Try waivern-community** - Default, most common case
3. **Try standalone package** - Look for `waivern-{type}` package
4. **Try remote registry** - Future feature for platform model
5. **Error with helpful message** - Guide user to install missing package

### Component Discovery

**Convention-based discovery:**

```python
# For connector type "mysql"
# Try in order:
1. waivern_community.connectors.mysql.MySQLConnector
2. waivern_mysql.MySQLConnector
3. Remote registry lookup

# For analyser type "personal_data"
# Try in order:
1. waivern_community.analysers.personal_data.PersonalDataAnalyser
2. waivern_personal_data.PersonalDataAnalyser
3. Remote registry lookup
```

### Error Handling

**Helpful error messages:**

```python
try:
    connector = PluginLoader.load_connector("postgres")
except ImportError:
    # Error message:
    """
    Failed to load PostgreSQL connector.

    The connector is not available. Please install one of:
    - waivern-community (includes PostgreSQL connector)
      Install with: uv add waivern-community

    - waivern-postgres (standalone package)
      Install with: uv add waivern-postgres

    Or specify a custom source in your runbook:
      source: "package:your-postgres-connector"
    """
```

---

## Third-Party Contribution Model

### Contribution Paths

```
┌─────────────────────────────────────────────────────────────┐
│              Third-Party Contributor                         │
└───────┬─────────────────────────────────────────────────────┘
        │
        │ Choose contribution path
        ▼
┌───────────────────────┐         ┌───────────────────────────┐
│  Option A: Community  │         │  Option B: Standalone     │
│                       │         │                           │
│  Fork monorepo        │         │  Create own repo          │
│  Add to community/    │         │  Publish to PyPI          │
│  Submit PR            │         │  Register in directory    │
└───────────────────────┘         └───────────────────────────┘
        │                                     │
        ▼                                     ▼
┌───────────────────────┐         ┌───────────────────────────┐
│  Available to all     │         │  Users install manually   │
│  users by default     │         │  More control/independence│
└───────────────────────┘         └───────────────────────────┘
```

### Community Package Strategy

**Why include in waivern-community:**
- ✅ Available to all users immediately
- ✅ Maintained by core team
- ✅ Included in testing/CI
- ✅ Easier for users (no extra install)

**When to use standalone:**
- Proprietary connectors (commercial databases, internal APIs)
- Experimental/unstable components
- Want independent versioning
- Large dependencies (keep community package lean)

### Package Naming Convention

**Connectors:** `waivern-{datasource}`
- `waivern-mysql`
- `waivern-postgres`
- `waivern-mongodb`
- `waivern-snowflake`

**Analysers:** `waivern-{analysis-type}`
- `waivern-personal-data`
- `waivern-processing-purpose`
- `waivern-gdpr-compliance`

**Rulesets:** `waivern-rulesets-{domain}`
- `waivern-rulesets-healthcare`
- `waivern-rulesets-finance`

---

## Remote Components

### Vision: Platform-as-a-Service Model

**Goal:** Allow organisations to:
1. Host their own analysers/connectors as services
2. Share components without publishing source code
3. Build SaaS compliance platforms on Waivern

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WCT / Waivern Web                         │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTP/gRPC
             ▼
┌─────────────────────────────────────────────────────────────┐
│              Remote Analyser Service                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Gateway                                          │  │
│  │  - Authentication                                     │  │
│  │  - Rate limiting                                      │  │
│  │  - Usage tracking                                     │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼─────────────────────────────────┐  │
│  │  Waivern Analyser Implementation                      │  │
│  │  (Running on customer infrastructure)                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Remote Component Protocol (Future Design)

**API Specification:**

```yaml
# OpenAPI specification for remote analysers
paths:
  /analyse:
    post:
      summary: Analyse data using remote analyser
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                data:
                  type: object
                  description: Data to analyse (Message.data)
                schema:
                  type: string
                  description: Input schema name
      responses:
        200:
          description: Analysis result
          content:
            application/json:
              schema:
                type: object
                properties:
                  findings:
                    type: array
                  metadata:
                    type: object
```

**Runbook Usage:**

```yaml
analysers:
  - name: "proprietary_pii"
    type: "personal_data"
    source: "remote:https://api.acme-compliance.com/analysers/pii"
    properties:
      api_key: "${ACME_API_KEY}"
      timeout: 30
      retry: 3
```

**Security Considerations:**

1. **Authentication:**
   - API keys
   - OAuth 2.0
   - mTLS for enterprise

2. **Data Privacy:**
   - Encrypt data in transit (TLS)
   - Support on-premise deployments
   - Data residency options

3. **Availability:**
   - Retry logic
   - Circuit breakers
   - Fallback to local analysers

### Remote Registry (Future)

**Package discovery service:**

```bash
# Search for connectors
wct plugins search "salesforce"

# Output:
# waivern-salesforce (community)
#   Description: Salesforce CRM connector
#   Install: uv add waivern-salesforce
#
# acme-salesforce-enterprise (remote)
#   Description: Enterprise Salesforce connector with advanced features
#   Provider: ACME Compliance Inc.
#   Pricing: Contact sales
#   Documentation: https://acme-compliance.com/docs/salesforce
```

---

## Testing Strategy

### Test Organisation

```
libs/waivern-core/tests/           # Core abstractions tests
libs/waivern-llm/tests/             # LLM service tests
libs/waivern-community/tests/       # All component tests
apps/wct/tests/                     # WCT integration tests
```

### Test Categories

**1. Unit Tests (per package)**

```bash
# Test single package
uv run pytest libs/waivern-core/tests/
uv run pytest libs/waivern-llm/tests/
uv run pytest libs/waivern-community/tests/
uv run pytest apps/wct/tests/
```

**2. Integration Tests**

```bash
# Test real APIs (LLM providers)
uv run pytest -m integration

# Test plugin loading
uv run pytest apps/wct/tests/test_plugin_loader.py
```

**3. End-to-End Tests**

```bash
# Test complete runbooks
uv run pytest tests/integration/test_runbook_execution.py
```

### CI/CD Strategy

**GitHub Actions workflow:**

```yaml
name: Test Workspace

on: [push, pull_request]

jobs:
  test-packages:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package:
          - libs/waivern-core
          - libs/waivern-llm
          - libs/waivern-community
          - apps/wct
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Test package
        run: uv run pytest ${{ matrix.package }}/tests/

      - name: Type check
        run: uv run basedpyright ${{ matrix.package }}/src/

      - name: Lint
        run: uv run ruff check ${{ matrix.package }}/src/

  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --group dev

      - name: Run integration tests
        run: uv run pytest -m integration
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Selective Testing (Performance Optimisation)

**Only test changed packages:**

```bash
# Detect changed packages
CHANGED_PACKAGES=$(git diff --name-only main... | grep -oP 'libs/[^/]+|apps/[^/]+' | sort -u)

# Test only changed
for package in $CHANGED_PACKAGES; do
    uv run pytest $package/tests/
done
```

---

## Implementation Checklists

### Pre-Migration Checklist

**✅ Completed:**
- [x] All tests passing (737 unit tests)
- [x] Type checking passes (basedpyright strict)
- [x] Linting passes (ruff)
- [x] Clean git status (as of commit bc3864e)
- [x] Architectural cleanup completed (Pre-Phase 1)

**⚠️ Status Unknown:**
- [ ] All Features 1-9 merged to main (needs verification)
- [ ] No pending PRs (needs verification)
- [ ] Create formal migration branch: `refactor/monorepo-migration` (if not already on one)
- [ ] Document current import structure

### Pre-Phase 1 Checklist: Architectural Cleanup (COMPLETED)

**✅ All Complete:**
- [x] Made `JsonSchemaLoader` configurable with custom search paths (commit 68079ba)
- [x] Moved `BaseFindingSchema` from waivern-core to WCT layer (commit cac9df8)
- [x] Moved `Analyser` + errors from WCT to waivern-core (commit 1de9b1e)
- [x] Removed re-export file `src/wct/analysers/base.py` (commit 1de9b1e)
- [x] Updated all imports to use `waivern_core` directly (commit 1de9b1e)
- [x] Removed orphaned `BaseFindingSchema` from waivern-core (commit bc3864e)
- [x] Updated waivern-core exports to remove `BaseFindingSchema` (commit bc3864e)
- [x] All 737 tests passing
- [x] Type checking passing (basedpyright strict)
- [x] Linting passing (ruff)
- [x] Dev checks passing
- [x] Committed all changes

**Key Achievements:**
- ✅ Framework independence: waivern-core has zero WCT dependencies
- ✅ Dict-to-typed pattern working: Framework returns dicts, WCT converts to Pydantic models
- ✅ No re-export layers: All imports direct from source packages
- ✅ Clean separation: `BaseFindingSchema` only in WCT where it belongs

### Phase 1 Checklist: waivern-core

**✅ Already Complete (Pre-Phase 1):**
- [x] Create `libs/waivern-core/` directory structure
- [x] Extract `BaseConnector` to `waivern_core/base_connector.py`
- [x] Extract `Analyser` to `waivern_core/base_analyser.py`
- [x] Move `Message` to `waivern_core/message.py`
- [x] Move schema types to `waivern_core/schemas/`
- [x] Update most imports to use `waivern_core`

**⚠️ Remaining Work:**
- [ ] Create formal `libs/waivern-core/pyproject.toml` with proper metadata
- [ ] Extract `BaseRuleset` to `waivern_core/base_ruleset.py`
- [ ] Update workspace config in root `pyproject.toml`
- [ ] Update `BaseRuleset` imports across codebase
- [ ] Run `uv sync` successfully
- [ ] All tests pass (currently 737 passing)
- [ ] Type checking passes (currently passing)
- [ ] Linting passes (currently passing)
- [ ] Commit Phase 1 completion

### Phase 2 Checklist: waivern-llm

- [ ] Create `libs/waivern-llm/` directory structure
- [ ] Create `libs/waivern-llm/pyproject.toml`
- [ ] Move `llm_service.py` to `waivern_llm/`
- [ ] Split into modules (base.py, factory.py, anthropic.py, openai.py)
- [ ] Move tests to `waivern_llm/tests/`
- [ ] Update all imports to use `waivern_llm`
- [ ] Run `uv sync` successfully
- [ ] All tests pass
- [ ] Integration tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Commit Phase 2

### Phase 3 Checklist: waivern-community

- [ ] Create `libs/waivern-community/` directory structure
- [ ] Create `libs/waivern-community/pyproject.toml`
- [ ] Move all connectors to `waivern_community/connectors/`
- [ ] Move all analysers to `waivern_community/analysers/`
- [ ] Move all rulesets to `waivern_community/rulesets/`
- [ ] Move all prompts to `waivern_community/prompts/`
- [ ] Update `__init__.py` exports
- [ ] Move tests to `waivern_community/tests/`
- [ ] Update all imports across codebase
- [ ] Run `uv sync` successfully
- [ ] All tests pass (may take longer)
- [ ] Integration tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Commit Phase 3

### Phase 4 Checklist: Individual Packages (Optional)

For each package (e.g., waivern-mysql):
- [ ] Create `libs/waivern-{name}/` directory
- [ ] Create `pyproject.toml`
- [ ] Copy component from waivern-community
- [ ] Update imports
- [ ] Copy tests
- [ ] Update waivern-community to re-export
- [ ] Run `uv sync` successfully
- [ ] All tests pass
- [ ] Commit

### Phase 5 Checklist: Dynamic Plugin Loading

- [ ] Create `apps/wct/` directory structure
- [ ] Create `apps/wct/pyproject.toml`
- [ ] Move WCT code to `apps/wct/src/wct/`
- [ ] Implement `plugin_loader.py`
- [ ] Update `executor.py` to use PluginLoader
- [ ] Add `source` field to runbook schema
- [ ] Write tests for plugin loading
- [ ] Test loading from community
- [ ] Test loading from standalone package
- [ ] Test error messages for missing packages
- [ ] Run `uv sync` successfully
- [ ] All tests pass
- [ ] Integration tests with dynamic loading pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Commit Phase 5

### Phase 6 Checklist: Contribution Infrastructure

- [ ] Create `docs/contributing/create-connector.md`
- [ ] Create `docs/contributing/create-analyser.md`
- [ ] Create `docs/contributing/create-ruleset.md`
- [ ] Create `docs/contributing/package-publishing.md`
- [ ] Create example template in `docs/examples/custom-connector/`
- [ ] Create example template in `docs/examples/custom-analyser/`
- [ ] Create `scripts/publish-packages.sh`
- [ ] Update main `README.md` with ecosystem overview
- [ ] Update `CLAUDE.md` with monorepo structure
- [ ] Commit Phase 6

### Final Verification Checklist

- [ ] Run full test suite: `uv run pytest`
- [ ] Run integration tests: `uv run pytest -m integration`
- [ ] Run type checking: `uv run basedpyright`
- [ ] Run linting: `uv run ruff check`
- [ ] Run dev checks: `./scripts/dev-checks.sh`
- [ ] Test runbook execution with dynamic loading
- [ ] Test plugin loading from community
- [ ] Test plugin loading from standalone package
- [ ] Verify all imports correct
- [ ] Check no broken imports
- [ ] Review all commit messages
- [ ] Update documentation
- [ ] Create final PR or merge to main

---

## Code Examples

### Example 1: Creating a Custom Connector

**File: `waivern-postgres/src/waivern_postgres/connector.py`**

```python
"""PostgreSQL connector for Waivern Compliance Framework."""

from __future__ import annotations

import logging
from typing import Any

import psycopg2
from waivern_core.base_connector import BaseConnector
from waivern_core.message import Message

logger = logging.getLogger(__name__)


class PostgreSQLConnector(BaseConnector):
    """Connector for PostgreSQL databases."""

    def __init__(
        self,
        host: str,
        port: int = 5432,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        """Initialise PostgreSQL connector.

        Args:
            host: Database host
            port: Database port (default: 5432)
            database: Database name
            user: Database user
            password: Database password
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._connection = None

    def get_output_schema(self) -> str:
        """Return output schema name."""
        return "standard_input"

    def extract(self) -> Message:
        """Extract data from PostgreSQL database.

        Returns:
            Message containing extracted data

        Raises:
            ConnectionError: If connection fails
        """
        logger.info(f"Connecting to PostgreSQL: {self.host}:{self.port}/{self.database}")

        try:
            # Connect to database
            self._connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )

            # Extract schema
            tables = self._extract_tables()
            logger.info(f"Extracted {len(tables)} tables")

            # Create message
            return Message(
                data={"tables": tables},
                metadata={
                    "source": "postgres",
                    "schema": self.get_output_schema(),
                    "database": self.database,
                },
            )

        except Exception as e:
            logger.error(f"Failed to extract from PostgreSQL: {e}")
            raise ConnectionError(f"PostgreSQL extraction failed: {e}") from e

        finally:
            if self._connection:
                self._connection.close()

    def _extract_tables(self) -> list[dict[str, Any]]:
        """Extract table metadata.

        Returns:
            List of table dictionaries
        """
        cursor = self._connection.cursor()

        # Query tables
        cursor.execute("""
            SELECT table_name, table_schema
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_name
        """)

        tables = []
        for table_name, schema in cursor.fetchall():
            # Get columns
            columns = self._extract_columns(table_name, schema)

            tables.append({
                "name": table_name,
                "schema": schema,
                "columns": columns,
            })

        return tables

    def _extract_columns(self, table_name: str, schema: str) -> list[dict[str, Any]]:
        """Extract column metadata for a table.

        Args:
            table_name: Table name
            schema: Schema name

        Returns:
            List of column dictionaries
        """
        cursor = self._connection.cursor()

        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """, (table_name, schema))

        columns = []
        for column_name, data_type, is_nullable in cursor.fetchall():
            columns.append({
                "name": column_name,
                "type": data_type,
                "nullable": is_nullable == "YES",
            })

        return columns
```

### Example 2: Creating a Custom Analyser

**File: `acme-compliance/src/acme_compliance/analyser.py`**

```python
"""Custom compliance analyser for ACME Corp."""

from __future__ import annotations

import logging
from typing import Any

from waivern_core.base_analyser import BaseAnalyser
from waivern_core.message import Message

logger = logging.getLogger(__name__)


class ACMEComplianceAnalyser(BaseAnalyser):
    """Analyser for ACME Corp compliance requirements."""

    def __init__(self, ruleset: str = "standard", threshold: float = 0.8):
        """Initialise ACME compliance analyser.

        Args:
            ruleset: Ruleset to use ("standard", "strict", "relaxed")
            threshold: Confidence threshold for findings
        """
        self.ruleset = ruleset
        self.threshold = threshold

    def get_input_schema(self) -> str:
        """Return input schema name."""
        return "standard_input"

    def get_output_schema(self) -> str:
        """Return output schema name."""
        return "acme_compliance_findings"

    def process_data(self, message: Message) -> Message:
        """Analyse data for ACME compliance.

        Args:
            message: Input message with data to analyse

        Returns:
            Message with compliance findings
        """
        logger.info(f"Analysing with ACME ruleset: {self.ruleset}")

        # Extract data
        tables = message.data.get("tables", [])

        # Analyse each table
        findings = []
        for table in tables:
            table_findings = self._analyse_table(table)
            findings.extend(table_findings)

        logger.info(f"Found {len(findings)} compliance findings")

        # Create output message
        return Message(
            data={
                "findings": findings,
                "summary": {
                    "total_findings": len(findings),
                    "ruleset": self.ruleset,
                    "threshold": self.threshold,
                },
            },
            metadata={
                "analyser": "acme_compliance",
                "schema": self.get_output_schema(),
            },
        )

    def _analyse_table(self, table: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyse a single table for compliance issues.

        Args:
            table: Table dictionary

        Returns:
            List of findings
        """
        findings = []

        # Check for sensitive data
        for column in table.get("columns", []):
            if self._is_sensitive_column(column):
                findings.append({
                    "type": "sensitive_data",
                    "table": table["name"],
                    "column": column["name"],
                    "severity": "high",
                    "recommendation": "Encrypt or mask sensitive data",
                })

        return findings

    def _is_sensitive_column(self, column: dict[str, Any]) -> bool:
        """Check if column contains sensitive data.

        Args:
            column: Column dictionary

        Returns:
            True if column is sensitive
        """
        sensitive_keywords = ["ssn", "credit_card", "password", "secret", "api_key"]
        column_name = column["name"].lower()

        return any(keyword in column_name for keyword in sensitive_keywords)
```

### Example 3: Using Remote Analyser (Future)

**File: `waivern_core/remote_analyser.py`**

```python
"""Remote analyser protocol implementation."""

from __future__ import annotations

import logging
from typing import Any

import requests
from waivern_core.base_analyser import BaseAnalyser
from waivern_core.message import Message

logger = logging.getLogger(__name__)


class RemoteAnalyser(BaseAnalyser):
    """Analyser that calls remote API endpoint."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout: int = 30,
        retry: int = 3,
    ):
        """Initialise remote analyser.

        Args:
            endpoint: Remote API endpoint URL
            api_key: API authentication key
            timeout: Request timeout in seconds
            retry: Number of retry attempts
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.retry = retry

    def get_input_schema(self) -> str:
        """Return input schema name."""
        # Query remote endpoint for schema
        response = requests.get(
            f"{self.endpoint}/schema",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        return response.json()["input_schema"]

    def get_output_schema(self) -> str:
        """Return output schema name."""
        response = requests.get(
            f"{self.endpoint}/schema",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        return response.json()["output_schema"]

    def process_data(self, message: Message) -> Message:
        """Send data to remote analyser for processing.

        Args:
            message: Input message with data to analyse

        Returns:
            Message with analysis results from remote service

        Raises:
            requests.RequestException: If remote call fails
        """
        logger.info(f"Sending data to remote analyser: {self.endpoint}")

        # Prepare request
        request_data = {
            "data": message.data,
            "schema": message.metadata.get("schema"),
        }

        # Send with retry logic
        for attempt in range(self.retry):
            try:
                response = requests.post(
                    f"{self.endpoint}/analyse",
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()

                # Parse response
                result = response.json()
                logger.info("Received response from remote analyser")

                return Message(
                    data=result,
                    metadata={
                        "analyser": "remote",
                        "endpoint": self.endpoint,
                        "schema": self.get_output_schema(),
                    },
                )

            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.retry} failed: {e}")
                if attempt == self.retry - 1:
                    logger.error("All retry attempts failed")
                    raise

        raise RuntimeError("Unexpected: should not reach here")
```

---

## Migration Timeline

**Recommended schedule (post-Feature 9):**

| Week | Phase | Focus |
|------|-------|-------|
| Week 1 | Phase 0-1 | Pre-work + waivern-core |
| Week 2 | Phase 2-3 | waivern-llm + waivern-community |
| Week 3 | Phase 4-5 | Individual packages + plugin loading |
| Week 4 | Phase 6 | Contribution infrastructure + docs |

**Total: ~4 weeks part-time** or **~1 week full-time**

---

## Success Criteria

**Pre-Phase 1 Complete (✅):**
- ✅ Framework architectural cleanup complete
- ✅ waivern-core has zero WCT dependencies
- ✅ All 737 unit tests pass
- ✅ Type checking passes (basedpyright strict)
- ✅ Linting passes (ruff)

**Full Migration Complete When:**
- [ ] All packages in workspace structure
- [ ] Workspace configuration in root pyproject.toml
- [ ] All 737+ unit tests pass
- [ ] All integration tests pass
- [ ] Type checking passes (basedpyright strict)
- [ ] Linting passes (ruff)
- [ ] Dynamic plugin loading works
- [ ] Can load from waivern-community
- [ ] Can load from standalone package
- [ ] Documentation complete
- [ ] Example templates created
- [ ] Publishing scripts ready

---

## Rollback Plan

If migration encounters critical issues:

1. **Keep migration branch** - Don't delete
2. **Revert to main** - Use stable version
3. **Document issues** - Learn for next attempt
4. **Plan fixes** - Address blockers
5. **Retry when ready** - Migration branch preserved

**Low risk because:**
- Each phase is committed separately
- Can rollback to any phase
- All tests verify correctness at each step
- No breaking changes to external APIs

---

## Future Enhancements

### Post-Migration Roadmap

1. **Remote component registry** (3-4 weeks)
   - Registry service for package discovery
   - Rating/review system
   - Usage analytics

2. **Remote analyser protocol** (2-3 weeks)
   - API specification
   - Authentication/authorization
   - SDK for building remote services

3. **Waivern Web UI** (6-8 weeks)
   - Reuse all waivern-* packages
   - Web-based runbook editor
   - Results visualisation

4. **Waivern API** (3-4 weeks)
   - REST API wrapper around executor
   - Job queue for async execution
   - Webhook notifications

5. **Waivern SDK** (2-3 weeks)
   - Programmatic API for Python
   - Create runbooks in code
   - Embedded compliance checks

---

## Questions & Answers

### Q: Should we extract individual packages immediately?

**A:** No, start with waivern-community. Extract individual packages only when:
- User requests minimal dependencies
- Component becomes popular standalone
- Third party wants to maintain it

### Q: How do users know which packages to install?

**A:** Error messages guide them:
```
Failed to load 'postgres' connector.
Install: uv add waivern-community
Or: uv add waivern-postgres
```

### Q: What if a component is in both community and standalone?

**A:** Community package re-exports from standalone if installed, otherwise uses bundled version.

### Q: How do we handle breaking changes in core?

**A:** Version compatibility matrix in documentation:
```
waivern-core 0.2.x → waivern-community 0.2.x, waivern-mysql 0.2.x
waivern-core 0.3.x → waivern-community 0.3.x, waivern-mysql 0.3.x
```

### Q: Can users create connectors without publishing?

**A:** Yes, local packages work:
```yaml
source: "package:my_local_connector"
```
Just needs to be in Python path or installed with `uv add -e /path/to/connector`

---

## Resources

### Documentation
- LangChain monorepo: https://github.com/langchain-ai/langchain
- uv workspaces: https://docs.astral.sh/uv/concepts/workspaces/
- Python packaging: https://packaging.python.org/

### Tools
- uv: https://astral.sh/uv
- Hatchling: https://hatch.pypa.io/
- pytest: https://pytest.org/

### Examples
- LangChain partner packages: https://python.langchain.com/docs/integrations/
- Pydantic monorepo: https://github.com/pydantic/pydantic
- FastAPI monorepo: https://github.com/tiangolo/fastapi

---

## Conclusion

This migration transforms the Waivern Compliance Tool into the **Waivern Compliance Framework** - a comprehensive, extensible ecosystem for compliance analysis.

**Key benefits:**
1. ✅ Clear architecture with reusable components
2. ✅ Easy for third parties to contribute
3. ✅ Dynamic plugin system for flexibility
4. ✅ Foundation for platform-as-a-service model
5. ✅ Scales to multiple tools (CLI, Web, API)

**Next steps:**
1. Complete Features 4-9 of multi-provider LLM support
2. Review and refine this plan
3. Execute migration phases sequentially
4. Build ecosystem on solid foundation

**Ready to execute post-Feature 9!** 🚀
