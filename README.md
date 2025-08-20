# Waivern Compliance Tool (WCT)

A modern, analyser-based compliance analysis framework for detecting and analysing compliance issues across tech stacks.

## Overview

WCT provides a flexible architecture for compliance analysis through:

- **Connectors**: Extract data from various sources (files, databases, web applications)
- **Analysers**: Perform compliance analysis on extracted data
- **Rulesets**: Rule patterns for compliance static analysis
- **Executor**: Manages the execution pipeline and data flow

The system is designed to be extensible and configurable through YAML runbook files with comprehensive validation that ensures type safety and component interoperability.

📋 **[Development Roadmap](docs/development_roadmap.md)** - See our current progress and planned features

🚀 **Ready to contribute?** Check out our [contribution opportunities](docs/development_roadmap.md#contribution-opportunities) and browse [good first issues](https://github.com/waivern-compliance/waivern-compliance/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) to get started!

## Quick Start

### Installation

This project uses `uv` for dependency management with optional dependency groups for specific connectors and analysers:

```bash
# Install core dependencies only
uv sync

# Install with specific connector/analyser dependencies
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
- `jsonschema` - Data validation for component interoperability
- `langchain` and `langchain-anthropic` - AI-powered compliance analysis and validation

Some connectors and analysers require additional dependencies that are not installed by default. Check the connector/analyser documentation or error messages for specific dependency group requirements.

**Notable Connectors**:
- MySQL connector requires `uv sync --group mysql`
- Source code connector requires `uv sync --group source-code`

### Basic Usage

1. **Run analysis with a runbook**:
   ```bash
   # Simple file analysis demonstration
   uv run wct run runbooks/samples/file_content_analysis.yaml

   # Comprehensive LAMP stack analysis
   uv run wct run runbooks/samples/LAMP_stack.yaml
   ```

2. **List available components**:
   ```bash
   uv run wct ls-connectors
   uv run wct ls-analysers
   ```

3. **Validate a runbook**:
   ```bash
   uv run wct validate-runbook runbooks/samples/file_content_analysis.yaml
   ```

### Runbooks Directory

WCT organises runbook configurations in the `runbooks/` directory with samples organised in `runbooks/samples/`:

- **`runbooks/samples/file_content_analysis.yaml`** - Simple file analysis demonstration using personal data analyser
- **`runbooks/samples/LAMP_stack.yaml`** - Comprehensive example demonstrating file, database, and source code analysis
- **`runbooks/README.md`** - Detailed documentation on runbook usage and creation guidelines

Run sample runbooks:
```bash
# Simple file content analysis
uv run wct run runbooks/samples/file_content_analysis.yaml

# Comprehensive LAMP stack analysis
uv run wct run runbooks/samples/LAMP_stack.yaml

# Run with verbose logging
uv run wct run runbooks/samples/file_content_analysis.yaml -v
```

### Example Runbook

```yaml
name: "Compliance Analysis"
description: "Analyse files and databases for sensitive information"

connectors:
  - name: "filesystem_reader"
    type: "filesystem"
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


analysers:
  - name: "content_analyser"
    type: "personal_data_analyser"
    metadata:
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]

execution:
  - connector: "filesystem_reader"
    analyser: "content_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
    context:
      description: "Analyse file content for personal data"
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]
```

**Key Features**:
- **Comprehensive validation**: Automatic input and output validation with clear error messages
- **Explicit connector-analyser mapping**: Clear data flow specification in execution steps
- **Dynamic schema loading**: Flexible schema file discovery with multiple search paths
- **End-to-end validation**: Full pipeline validation from runbook loading to analysis results
- **Optional dependencies**: MySQL connector requires `uv sync --group mysql`, source code connector requires `uv sync --group source-code`


## Architecture

For a comprehensive understanding of the core concepts and design principles that underpin WCT, see **[WCF Core Concepts](docs/wcf_core_concepts.md)**.

### Validation System

WCT uses a comprehensive validation system with two distinct validation approaches:

**Data Flow Schemas** - Validate runtime data between components:
- **StandardInputSchema**: Common input format for filesystem connectors
- **PersonalDataFindingSchema**: Output format for personal data analysis results
- Uses JSON Schema for cross-component data validation

**Configuration Validation** - Validate runbook configuration files:
- **Runbook**: YAML runbook configuration validation with structural requirements
- Uses Python type annotations for clear validation rules

Key features:
- **Declarative validation**: Clear validation rules with comprehensive error messages
- **Better error messages**: Field path reporting with detailed validation failure information
- **Type safety**: Strongly typed interfaces throughout the system
- **Versioned architecture**: Consistent schema structure in `json_schemas/{name}/{version}/`

### Core Components

- **`src/wct/runbook.py`**: Runbook loading with comprehensive validation
- **`src/wct/executor.py`**: Schema-aware execution engine with automatic data flow matching
- **`src/wct/schemas/`**: Strongly typed schema system (see [schemas README](src/wct/schemas/README.md))
  - Data flow schemas: `StandardInputSchema`, `PersonalDataFindingSchema`
  - JSON schema validation for component data exchange
- **`src/wct/connectors/`**: Data source connectors
  - `filesystem/` - File content extraction
  - `mysql/` - Database analysis
- **`src/wct/analysers/`**: Compliance analysis engines
  - `personal_data_analyser/` - Personal data detection with LLM validation
- **`src/wct/rulesets/`**: Versioned rule patterns for compliance static analysis

### Validation Pipeline Flow

1. **Runbook loading**: Validates YAML structure, field requirements, and patterns
2. **Cross-reference validation**: Verify connector/analyser names and execution step relationships
3. **Execution orchestration**: Automatic schema matching between connector outputs and analyser inputs
4. **Data validation**: Runtime validation of data flowing between components using Message objects
5. **Results processing**: Schema-validated analysis results with comprehensive error reporting

### Modular Architecture Benefits

- **Schema Contracts**: Clear input/output schema declarations for all components
- **Dependency Isolation**: Optional dependencies grouped by component (`uv sync --group mysql`)
- **Independent Testing**: Each module tested in isolation with comprehensive coverage
- **Declarative Configuration**: YAML runbooks with comprehensive validation eliminate manual validation
- **Type Safety**: Strongly typed interfaces with comprehensive error reporting
- **Compliance Focus**: Components optimised for regulatory requirements (GDPR, CCPA)

### Configuration Format

WCT runbooks use **validated YAML** with mandatory schema specifications:

```yaml
# All fields comprehensively validated
name: "Analysis Pipeline"                    # Required
description: "Compliance analysis setup"    # Required

