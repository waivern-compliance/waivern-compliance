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
│   ├── waivern-sqlite/            # SQLite connector (standalone)
│   ├── waivern-filesystem/        # Filesystem connector (standalone)
│   ├── waivern-source-code/       # Source code connector (standalone)
│   ├── waivern-rulesets/          # Shared rulesets (standalone)
│   ├── waivern-analysers-shared/  # Shared analyser utilities (standalone)
│   ├── waivern-personal-data-analyser/  # Personal data analyser (standalone)
│   ├── waivern-data-subject-analyser/  # Data subject analyser (standalone)
│   ├── waivern-processing-purpose-analyser/  # Processing purpose analyser (standalone)
│   ├── waivern-data-export-analyser/  # Data export analyser (work in progress)
│   ├── waivern-orchestration/     # Runbook parsing, planning, and DAG execution
│   └── waivern-artifact-store/    # In-memory artifact storage for execution
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
- **waivern-sqlite**: SQLite connector (standalone package)
- **waivern-filesystem**: Filesystem connector for reading files and directories (standalone package)
- **waivern-source-code**: Source code connector for PHP analysis (standalone package)
- **waivern-rulesets**: Shared rulesets for pattern-based analysis (PersonalDataRuleset, ProcessingPurposesRuleset, etc.)
- **waivern-analysers-shared**: Shared utilities for analysers (RulesetManager, EvidenceExtractor, LLM validation strategies, etc.)
- **waivern-personal-data-analyser**: Personal data analyser (standalone package for minimal dependencies)
- **waivern-data-subject-analyser**: Data subject analyser (standalone package)
- **waivern-processing-purpose-analyser**: Processing purpose analyser (standalone package, supports both standard input and source code analysis)
- **waivern-data-export-analyser**: Data export analyser with TCF vendor database (work in progress, not yet functional)
- **waivern-orchestration**: Runbook parsing, execution planning (DAG), and parallel artifact execution
- **waivern-artifact-store**: In-memory artifact storage for inter-artifact data passing during execution

**Applications:**
- **wct**: CLI tool that orchestrates compliance analysis by executing YAML runbooks using framework components

## How the Framework Works

### Core WCF Concepts

1. **Connectors** - Extract data from sources (databases, files, APIs) and transform to WCF schemas
2. **Analysers** - Pure functions that process schema-validated data and produce compliance findings
3. **Rulesets** - YAML-based pattern definitions for static compliance analysis
4. **Schemas** - JSON Schema contracts that define component communication
5. **Runbooks** - YAML configurations defining artifacts and their dependencies (like Infrastructure as Code)
6. **Orchestration** - Planner resolves dependencies and schemas; DAGExecutor runs artifacts in parallel

### Data Flow

```
Runbook (YAML) → Planner → DAGExecutor → Connector/Analyser → Findings (JSON)
```

1. User writes a runbook defining artifacts (sources and transformations)
2. Planner parses runbook, builds execution DAG, resolves schemas
3. DAGExecutor runs artifacts in dependency order (parallel where possible)
4. Connectors extract data; Analysers transform data
5. Data flows through Message objects (automatic schema validation)
6. Results are output as JSON files

### Schema-Driven Architecture

The framework is **schema-driven**:
- Components declare input/output schemas
- Executor automatically matches schemas between connectors and analysers
- Message objects provide automatic validation at runtime
- JSON Schema files define structure and validation rules

**Schema Ownership:**
- **Shared schemas** (StandardInputSchema, BaseFindingSchema) → waivern-core
- **Component-specific schemas** → co-located with components (standalone packages)
- **Application schemas** (runbook config, analysis output) → wct

**Examples:**
- PersonalDataFindingSchema → waivern-personal-data-analyser (standalone)
- ProcessingPurposeFindingSchema → waivern-processing-purpose-analyser (standalone)
- DataSubjectFindingSchema → waivern-data-subject-analyser (standalone)

## Development Commands

This project uses `uv` for dependency management.

### Workspace-Level Commands

**Testing:**
```bash
uv run pytest                       # Run all tests
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
cd libs/waivern-personal-data-analyser && ./scripts/format.sh
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

**See:** [docs/how-tos/configuration.md](docs/how-tos/configuration.md) for complete documentation.

## Runbook Format

Runbooks use an artifact-centric format where each artifact is either a source (data extraction) or derived (transformation):

```yaml
name: "Runbook Name"
description: "What this runbook analyses"
contact: "Contact Person <email@company.com>"

artifacts:
  # Source artifact - extracts data
  file_content:
    source:
      type: "filesystem"
      properties:
        path: "./sample_file.txt"

  # Derived artifact - transforms data
  personal_data_findings:
    inputs: file_content
    transform:
      type: "personal_data"
      properties:
        pattern_matching:
          ruleset: "personal_data"
    output: true  # Include in final output
