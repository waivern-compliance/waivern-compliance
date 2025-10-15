# Waivern Compliance Tool (WCT)

Command-line application for compliance analysis using the Waivern Compliance Framework.

## Overview

WCT is the CLI tool that orchestrates compliance analysis using connectors, analysers, and rulesets from the Waivern ecosystem. It reads YAML runbook configurations and executes compliance analysis pipelines.

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
│       ├── __main__.py     # CLI entry point
│       ├── cli.py          # CLI commands
│       ├── executor.py     # Runbook executor
│       ├── connectors/     # Data source connectors
│       ├── analysers/      # Compliance analysers
│       ├── rulesets/       # Compliance rulesets
│       ├── schemas/        # Data schemas
│       └── llm_service/    # LLM integration
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
- `pydantic>=2.11.5` - Data validation
- `typer>=0.16.0` - CLI framework
- `rich>=13.0.0` - Terminal formatting

### Connector Dependencies
- `pymysql>=1.1.1` - MySQL database connector
- `cryptography>=45.0.5` - Database connection security
- `tree-sitter>=0.21.0` - Source code parsing

### Analyser Dependencies
- `langchain>=0.3.0` - LLM framework
- `langchain-anthropic>=0.2.0` - Anthropic LLM provider
- `jsonschema>=4.25.0` - Schema validation

## Usage

See the [main README](../../README.md) for installation and usage instructions.

### Quick Start

```bash
# From workspace root
uv run wct run runbooks/samples/file_content_analysis.yaml
uv run wct ls-connectors
uv run wct ls-analysers
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
