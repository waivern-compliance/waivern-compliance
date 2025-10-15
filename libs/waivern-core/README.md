# waivern-core

Core abstractions for Waivern Compliance Framework.

## Overview

This package provides the base abstractions that all Waivern components must implement:

- **Connector**: Base class for data source connectors
- **Analyser**: Base class for compliance analysers
- **Ruleset**: Base class for compliance rulesets
- **Message**: Data structure for passing data between components
- **Schema**: Base classes for schema definitions and validation

## Installation

```bash
uv add waivern-core
```

## Usage

```python
from waivern_core.base_connector import Connector
from waivern_core.message import Message
from waivern_core.schemas.base import Schema

class MyConnector(Connector):
    # Implement abstract methods
    ...
```

## Dependencies

Minimal dependencies by design:
- `jsonschema` - For schema validation
- `typing-extensions` - For enhanced type hints
- `annotated-types` - For type annotations

## Development

This package follows a **package-centric development approach**:

```bash
# From package directory
cd libs/waivern-core

# Run quality checks
./scripts/lint.sh          # Lint this package
./scripts/format.sh        # Format this package
./scripts/type-check.sh    # Type check this package

# From workspace root
./scripts/dev-checks.sh    # Check all packages + run tests
```

### Package Configuration

Each package owns its complete quality tool configuration:
- **Type checking**: basedpyright in strict mode (`pyproject.toml`)
- **Linting/Formatting**: ruff with compliance-focused rules (`pyproject.toml`)
- **Scripts**: Package-specific quality check scripts (`scripts/`)

This enables independent development and ensures consistent standards across all packages.

## License

Same as main waivern-compliance project