```

**Key concepts:**
- **Source artifacts** use `source` to extract data via connectors
- **Derived artifacts** use `inputs` + `transform` to process upstream data
- **`output: true`** marks artifacts for inclusion in results
- Dependencies determine execution order (parallel where possible)

**Sample Runbooks:**
- `apps/wct/runbooks/samples/file_content_analysis.yaml` - Simple file analysis
- `apps/wct/runbooks/samples/LAMP_stack.yaml` - Comprehensive MySQL + PHP analysis
- See `apps/wct/runbooks/README.md` for detailed documentation

## Architecture Details

### Framework Independence

The framework libraries are independent:
- **waivern-core** - No dependencies on WCT or other packages
- **waivern-llm** - Depends only on waivern-core, no WCT dependencies
- **Component packages** - Each standalone package depends only on waivern-core and necessary shared utilities
- **wct** - Application that discovers and uses framework components via entry points

This enables:
- Independent versioning and releases
- Other applications can use the framework
- Clear separation of concerns
- True plugin architecture with zero hardcoded dependencies

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

### Component Architecture

**Dependency Injection System:**
- Components instantiated via `ComponentFactory` pattern
- `ServiceContainer` manages singleton services (e.g., LLM services)
- Executor holds factories, not component classes
- Configuration via dedicated Config classes (Pydantic models)

**Component Registry:**
- Components register automatically via metaclass
- Executor discovers component factories by type name
- Tests use `isolated_registry` fixture for proper isolation

### Shared Utilities vs Services

**Architecture Decision:** Database utilities (waivern-connectors-database) remain a **shared library**, not a service.

**When to use Services (via ServiceContainer):**
- Stateful components requiring lifecycle management
- Multiple implementations of same interface
- Runtime configuration needed
- External system connections (API clients, database pools)
- Examples: LLM services (API clients, retry logic, rate limiting)

**When to use Shared Libraries (direct imports):**
- Stateless pure functions with no side effects
- Single implementation, no polymorphism needed
- No runtime configuration required
- No lifecycle management needed
- Examples: Database extraction utilities, schema utilities, evidence extractors

**Database utilities characteristics:**
- Pure functions: `extract_data(conn, query) → dict`
- No state, no configuration, no lifecycle
- Single implementation (no need for polymorphism)
- Used in hot path (performance-sensitive)

**Why not convert to service:**
- Would add ~110 LOC infrastructure for 134 LOC utilities
- Violates YAGNI principle (no current need for DI features)
- Performance overhead (DI resolution) unjustified
- Industry patterns (Django utils, Spring utils, Apache Commons) support shared library approach

**Result:** Stateless pure functions belong in shared libraries. Services are for stateful infrastructure requiring lifecycle management.

## Core Concepts Documentation

**See:** [docs/core-concepts/wcf-core-components.md](docs/core-concepts/wcf-core-components.md) for detailed framework concepts.

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

- All packages have comprehensive test coverage
- Integration tests marked with `@pytest.mark.integration` (require API keys)
- Run `uv run pytest` before committing
- Type checking in strict mode (basedpyright)
- Tests use `isolated_registry` fixture for component registry isolation

## Important Development Notes

### Component Implementation

**When creating connectors:**
- Implement `get_supported_output_schemas()` returning `list[Schema]`
- Transform extracted data to match declared schema
- Return Message objects from `extract()` method
- Create a `ComponentFactory[Connector]` for instantiation
- Configuration via dedicated Config class (Pydantic model)

**When creating analysers:**
- Implement `get_input_requirements()` returning `list[list[InputRequirement]]` (declares supported input combinations)
- Implement `get_supported_output_schemas()` returning `list[Schema]`
- Implement `process(inputs: list[Message], output_schema: Schema) -> Message`
- NO need to implement validation - handled by Message mechanism
- Create a `ComponentFactory[Analyser]` for instantiation
- Configuration via dedicated Config class (Pydantic model)
- Use `@override` decorators for abstract methods
- Inherit test class from `AnalyserContractTests` for automatic contract validation

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

### Task Completion Requirements

**CRITICAL: You MUST run `./scripts/dev-checks.sh` before marking ANY task as completed.**

When using TodoWrite to track tasks:
1. Mark task as `in_progress` when you start working on it
2. Make your code changes
3. **ALWAYS run `./scripts/dev-checks.sh` to verify all checks pass**
4. **ONLY AFTER dev-checks pass**, mark task as `completed`
5. Move to next task

**NEVER mark a task as completed without running dev-checks first.** This is non-negotiable.

### DO NOT

- Commit directly to `main` or `master` - always use feature branches
- Create backwards compatibility layers unless explicitly asked
- Preserve old context in comments during refactoring
- Attempt to bypass quality checks
- Use quick fixes for design flaws - advise on refactoring instead
- **Mark any task as completed without running dev-checks first**

### DO

- What has been asked - nothing more, nothing less
- Analyse and remove unnecessary code after refactoring
- Break large classes/functions into smaller, focused ones
- Carefully analyse errors to determine root cause
- Use conventional commits for all commits and PRs
- **Run `./scripts/dev-checks.sh` before marking each task as completed**

## Git and PR Requirements

**Branch Naming (Conventional Commits):**
- `feature/feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/documentation-updates` - Documentation changes
- `refactor/component-name` - Refactoring work

**NEVER commit directly to `main` or `master`** - always create a branch first.

## Additional Resources

- **[README.md](README.md)** - Project overview and quick start
- **[docs/core-concepts/wcf-core-components.md](docs/core-concepts/wcf-core-components.md)** - Framework concepts
- **[docs/how-tos/configuration.md](docs/how-tos/configuration.md)** - Configuration guide
- **[docs/roadmaps/monorepo-migration/monorepo-migration-completed.md](docs/roadmaps/monorepo-migration/monorepo-migration-completed.md)** - Migration history
- **[apps/wct/runbooks/README.md](apps/wct/runbooks/README.md)** - Runbook documentation
