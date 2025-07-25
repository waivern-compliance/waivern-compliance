# Waivern Compliance Tool (WCT)

A modern, plugin-based compliance analysis framework for detecting and analyzing compliance issues across tech stacks.

## Overview

WCT provides a flexible architecture for compliance analysis through:

- **Connectors**: Extract data from various sources (files, databases, web applications)
- **Plugins**: Perform compliance analysis on extracted data
- **Rulesets**: Define reusable compliance rules and checks
- **Orchestrator**: Manages the execution pipeline and data flow

The system is designed to be extensible and configurable through YAML runbook files with a unified schema-driven architecture that ensures type safety and component interoperability.

## Quick Start

### Installation

This project uses `uv` for dependency management with optional dependency groups for specific connectors and plugins:

```bash
# Install core dependencies only
uv sync

# Install with specific connector/plugin dependencies
uv sync --group mysql      # MySQL connector support
uv sync --group dev        # Development tools

# Install multiple groups
uv sync --group mysql --group dev

# Install pre-commit hooks (recommended)
uv run pre-commit install
```

**Available Dependency Groups**:
- `mysql` - MySQL connector dependencies (pymysql, cryptography)
- `dev` - Development tools (pytest, ruff, basedpyright, etc.)

**Core Dependencies**:
- `jsonschema` - JSON schema validation for comprehensive data validation

Some connectors and plugins require additional dependencies that are not installed by default. Check the connector/plugin documentation or error messages for specific dependency group requirements.

### Basic Usage

1. **Run analysis with a runbook**:
   ```bash
   uv run wct run sample_runbook.yaml
   ```

2. **List available components**:
   ```bash
   uv run wct list-connectors
   uv run wct list-plugins
   ```

3. **Validate a runbook**:
   ```bash
   uv run wct validate-runbook your_runbook.yaml
   ```

### Example Runbook

```yaml
name: "Compliance Analysis"
description: "Analyze files and databases for sensitive information"

connectors:
  - name: "file_reader"
    type: "file_reader"
    properties:
      path: "./sample_file.txt"
  - name: "my_database"
    type: "mysql"
    properties:
      host: "localhost"
      user: "dbuser"
      password: "dbpass"
      database: "mydb"
      port: 3306

  mysql_db:
    type: mysql
    properties:
      host: "localhost"
      user: "dbuser"
      password: "dbpass"
      database: "mydb"

plugins:
  - name: "content_analyser"
    type: "file_content_analyser"
    properties:
      sensitivity_level: "medium"
    metadata:
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]

execution:
  - connector: "file_reader"
    plugin: "content_analyser"
    input_schema: "./src/wct/schemas/text.json"
    output_schema: "./src/wct/schemas/content_analysis_result.json"
    context:
      description: "Analyze file content for sensitive information"
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]
```

**Key Features**:
- **Comprehensive schema validation**: Automatic input and output validation against JSON schemas
- **Explicit connector-plugin mapping**: Clear data flow specification in execution steps
- **Dynamic schema loading**: Flexible schema file discovery with multiple search paths
- **End-to-end validation**: Full pipeline validation from data extraction to analysis results
- **Optional dependencies**: MySQL connector requires `uv sync --group mysql`


## Architecture

### Schema-Driven Design

WCT uses a **unified schema system** (`WctSchema`) with comprehensive validation:

- **Type Safety**: Generic schema containers with compile-time type checking
- **Automatic Validation**: Built-in input and output validation using JSON schemas
- **Dynamic Schema Loading**: Flexible schema file discovery across multiple locations
- **End-to-End Validation**: Complete pipeline validation from connector output to plugin results
- **Interoperability**: Standardized data contracts between connectors and plugins
- **Extensibility**: Easy to add new schema types while maintaining compatibility

### Core Components

- **`src/wct/orchestrator.py`**: Schema-aware orchestration engine
- **`src/wct/schema.py`**: Unified WctSchema system for type-safe data flow
- **`src/wct/schemas/`**: JSON schema definitions for validation
  - `text.json` - Text content schema
  - `content_analysis_result.json` - Analysis output schema
- **`src/wct/connectors/`**: Schema-compliant data source connectors
  - `file/` - File connector producing "text" schema
  - `mysql/` - MySQL connector producing "mysql_database" schema
  - `wordpress/` - WordPress connector producing "wordpress_site" schema
- **`src/wct/plugins/`**: Schema-aware analysis plugins
  - `file_content_analyser/` - Consumes "text" schema, produces "content_analysis_result"
  - `personal_data_analyser/` - Personal data detection with schema validation
- **`src/wct/rulesets/`**: Reusable compliance rules with schema support

### Schema Pipeline Flow

1. **Plugins declare input schemas** in execution order
2. **Orchestrator determines required schemas** from plugin requirements
3. **Connectors extract data** only if their output schemas are needed
4. **Schema validation** ensures data format compliance
5. **Plugins process validated data** and produce schema-compliant results

