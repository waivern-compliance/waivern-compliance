# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Waivern Compliance Framework (WCF)** - an open-source framework for compliance analysis across any technology stack and compliance regulation (GDPR, ePrivacy, EU AI Act, NIS2, DORA, etc.).

The repository is organised as a **monorepo** with framework libraries and applications.

## Monorepo Structure

```
waivern-compliance/
├── libs/                           # Framework libraries
│   ├── waivern-core/              # Core abstractions (Connector, Analyser, Schema, Message)
│   ├── waivern-llm/               # Multi-provider LLM abstraction (Anthropic, OpenAI, Google)
│   ├── waivern-connectors-database/  # Shared SQL connector utilities
│   ├── waivern-mysql/             # MySQL connector (standalone)
│   ├── waivern-rulesets/          # Shared rulesets (standalone)
│   ├── waivern-analysers-shared/  # Shared analyser utilities (standalone)
│   ├── waivern-personal-data-analyser/  # Personal data analyser (standalone)
│   └── waivern-community/         # SQLite + other connectors, analysers, prompts
└── apps/                           # Applications
    └── wct/                        # Waivern Compliance Tool (CLI application)
        ├── .env                    # App-specific configuration
        ├── config/                 # Organisation configuration
        ├── runbooks/               # Runbook configurations
        │   └── samples/            # Sample runbooks
        ├── src/wct/                # WCT application code
        └── tests/                  # Application tests
```

### Package Descriptions

**Framework Libraries:**
- **waivern-core**: Base abstractions that all components implement (Connector, Analyser, Message, Schema, Ruleset)
- **waivern-llm**: Multi-provider LLM service with lazy loading for optional providers (zero WCT dependencies)
- **waivern-connectors-database**: Shared SQL connector utilities (DatabaseConnector, DatabaseExtractionUtils, DatabaseSchemaUtils)
- **waivern-mysql**: MySQL connector (standalone package for minimal dependencies)
- **waivern-rulesets**: Shared rulesets for pattern-based analysis (PersonalDataRuleset, ProcessingPurposesRuleset, etc.)
- **waivern-analysers-shared**: Shared utilities for analysers (LLMServiceManager, RulesetManager, EvidenceExtractor, etc.)
- **waivern-personal-data-analyser**: Personal data analyser (standalone package for minimal dependencies)
- **waivern-community**: Built-in connectors (SQLite, Filesystem, SourceCode), analysers (ProcessingPurpose, DataSubject), and prompts (re-exports standalone packages for convenience)

**Applications:**
- **wct**: CLI tool that orchestrates compliance analysis by executing YAML runbooks using framework components

## How the Framework Works

### Core WCF Concepts

1. **Connectors** - Extract data from sources (databases, files, APIs) and transform to WCF schemas
2. **Analysers** - Pure functions that process schema-validated data and produce compliance findings
3. **Rulesets** - YAML-based pattern definitions for static compliance analysis
4. **Schemas** - JSON Schema contracts that define component communication
5. **Runbooks** - YAML configurations defining what to analyse and how (like Infrastructure as Code)
6. **Executor** - Orchestrates runbook execution (lives in WCT application)

### Data Flow

```
Runbook (YAML) → Executor → Connector → Schema Validation → Analyser → Findings (JSON)
```

1. User writes a runbook specifying connectors, analysers, and execution steps
2. WCT Executor loads the runbook and validates configuration
3. Connectors extract data and transform to WCF schemas
4. Data flows through Message objects (automatic schema validation)
5. Analysers process data using rulesets and/or LLM validation
6. Results are output as JSON files

### Schema-Driven Architecture

The framework is **schema-driven**:
- Components declare input/output schemas
- Executor automatically matches schemas between connectors and analysers
- Message objects provide automatic validation at runtime
- JSON Schema files define structure and validation rules

**Schema Ownership:**
- **Shared schemas** (StandardInputSchema, BaseFindingSchema) → waivern-core
- **Component-specific schemas** → co-located with components (standalone packages or waivern-community)
- **Application schemas** (runbook config, analysis output) → wct

**Examples:**
- PersonalDataFindingSchema → waivern-personal-data-analyser (standalone)
- ProcessingPurposeFindingSchema → waivern-community
- DataSubjectFindingSchema → waivern-community

## Development Commands

This project uses `uv` for dependency management.

### Workspace-Level Commands

**Testing:**
```bash
uv run pytest                       # Run all tests (752 tests)
uv run pytest -v                    # Verbose output
uv run pytest -m integration        # Run integration tests (requires API keys)
```

**Quality Checks (Package-Centric):**
```bash
./scripts/lint.sh                   # Lint all packages
./scripts/format.sh                 # Format all packages
./scripts/type-check.sh             # Type check all packages
./scripts/dev-checks.sh             # Run all checks + tests
```

