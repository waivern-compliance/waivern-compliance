# Waivern Analyser

A flexible, plugin-based compliance analysis framework designed to analyze various systems, applications, and codebases for compliance with different standards and rules.

## Overview

Waivern Analyser provides a modular architecture that separates data collection from analysis through two main component types:

- **Connectors**: Extract and gather data from various sources (source code, databases, APIs, etc.)
- **Rulesets**: Define compliance rules and analysis logic to evaluate the collected data

## Architecture

The framework uses a plugin-based architecture where:

1. **Plugins** are discovered automatically using Python entry points
2. **Connectors** implement data extraction logic
3. **Rulesets** implement compliance analysis logic
4. **Workspace structure** allows modular development of components

```
waivern-analyser/
├── src/
│   ├── waivern_analyser/          # Core framework
│   ├── connectors/                # Data source connectors
│   │   ├── core/                  # Base connector framework
│   │   └── source_code/           # Source code analysis connector
│   └── rulesets/                  # Compliance rulesets
│       ├── core/                  # Base ruleset framework
│       └── wordpress/             # WordPress-specific rules
└── pyproject.toml                 # Project configuration
```

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
# Install uv if you haven't already
pip install uv

# Install the project and all workspace members
uv sync

# Install in development mode
uv pip install -e .
```

## Usage

### Running the Analyser

```bash
# Run the main analyser
waivern-analyser

# Or run as a module
python -m waivern_analyser
```

### Creating Custom Plugins

Plugins are the primary way to extend Waivern Analyser. A plugin can provide connectors, rulesets, or both.

#### Example Plugin Structure

```python
from waivern_analyser.plugin import Plugin
from waivern_connectors_core import Connector
from waivern_rulesets_core import Ruleset

class MyCustomPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "my-custom-plugin"
    
    @classmethod
    def get_connectors(cls):
        return (MyConnector(),)
    
    @classmethod
    def get_rulesets(cls):
        return (MyRuleset(),)
```

#### Registering Plugins

Add your plugin to your package's `pyproject.toml`:

```toml
[project.entry-points."waivern-plugins"]
my-plugin = "my_package:MyCustomPlugin"
```

## Development

### Project Structure

This is a uv workspace containing multiple related packages:

- `waivern-analyser`: Main framework
- `waivern-connectors-core`: Base classes for connectors
- `waivern-connectors-source-code`: Source code analysis connector
- `waivern-rulesets-core`: Base classes for rulesets
- `waivern-rulesets-wordpress`: WordPress compliance rules

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd analyser

# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run type checking
uv run basedpyright

# Run linting
uv run ruff check
```

### Creating New Connectors

1. Create a new directory under `src/connectors/`
2. Implement the `Connector` abstract class
3. Define input/output schemas
4. Add to workspace in main `pyproject.toml`

### Creating New Rulesets

1. Create a new directory under `src/rulesets/`
2. Implement the `Ruleset` abstract class
3. Define input/output schemas
4. Create a plugin class
5. Register the plugin via entry points

## Examples

### Available Connectors

- **Source Code Connector**: Analyzes source code repositories

### Available Rulesets

- **WordPress Ruleset**: Compliance rules specific to WordPress applications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and type checking succeeds
6. Submit a pull request

## License

[Add your license information here]

## Support

[Add support information here]