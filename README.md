# Waivern Compliance Tool (WCT)

A modern, plugin-based compliance analysis framework for detecting and analyzing compliance issues across tech stacks.

## Overview

WCT provides a flexible architecture for compliance analysis through:

- **Connectors**: Extract data from various sources (files, databases, web applications)
- **Plugins**: Perform compliance analysis on extracted data
- **Rulesets**: Define reusable compliance rules and checks
- **Orchestrator**: Manages the execution pipeline and data flow

The system is designed to be extensible and configurable through YAML runbook files.

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

Some connectors and plugins require additional dependencies that are not installed by default. Check the connector/plugin documentation or error messages for specific dependency group requirements.

### Basic Usage

1. **Analyze with a runbook**:
   ```bash
   uv run wct analyze sample_runbook.yaml
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
connectors:
  file_reader:
    type: file
    properties:
      file_path: "/path/to/data.txt"

  mysql_db:
    type: mysql
    properties:
      host: "localhost"
      user: "dbuser"
      password: "dbpass"
      database: "mydb"

plugins:
  personal_data_check:
    type: personal_data_analyser
    properties:
      check_emails: true
      check_phone_numbers: true

execution_order:
  - connector: file_reader
    plugin: personal_data_check
  - connector: mysql_db
    plugin: personal_data_check
```

**Note**: The MySQL connector requires the `mysql` dependency group: `uv sync --group mysql`

## Architecture

### Core Components

- **`src/wct/orchestrator.py`**: Main orchestration engine
- **`src/wct/connectors/`**: Data source connectors (modular architecture)
  - `file/` - File connector for local files
  - `mysql/` - MySQL connector for database analysis
  - `wordpress/` - WordPress connector for CMS analysis
- **`src/wct/plugins/`**: Analysis plugins (modular architecture)
  - `file_content_analyser/` - File content analysis module
  - `personal_data_analyser/` - Personal data analysis module
- **`src/wct/rulesets/`**: Reusable compliance rules
  - Personal data detection rules

### Modular Architecture Benefits

Each connector and plugin is organized as an independent module with its own directory:

- **Better Encapsulation**: Each component can contain supporting files, utilities, and tests
- **Extensibility**: Easy to add complex logic, configuration files, and dependencies per component
- **Maintainability**: Clear separation of concerns with dedicated directories
- **Development Flexibility**: Teams can work on individual components without conflicts

### Configuration

WCT uses YAML runbook files with three main sections:

- **`connectors`**: Define data sources and their configuration
- **`plugins`**: Specify analysis plugins to run
- **`execution_order`**: Control the sequence of connector->plugin execution

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
uv run wct analyze runbook.yaml --log-level DEBUG
uv run wct analyze runbook.yaml -v  # Shortcut for debug
```

### Extending WCT

#### Creating a Custom Connector

```python
from wct.connectors.base import Connector

class MyConnector(Connector):
    @classmethod
    def get_name(cls) -> str:
        return "my_connector"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        # Initialize from configuration
        return cls(**properties)

    def extract(self) -> dict[str, Any]:
        # Extract data from your source
        return {"data": "extracted_content"}
```

#### Creating a Custom Plugin

```python
from wct.plugins.base import Plugin

class MyPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "my_plugin"

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        # Analyze the data
        return {"findings": ["compliance_issue_1"]}
```

### Project Structure

```
src/wct/
├── __main__.py           # CLI entry point
├── orchestrator.py       # Main orchestration engine
├── connectors/           # Data source connectors (modular)
│   ├── base.py          # Base connector class
│   ├── file/            # File system connector module
│   │   ├── __init__.py
│   │   └── connector.py
│   ├── mysql/           # MySQL database connector module
│   │   ├── __init__.py
│   │   └── connector.py
│   └── wordpress/       # WordPress connector module
│       ├── __init__.py
│       └── connector.py
├── plugins/             # Analysis plugins (modular)
│   ├── base.py          # Base plugin class
│   ├── file_content_analyser/    # File content analysis module
│   │   ├── __init__.py
│   │   └── plugin.py
│   └── personal_data_analyser/   # Personal data analysis module
│       ├── __init__.py
│       └── plugin.py
└── rulesets/            # Reusable compliance rules
    ├── base.py          # Base ruleset class
    └── personal_data.py # Personal data detection rules
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