### Modular Architecture Benefits

Each connector and plugin is organized as an independent module:

- **Schema Contracts**: Clear input/output schema declarations
- **Dependency Isolation**: Optional dependencies grouped by component
- **Independent Testing**: Each module can be tested in isolation
- **Hot-swappable Components**: Add/remove connectors and plugins without affecting others

### Configuration Format

WCT runbooks use a **comprehensive execution format** with explicit connector-plugin mapping:

```yaml
# Modern execution format (required)
execution:
  - connector: "connector_name"
    plugin: "plugin_name"
    input_schema: "./src/wct/schemas/schema_name.json"
    output_schema: "./src/wct/schemas/output_schema.json"  # optional
    context:  # optional metadata
      description: "Step description"
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]
```

## Development

### Development Commands

**Testing**:
```bash
uv run pytest                    # Run all tests
uv run pytest -v                 # Verbose output
uv run pytest tests/specific.py  # Run specific test
```

**Code Quality**:
```bash
uv run ruff check               # Linting
uv run ruff format              # Code formatting
uv run basedpyright             # Type checking
uv run pre-commit run --all-files  # All pre-commit hooks
```

**Logging Options**:
All WCT commands support detailed logging:
```bash
uv run wct run runbook.yaml --log-level DEBUG
uv run wct run runbook.yaml -v  # Shortcut for debug
```

### Extending WCT

#### Creating a Schema-Compliant Connector

```python
from typing import Any
from typing_extensions import Self, override
from wct.connectors.base import Connector
from wct.schema import WctSchema

class MyConnector(Connector[dict[str, Any]]):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_connector"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(**properties)

    @override
    def extract(self, schema: WctSchema[dict[str, Any]]) -> dict[str, Any]:
        # Extract and transform data to match schema
        return {"data": "schema_compliant_content"}

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_data", type=dict[str, Any])
```

#### Creating a Schema-Aware Plugin

```python
from typing import Any
from typing_extensions import Self, override
from wct.plugins.base import Plugin
from wct.schema import WctSchema

class MyPlugin(Plugin[dict[str, Any], dict[str, Any]]):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_plugin"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(**properties)

    @override
    def process_data(self, data: dict[str, Any]) -> dict[str, Any]:
        # Process schema-validated input data
        # Input and output validation are handled automatically by the base class
        return {"findings": ["compliance_issue_1"]}

    @override
    def get_input_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_data", type=dict[str, Any])

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_results", type=dict[str, Any])

    @override
    def validate_input(self, data: dict[str, Any]) -> bool:
        # Dynamic validation using JSON schema files
        # This method now automatically loads and validates against JSON schemas
        # Custom validation logic can be added here if needed
        return True  # Base class handles schema validation
```

**Key Plugin Features**:
- **Automatic Validation**: The `process()` method automatically validates both input and output data
- **Dynamic Schema Loading**: JSON schema files are automatically discovered and loaded
- **Type Safety**: Full type checking with generic type parameters
- **Error Handling**: Comprehensive error messages for validation failures
- **Seamless Processing**: Implement `process_data()` for your core logic, validation is handled transparently

### Project Structure

```
src/wct/
├── __main__.py           # CLI entry point
├── orchestrator.py       # Schema-aware orchestration engine
├── schema.py             # Unified WctSchema system
├── schemas/              # JSON schema definitions
│   ├── text.json                    # Text content schema
│   └── content_analysis_result.json # Analysis result schema
├── connectors/           # Schema-compliant data connectors
│   ├── base.py          # Abstract connector with schema support
│   ├── file/            # File connector (produces "text" schema)
│   │   ├── __init__.py
│   │   └── connector.py
│   ├── mysql/           # MySQL connector (produces "mysql_database" schema)
│   │   ├── __init__.py
│   │   └── connector.py
│   └── wordpress/       # WordPress connector (produces "wordpress_site" schema)
│       ├── __init__.py
│       └── connector.py
├── plugins/             # Schema-aware analysis plugins
│   ├── base.py          # Abstract plugin with schema validation
│   ├── file_content_analyser/    # Text analysis (text → content_analysis_result)
│   │   ├── __init__.py
│   │   └── plugin.py
│   └── personal_data_analyser/   # Personal data detection with schemas
│       ├── __init__.py
│       └── plugin.py
├── rulesets/            # Schema-compliant compliance rules
│   ├── base.py          # Base ruleset class
│   └── personal_data.py # Personal data detection rules
├── runbook.py           # Schema-aware runbook parsing
└── cli.py               # Command-line interface
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `uv run pre-commit run --all-files`
5. Submit a pull request

### Code Standards

- Type annotations are required (`basedpyright`)
- Code formatting with `ruff`
- Security checks with `bandit`
- Comprehensive test coverage

## License

[Add your license information here]

## Support

[Add support/contact information here]