**Pre-commit:**
```bash
uv run pre-commit install           # Install hooks (once)
uv run pre-commit run --all-files   # Run all hooks manually
```

### Package-Level Commands

Each package can be checked independently:

```bash
# Check individual packages
cd libs/waivern-core && ./scripts/lint.sh
cd libs/waivern-llm && ./scripts/type-check.sh
cd libs/waivern-community && ./scripts/format.sh
cd apps/wct && ./scripts/dev-checks.sh
```

### WCT Application Commands

```bash
# Run compliance analysis
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v

# List available components
uv run wct ls-connectors
uv run wct ls-analysers

# Validate runbook
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml

# Test LLM configuration
uv run wct test-llm

# Generate JSON Schema
uv run wct generate-schema
```

**Logging Options:**
- `--log-level DEBUG` or `-v` - Detailed debugging
- `--log-level INFO` - Default informational messages
- `--log-level WARNING` - Warnings and errors only

## Workspace Configuration

The monorepo uses UV workspaces with auto-discovery for package members.

**Root `pyproject.toml` structure:**

```toml
[tool.uv.workspace]
members = [
    "libs/*",     # Auto-discovers all packages in libs/
    "apps/*",     # Auto-discovers all packages in apps/
]

[tool.uv.sources]
# Each workspace member used as a dependency must be explicitly declared
# These definitions are inherited by all workspace members
waivern-core = { workspace = true }
waivern-llm = { workspace = true }
# ... etc for all workspace packages
```

**Key points:**

1. **Workspace members:** Use glob patterns (`libs/*`, `apps/*`) for auto-discovery
   - Any directory with a `pyproject.toml` is automatically included
   - No manual updates needed when adding new packages

2. **Workspace sources:** Must be explicitly declared for each package
   - Required for dependency resolution across workspace members
   - Cannot use glob patterns (mapping structure)
   - Must be updated manually when adding new packages

3. **Workspace scripts:** Auto-discover packages and run in parallel
   - `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh` discover all packages
   - Run package checks in parallel (packages are truly independent!)
   - No manual updates needed when adding new packages

4. **Pre-commit scripts:** Auto-discover packages and group changed files
   - `scripts/pre-commit-*.sh` dynamically find packages and group files
   - No manual updates needed when adding new packages

**Adding a new package:**
1. Create package directory in `libs/` or `apps/` with `pyproject.toml`
2. Ensure package has standard scripts: `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`
3. Add entry to `[tool.uv.sources]` in root `pyproject.toml` (if used as dependency)
4. Run `uv sync` to register the new package
5. That's it! Workspace and pre-commit scripts will auto-discover it

## Environment Configuration

Applications own configuration. WCT configuration is in `apps/wct/.env`.

**Quick Start:**
```bash
cp apps/wct/.env.example apps/wct/.env
# Edit apps/wct/.env with your API keys
uv run wct test-llm  # Verify configuration
```

**Configuration Layers (highest to lowest priority):**
1. System environment variables (production)
2. Application `.env` file (`apps/wct/.env` for local development)
3. Runbook properties (YAML configuration)
4. Code defaults

**Common Environment Variables:**
- `ANTHROPIC_API_KEY` - Anthropic API key for LLM validation
- `ANTHROPIC_MODEL` - Model name (optional, defaults to claude-sonnet-4-5-20250929)
- `LLM_PROVIDER` - Provider selection (anthropic, openai, google)
- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` - MySQL connector configuration

**See:** [docs/configuration.md](docs/configuration.md) for complete documentation.

## Runbook Format

Runbooks are YAML files that define compliance analysis pipelines:

```yaml
name: "Runbook Name"
description: "What this runbook analyses"
contact: "Contact Person <email@company.com>"

connectors:
  - name: "filesystem_reader"
    type: "filesystem"
    properties:
      path: "./sample_file.txt"

analysers:
  - name: "content_analyser"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        ruleset: "personal_data"
        evidence_context_size: "medium"
      llm_validation:
        enable_llm_validation: true

execution:
  - name: "Analyse file content"
    connector: "filesystem_reader"
    analyser: "content_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
