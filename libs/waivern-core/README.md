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

## License

Same as main waivern-compliance project