connectors:                                  # Required, minItems: 1
  - name: "filesystem_reader"               # Required, pattern validated
    type: "filesystem"                      # Required
    properties: {...}                       # Required

analysers:                                  # Required, minItems: 1
  - name: "data_analyser"                  # Required, pattern validated
    type: "personal_data_analyser"         # Required
    properties: {...}                      # Required

execution:                                  # Required, minItems: 1
  - connector: "filesystem_reader"          # Required, cross-referenced
    analyser: "data_analyser"              # Required, cross-referenced
    input_schema: "standard_input"    # Required
    output_schema: "personal_data_finding"  # Required
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
uv run wct run runbooks/sample_runbook.yaml --log-level DEBUG
uv run wct run runbooks/sample_runbook.yaml -v  # Shortcut for debug
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

#### Creating a Schema-Aware Analyser

```python
from typing import Any
from typing_extensions import Self, override
from wct.analysers.base import Analyser
from wct.schema import WctSchema
from wct.message import Message

class MyAnalyser(Analyser):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_analyser"

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

**Key Analyser Features**:
- **Message-Based Architecture**: All analysers now work with `Message` objects for unified data flow
- **Automatic Validation**: The `process()` method automatically validates both input and output Messages
- **Schema-Aware Processing**: Input and output Messages are validated against declared schemas
- **Type Safety**: Full type checking with generic type parameters and Message containers
- **Error Handling**: Comprehensive error messages for validation failures
- **Seamless Processing**: Implement `process_data()` with Message objects, validation is handled transparently
- **No Manual Validation**: Analysers no longer need to implement validation - handled by the Message mechanism

### Project Structure

```
src/wct/
├── __main__.py           # CLI entry point
├── runbook.py           # Runbook loading and validation
├── executor.py          # Schema-aware execution engine
├── schemas/             # Strongly typed schema system
│   ├── README.md        # Schema architecture and usage documentation
│   ├── standard_input.py # StandardInputSchema (data flow validation)
│   └── json_schemas/    # Versioned JSON Schema definitions
│       └── standard_input/1.0.0/
│           └── standard_input.json # JSON Schema validation rules
├── connectors/          # Data source extractors
│   ├── base.py         # Abstract connector interface
│   ├── filesystem/     # File content extraction
│   └── mysql/          # Database analysis (requires --group mysql)
├── analysers/          # Compliance analysis engines
│   ├── base.py         # Abstract analyser interface
│   └── personal_data_analyser/ # Personal data detection with LLM
└── rulesets/           # Rule patterns for compliance static analysis
    ├── data/           # Versioned rule pattern configurations
    ├── base.py         # Ruleset framework
    └── {ruleset}.py    # Rule pattern loaders

runbooks/               # YAML configuration files
├── README.md          # Usage guidelines and examples
└── samples/           # Sample runbook configurations
    ├── file_content_analysis.yaml  # Basic file analysis demo
    └── LAMP_stack.yaml             # Comprehensive analysis example
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

### Community Support

Join our Discord community for support, discussions, and updates:

🔗 **[Discord Server](https://discord.com/invite/gcU7py4X)**

Our Discord server provides:
- **General Help** - Get assistance with installation, configuration, and usage
- **Development Discussion** - Collaborate on new features and improvements
- **Bug Reports** - Report issues and get community support
- **Feature Requests** - Suggest and discuss new functionality
- **Community Showcase** - Share your WCT implementations and use cases

### Other Support Channels

- **GitHub Issues** - For bug reports and feature requests: [Open an Issue](https://github.com/waivern-compliance/waivern-compliance/issues)
- **GitHub Discussions** - For general questions and community discussions
- **Documentation** - Check the [README](README.md) and [CLAUDE.md](CLAUDE.md) for detailed guidance