```

**Sample Runbooks:**
- `apps/wct/runbooks/samples/file_content_analysis.yaml` - Simple file analysis
- `apps/wct/runbooks/samples/LAMP_stack.yaml` - Comprehensive MySQL + PHP analysis
- See `apps/wct/runbooks/README.md` for detailed documentation

## Architecture Details

### Framework Independence

The framework libraries are independent:
- **waivern-core** - No dependencies on WCT or other packages
- **waivern-llm** - Depends only on waivern-core, no WCT dependencies
- **waivern-community** - Depends on waivern-core and waivern-llm, no WCT dependencies
- **wct** - Application that uses all framework libraries

This enables:
- Independent versioning and releases
- Other applications can use the framework
- Clear separation of concerns

### Package-Centric Quality Checks

Each package owns its quality tool configuration:
- Tool configs (basedpyright, ruff) in package `pyproject.toml`
- Package-specific scripts in `{package}/scripts/`
- Workspace scripts orchestrate package checks
- Pre-commit hooks process files by package

### Message-Based Validation

All data flow uses Message objects:
- Connectors return Message objects with schema-validated data
- Analysers receive and return Message objects
- Automatic validation against declared schemas
- No manual validation needed in analyser implementations

### Component Registry

Components register automatically:
- Connectors and analysers register via metaclass
- Executor discovers components by type name
- Tests use `isolated_registry` fixture for proper isolation

## Core Concepts Documentation

**See:** [docs/wcf_core_concepts.md](docs/wcf_core_concepts.md) for detailed framework concepts.

**Key principles:**
- **Schema-driven:** Components communicate through JSON Schema contracts
- **Component ownership:** Components own their data contracts (schemas co-located)
- **Pure functions:** Analysers behave like pure functions (input schema → output schema)
- **Modularity:** Connectors don't know about analysers and vice versa
- **Extensibility:** New components implement base abstractions

## Development Workflow

### Making Changes

1. **Create feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes in appropriate package:**
   - Framework abstractions → `libs/waivern-core/`
   - LLM functionality → `libs/waivern-llm/`
   - Rulesets → `libs/waivern-rulesets/`
   - Shared analyser utilities → `libs/waivern-analysers-shared/`
   - Standalone components → `libs/waivern-{component-name}/`
   - Community components → `libs/waivern-community/`
   - Application logic → `apps/wct/`

3. **Run quality checks:**
   ```bash
   ./scripts/dev-checks.sh
   ```

4. **Commit using conventional commits:**
   ```bash
   git commit -m "feat: add new connector for PostgreSQL"
   git commit -m "fix: resolve schema validation error"
   git commit -m "docs: update runbook documentation"
   ```

### Testing Guidelines

- All packages have comprehensive test coverage (752 tests total)
- Integration tests marked with `@pytest.mark.integration` (require API keys)
- Run `uv run pytest` before committing
- Type checking in strict mode (basedpyright)
- Tests use `isolated_registry` fixture for component registry isolation

## Important Development Notes

### Schema Implementation

**When creating connectors:**
- Implement `get_output_schema()` returning `WctSchema[T]`
- Transform extracted data to match declared schema
- Return Message objects from `extract()` method

**When creating analysers:**
- Implement `get_input_schema()` and `get_output_schema()`
- Implement `process_data(message: Message) -> Message`
- NO need to implement validation - handled by Message mechanism
- Use `@override` decorators for abstract methods

**Schema files:**
- JSON Schema files in `{package}/schemas/json_schemas/{name}/{version}/{name}.json`
- Versioned directory structure
- Runtime discovery from multiple search paths

### Code Quality Standards

- Type annotations required (basedpyright strict mode)
- Code formatting with ruff
- Security checks with bandit
- British English spelling
- No unused imports or variables
- Comprehensive docstrings

**Modern Python Features (Python 3.12+):**
- Use PEP 695 generic syntax: `def func[T](x: T) -> T:` instead of `TypeVar`
- Use PEP 695 for generic classes: `class Container[T]:` instead of `Generic[T]`
- Use `type` statement for type aliases: `type Point[T] = tuple[T, T]`
- Use structural pattern matching (match/case) where appropriate
- Use modern syntax features when they improve readability and type safety
- Always consider the latest Python best practices and idioms

### DO NOT

- Commit directly to `main` or `master` - always use feature branches
- Create backwards compatibility layers unless explicitly asked
- Preserve old context in comments during refactoring
- Attempt to bypass quality checks
- Use quick fixes for design flaws - advise on refactoring instead

### DO

- What has been asked - nothing more, nothing less
- Analyse and remove unnecessary code after refactoring
- Break large classes/functions into smaller, focused ones
- Carefully analyse errors to determine root cause
- Use conventional commits for all commits and PRs
- Run `./scripts/dev-checks.sh` after each task

## Git and PR Requirements

**Branch Naming (Conventional Commits):**
- `feature/feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/documentation-updates` - Documentation changes
- `refactor/component-name` - Refactoring work

**NEVER commit directly to `main` or `master`** - always create a branch first.

## Additional Resources

- **[README.md](README.md)** - Project overview and quick start
- **[docs/wcf_core_concepts.md](docs/wcf_core_concepts.md)** - Framework concepts
- **[docs/configuration.md](docs/configuration.md)** - Configuration guide
- **[docs/architecture/monorepo-migration-completed.md](docs/architecture/monorepo-migration-completed.md)** - Migration history
- **[apps/wct/runbooks/README.md](apps/wct/runbooks/README.md)** - Runbook documentation
