# Waivern Compliance Tool (WCT)

Command-line application for compliance analysis using the Waivern Compliance Framework.

## Overview

WCT is the CLI tool that orchestrates compliance analysis using connectors, processors, and rulesets from the Waivern ecosystem. It reads YAML runbook configurations and executes compliance analysis pipelines.

## Package Structure

```
apps/wct/
├── pyproject.toml          # Package configuration
├── README.md               # This file
├── scripts/                # Package-specific quality check scripts
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── src/
│   └── wct/
│       ├── __main__.py     # CLI entry point (Typer app definition)
│       ├── cli/            # CLI command implementations
│       │   ├── errors.py       # CLIError and error handling context manager
│       │   ├── formatting.py   # Rich console output formatting
│       │   ├── infrastructure.py # Service container setup
│       │   ├── run.py          # `wct run` command
│       │   ├── list.py         # `wct connectors/processors/runs/...` commands
│       │   ├── poll.py         # `wct poll` command (batch mode)
│       │   └── validate.py     # `wct validate-runbook` and `wct generate-schema`
│       ├── config/         # Configuration loading
│       ├── exporters/      # Result exporters (JSON, GDPR, etc.)
│       ├── schemas/        # Data schemas
│       └── logging.py      # Logging configuration
└── tests/                  # Package tests
```

## Development

This package follows a **package-centric development approach**:

```bash
# From package directory
cd apps/wct

# Run quality checks
./scripts/lint.sh          # Lint this package
./scripts/format.sh        # Format this package
./scripts/type-check.sh    # Type check this package

# From workspace root
./scripts/dev-checks.sh    # Check all packages + run tests
```

### Package Configuration

This package owns its complete quality tool configuration:
- **Type checking**: basedpyright in strict mode with test environment relaxations (`pyproject.toml`)
- **Linting/Formatting**: ruff with compliance-focused rules (`pyproject.toml`)
- **Scripts**: Package-specific quality check scripts (`scripts/`)

This enables independent development and ensures consistent standards.

## Dependencies

### Core Dependencies
- `waivern-core` - Framework abstractions
- `waivern-orchestration` - Runbook parsing, DAG execution
- `waivern-llm` - Multi-provider LLM abstraction (with batch mode support)
- `waivern-artifact-store` - Artifact and batch job storage
- `pydantic>=2.11.5` - Data validation
- `typer>=0.16.0` - CLI framework
- `rich>=13.0.0` - Terminal formatting

## Usage

See the [main README](../../README.md) for installation and usage instructions.

### Quick Start

```bash
# From workspace root
uv run wct run runbooks/samples/file_content_analysis.yaml
uv run wct run analysis.yaml --resume <run-id>  # Resume interrupted/failed run
uv run wct runs                                  # List recorded runs
uv run wct poll <run-id>                         # Poll batch job status
uv run wct connectors
uv run wct processors
```

## Testing

```bash
# From workspace root
uv run pytest apps/wct/tests/           # Run WCT tests only
uv run pytest apps/wct/tests/ -v        # Verbose output
uv run pytest                           # Run all workspace tests
```

## Documentation

Key documentation within this package:
- **[Schemas README](src/wct/schemas/README.md)** - Schema architecture and usage
- **[Processing Purpose Analyser README](src/wct/analysers/processing_purpose_analyser/README.md)** - Processing purpose detection

## License

Same as main waivern-compliance project (Apache License 2.0)
