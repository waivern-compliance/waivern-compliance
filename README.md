# Waivern Compliance Tool (WCT)

A modern, plugin-based compliance analysis framework for detecting and analyzing compliance issues across tech stacks.

## Overview

WCT provides a flexible architecture for compliance analysis through:

- **Connectors**: Extract data from various sources (files, databases, web applications)
- **Plugins**: Perform compliance analysis on extracted data
- **Rulesets**: Define reusable compliance rules and checks
- **Executor**: Manages the execution pipeline and data flow

The system is designed to be extensible and configurable through YAML runbook files with a unified schema-driven architecture that ensures type safety and component interoperability.

## Quick Start

### Installation

This project uses `uv` for dependency management with optional dependency groups for specific connectors and plugins:

```bash
# Install core dependencies only
uv sync

# Install with specific connector/plugin dependencies
uv sync --group mysql      # MySQL connector support
uv sync --group source-code # Source code analysis support
uv sync --group dev        # Development tools

# Install multiple groups
uv sync --group mysql --group source-code --group dev

# Install pre-commit hooks (recommended)
uv run pre-commit install
```

**Available Dependency Groups**:
- `mysql` - MySQL connector dependencies (pymysql, cryptography)
- `source-code` - Source code analysis dependencies (tree-sitter, tree-sitter-php)
- `dev` - Development tools (pytest, ruff, basedpyright, etc.)

**Core Dependencies**:
- `jsonschema` - JSON schema validation for comprehensive data validation
- `langchain` and `langchain-anthropic` - AI-powered compliance analysis and validation

Some connectors and plugins require additional dependencies that are not installed by default. Check the connector/plugin documentation or error messages for specific dependency group requirements.

**Notable Connectors**:
- MySQL connector requires `uv sync --group mysql`
- Source code connector requires `uv sync --group source-code`

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
    input_schema_name: "text"
    output_schema_name: "file_content_analysis_result"
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
- **Optional dependencies**: MySQL connector requires `uv sync --group mysql`, source code connector requires `uv sync --group source-code`


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

- **`src/wct/executor.py`**: Schema-aware execution engine
- **`src/wct/schema.py`**: Unified WctSchema system for type-safe data flow
- **`src/wct/schemas/`**: JSON schema definitions for validation
  - `text.json` - Text content schema
  - `file_content_analysis_result.json` - Analysis output schema
- **`src/wct/connectors/`**: Schema-compliant data source connectors
  - `file/` - File connector producing "text" schema
  - `mysql/` - MySQL connector producing "mysql_database" schema
  - `source_code/` - Source code connector producing "source_code_analysis" schema
  - `wordpress/` - WordPress connector producing "wordpress_site" schema
- **`src/wct/plugins/`**: Schema-aware analysis plugins
  - `file_content_analyser/` - Consumes "text" schema, produces "file_content_analysis_result"
  - `personal_data_analyser/` - Personal data detection with schema validation
- **`src/wct/rulesets/`**: Reusable compliance rules with schema support

### Schema Pipeline Flow

1. **Plugins declare input schemas** in execution order
2. **Executor determines required schemas** from plugin requirements
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
    input_schema_name: "schema_name"  # Schema name (not file path)
    output_schema_name: "output_schema"  # Schema name (optional)
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
from wct.message import Message

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
    def process_data(self, message: Message) -> Message:
        # Process schema-validated input message
        # Extract data from the message
        input_data = message.content

        # Perform your analysis logic here
        findings = ["compliance_issue_1"]

        # Create result data
        result_data = {"findings": findings}

        # Return new Message with results
        return Message(
            id=f"Analysis results for {message.id}",
            content=result_data,
            schema=self.get_output_schema(),
        )

    @override
    def get_input_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_data", type=dict[str, Any])

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_results", type=dict[str, Any])

```

**Key Plugin Features**:
- **Message-Based Architecture**: All plugins now work with `Message` objects for unified data flow
- **Automatic Validation**: The `process()` method automatically validates both input and output Messages
- **Schema-Aware Processing**: Input and output Messages are validated against declared schemas
- **Type Safety**: Full type checking with generic type parameters and Message containers
- **Error Handling**: Comprehensive error messages for validation failures
- **Seamless Processing**: Implement `process_data()` with Message objects, validation is handled transparently
- **No Manual Validation**: Plugins no longer need to implement validation - handled by the Message mechanism

### Project Structure

```
src/wct/
├── __main__.py           # CLI entry point
├── executor.py           # Schema-aware execution engine
├── schema.py             # Unified WctSchema system
├── schemas/              # JSON schema definitions
│   ├── text.json                    # Text content schema
│   ├── source_code_analysis.json   # Source code analysis schema
│   └── file_content_analysis_result.json # Analysis result schema
├── connectors/           # Schema-compliant data connectors
│   ├── base.py          # Abstract connector with schema support
│   ├── file/            # File connector (produces "text" schema)
│   │   ├── __init__.py
│   │   └── connector.py
│   ├── mysql/           # MySQL connector (produces "mysql_database" schema)
│   │   ├── __init__.py
│   │   └── connector.py
│   ├── source_code/     # Source code connector (produces "source_code_analysis" schema)
│   │   ├── __init__.py
│   │   ├── connector.py
│   │   ├── parser.py
│   │   └── extractors/  # Modular code analysis extractors
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── functions.py
│   │       └── classes.py
│   └── wordpress/       # WordPress connector (produces "wordpress_site" schema)
│       ├── __init__.py
│       └── connector.py
├── plugins/             # Schema-aware analysis plugins
│   ├── base.py          # Abstract plugin with schema validation
│   ├── file_content_analyser/    # Text analysis (text → file_content_analysis_result)
│   │   ├── __init__.py
│   │   └── plugin.py
│   └── personal_data_analyser/   # Personal data detection with schemas
│       ├── __init__.py
│       └── plugin.py
├── rulesets/            # Schema-compliant compliance rules
│   ├── base.py          # Base ruleset class
│   └── personal_data.py # Personal data detection rules
├── runbook.py           # Schema-aware runbook parsing with Message support
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

This project uses a dual-license structure:

### Main Codebase
The core Waivern Compliance Tool is licensed under the **GNU Affero General Public License v3.0** with additional terms. See the [`LICENSE`](LICENSE) file for full details.

### Connectors
The connector modules (`src/wct/connectors/`) are licensed under the **GNU General Public License v3.0**. See [`src/wct/connectors/LICENSE`](src/wct/connectors/LICENSE) for full details.

This licensing structure allows:
- **Core WCT Framework**: Strong copyleft protection ensuring modifications remain open source, especially for network/SaaS usage
- **Connectors**: Standard GPL protection for data extraction components with more permissive linking options

For commercial licensing or questions about license compatibility, please contact Wainvern.

## Support

[Add support/contact information here]
