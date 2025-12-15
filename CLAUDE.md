# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

**Waivern Compliance Framework (WCF)** - Open-source framework for compliance analysis (GDPR, ePrivacy, EU AI Act, NIS2, DORA, etc.).

**Monorepo structure:**
```
waivern-compliance/
├── libs/                              # Framework libraries
│   ├── waivern-core/                  # Base abstractions (Connector, Analyser, Schema, Message)
│   ├── waivern-llm/                   # Multi-provider LLM abstraction
│   ├── waivern-orchestration/         # Runbook parsing, flattening, DAG execution
│   ├── waivern-artifact-store/        # In-memory artifact storage
│   ├── waivern-connectors-database/   # Shared SQL utilities
│   ├── waivern-mysql/                 # MySQL connector
│   ├── waivern-sqlite/                # SQLite connector
│   ├── waivern-filesystem/            # Filesystem connector
│   ├── waivern-source-code/           # Source code connector (PHP)
│   ├── waivern-rulesets/              # Pattern-based rulesets
│   ├── waivern-analysers-shared/      # Shared analyser utilities
│   ├── waivern-personal-data-analyser/
│   ├── waivern-data-subject-analyser/
│   ├── waivern-processing-purpose-analyser/
│   └── waivern-data-export-analyser/  # Work in progress
└── apps/
    └── wct/                           # CLI application
        ├── runbooks/samples/          # Sample runbooks
        └── .env                       # App configuration
```

## Core Concepts

```
Runbook (YAML) → Planner → DAGExecutor → Connector/Processor → Findings (JSON)
```

1. **Connectors** - Extract data from sources, output schema-validated Messages
2. **Processors** - Transform data, declare input requirements via `InputRequirement`
3. **Runbooks** - YAML defining artifacts and dependencies
4. **Planner** - Parses runbook, flattens child runbooks, builds DAG, validates schemas
5. **DAGExecutor** - Runs artifacts in parallel where possible

**Schema-driven:** Components declare schemas; Message objects validate automatically.

## Runbook Format

```yaml
name: "Runbook Name"
description: "Description"

artifacts:
  # Source artifact
  file_content:
    source:
      type: "filesystem"
      properties:
        path: "./sample.txt"

  # Derived artifact
  findings:
    inputs: file_content
    process:
      type: "personal_data"
      properties:
        pattern_matching:
          ruleset: "personal_data"
    output: true
```

- **Source artifacts**: `source` → connector extracts data
- **Derived artifacts**: `inputs` + `process` → processor transforms data
- **`output: true`**: Include in final results

**Samples:** `apps/wct/runbooks/samples/`

## Development Commands

```bash
# Quality checks (ALWAYS run before completing tasks)
./scripts/dev-checks.sh             # All checks + tests

# Individual checks
./scripts/lint.sh && ./scripts/format.sh && ./scripts/type-check.sh

# Testing
uv run pytest                       # All tests
uv run pytest -m integration        # Integration tests (requires API keys)

# WCT CLI
uv run wct run <runbook.yaml>       # Run analysis
uv run wct run <runbook.yaml> -v    # Verbose
uv run wct ls-connectors            # List connectors
uv run wct ls-processors            # List processors
uv run wct validate-runbook <file>  # Validate runbook
uv run wct test-llm                 # Test LLM config
```

## Component Implementation

**Connectors:**
```python
@classmethod
def get_supported_output_schemas(cls) -> list[Schema]: ...
def extract(self, output_schema: Schema) -> Message: ...
```

**Processors (Analysers):**
```python
@classmethod
def get_input_requirements(cls) -> list[list[InputRequirement]]:
    return [[InputRequirement("standard_input", "1.0.0")]]

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]: ...

def process(self, inputs: list[Message], output_schema: Schema) -> Message: ...
```

- Use `ComponentFactory[T]` for instantiation
- Configuration via Pydantic Config classes
- Inherit from `AnalyserContractTests` for automatic contract validation
- Use `@override` decorators for abstract methods

**Schema files:** `{package}/schemas/json_schemas/{name}/{version}/{name}.json`

## Code Standards

- **Type annotations required** (basedpyright strict mode)
- **Formatting:** ruff
- **British English** spelling
- **Python 3.12+:** Use PEP 695 generics (`def func[T](...)`), pattern matching where appropriate

## Task Completion

**CRITICAL: Run `./scripts/dev-checks.sh` before marking ANY task completed.**

1. Mark task `in_progress`
2. Make changes
3. Run `./scripts/dev-checks.sh`
4. Only after checks pass → mark `completed`

## DO NOT

- Commit directly to `main`/`master` - use feature branches
- Create backwards compatibility layers unless asked
- Preserve old context in comments during refactoring
- Bypass quality checks
- Mark tasks completed without running dev-checks

## DO

- What was asked - nothing more, nothing less
- Remove unnecessary code after refactoring
- Break large classes/functions into smaller ones
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Run dev-checks before each task completion

## Git Requirements

**Branch naming:**
- `feature/feature-name`
- `fix/issue-description`
- `docs/documentation-updates`
- `refactor/component-name`

**Never commit directly to main/master.**

## Environment Configuration

```bash
cp apps/wct/.env.example apps/wct/.env
# Edit with API keys
uv run wct test-llm
```

**Priority:** Environment variables > `.env` file > Runbook properties > Code defaults

**Key variables:** `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `MYSQL_*`

## Adding New Packages

1. Create directory in `libs/` or `apps/` with `pyproject.toml`
2. Add standard scripts: `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`
3. Add to `[tool.uv.sources]` in root `pyproject.toml` if used as dependency
4. Run `uv sync`

## Resources

- [WCF Core Concepts](docs/core-concepts/wcf-core-components.md)
- [Configuration Guide](docs/how-tos/configuration.md)
- [Runbook Documentation](apps/wct/runbooks/README.md)
- [Child Runbook Composition](libs/waivern-orchestration/docs/child-runbook-composition.md)
