# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python project using `uv` for dependency management. Key commands:

**Testing:**
- `uv run pytest` - Run all tests
- `uv run pytest tests/test_specific.py` - Run specific test file
- `uv run pytest -v` - Run tests with verbose output

**Linting and Type Checking:**
- `uv run ruff check` - Run linting
- `uv run ruff format` - Format code
- `uv run basedpyright` - Run type checking
- `uv run pre-commit run --all-files` - Run all pre-commit hooks
- `uv run pre-commit install` - Install pre-commit hooks (run once after cloning)

**Running the Application:**
- `uv run wct run <runbook.yaml>` - Run WCT analysis with a runbook
- `uv run wct list-connectors` - List available connectors
- `uv run wct list-plugins` - List available plugins
- `uv run wct validate-runbook <runbook.yaml>` - Validate a runbook

**Dependency Groups:**
WCT uses optional dependency groups for specific connectors:
- `uv sync --group mysql` - Install MySQL connector dependencies (pymysql, cryptography)
- `uv sync --group dev` - Install development tools
- `uv sync --group mysql --group dev` - Install multiple groups

**Logging Options:**
All WCT commands support logging configuration:
- `--log-level DEBUG` - Show all debug information
- `--log-level INFO` - Show informational messages (default)
- `--log-level WARNING` - Show warnings and errors only
- `--log-level ERROR` - Show errors only
- `--log-level CRITICAL` - Show critical errors only
- `--verbose` or `-v` - Shortcut for `--log-level DEBUG`

Examples:
- `uv run wct run runbook.yaml --log-level DEBUG` - Detailed debugging
- `uv run wct run runbook.yaml -v` - Verbose output
- `uv run wct list-connectors --log-level WARNING` - Minimal output

## Architecture Overview

This codebase implements WCT (Waivern Compliance Tool), a modern compliance analysis framework with **unified schema-driven architecture**:

### WCT Schema-Driven System Architecture
- **Entry point:** `src/wct/__main__.py`
- **Schema-aware executor:** `src/wct/executor.py`
- **Unified schema system:** `src/wct/schema.py` - `WctSchema[T]` for type-safe data flow
- **Schema definitions:** `src/wct/schemas/` - JSON schema files for validation
- **Configuration:** YAML runbooks with schema-aware execution order
- **Architecture:** Schema-compliant connectors and plugins with automatic data flow matching

### Key Schema-Compliant Components
- **Schema-Compliant Connectors:** Extract and transform data to WCT schemas - **Modular Architecture**
  - File connector (`src/wct/connectors/file/`) - Produces "text" schema
  - MySQL connector (`src/wct/connectors/mysql/`) - Produces "mysql_database" schema
  - WordPress connector (`src/wct/connectors/wordpress/`) - Produces "wordpress_site" schema
- **Schema-Aware Plugins:** Process validated data with input/output schema contracts - **Modular Architecture**
  - File content analyser (`src/wct/plugins/file_content_analyser/`) - text → content_analysis_result
  - Personal data analyser (`src/wct/plugins/personal_data_analyser/`) - Schema-validated processing
- **Schema-Aware Executor:** Matches connector output schemas to plugin input schemas automatically
- **Schema System:** `WctSchema[T]` with JSON schema validation for runtime type safety
- **Rulesets:** Schema-compliant reusable rule definitions for compliance checks
  - Personal data ruleset (`src/wct/rulesets/personal_data.py`)

### Schema-Driven Modular Architecture
Each connector and plugin is organized as an independent module with schema contracts:
- **Directory Structure:** Each component has its own directory with `__init__.py` and implementation files
- **Schema Contracts:** Clear input/output schema declarations for type safety
- **Dependency Isolation:** Optional dependencies grouped by component (e.g., `mysql` group)
- **Encapsulation:** Components can contain supporting files, utilities, configuration, and tests
- **Extensibility:** Easy to add complex logic and dependencies per component
- **Import Compatibility:** Main `__init__.py` files maintain backward-compatible imports

### Modern Execution Configuration Format
WCT runbooks use a comprehensive execution format with explicit connector-plugin mapping:

**Required Execution Format:**
```yaml
execution:
  - connector: "connector_name"
    plugin: "plugin_name"
    input_schema_name: "schema_name"  # Schema name (not file path)
    output_schema_name: "output_schema"  # Schema name (optional)
    context:  # optional metadata
      description: "Step description"
      priority: "high"
      compliance_frameworks: ["GDPR", "CCPA"]
      sensitivity_rules: ["email_detection", "password_detection"]
```

**Core Runbook Sections:**
- `connectors`: Define data sources and their configuration
- `plugins`: Specify analysis plugins with metadata
- `execution`: Comprehensive execution steps with connector-plugin mapping and context

### Schema-Compliant Base Classes with Automatic Validation
- **Connector base:** `src/wct/connectors/base.py` - Abstract connector with `WctSchema[T]` support and transform methods
- **Plugin base:** `src/wct/plugins/base.py` - Abstract plugin with Message-based architecture and automatic validation
  - `process()` - Automatic end-to-end Message validation with processing
  - `process_data()` - Abstract method for plugin-specific processing logic using Message objects
  - Message validation handled automatically by base class (no manual validation needed)
- **Ruleset base:** `src/wct/rulesets/base.py` - Schema-aware rule definitions
- **Schema system:** `src/wct/schema.py` - `WctSchema[T]` generic container for type safety
- All components support dynamic registration, configuration, and comprehensive schema validation

## Project Structure Notes
- Uses `uv` for dependency management with optional dependency groups
- **Core Dependencies:** `jsonschema` for comprehensive JSON schema validation
- Type annotations are enforced with `basedpyright` (schema system is fully type-safe)
- Main package is `wct` located in `src/wct/`
- Schema definitions in `src/wct/schemas/` (JSON Schema format)
- Sample configurations: `sample_runbook.yaml` (with modern execution format)

## Development Setup

**Pre-commit hooks are configured** for the WCT schema-driven system:
- Ruff linting and formatting
- Basic file checks (YAML/TOML validation, trailing whitespace, etc.)
- Security checks with bandit
- Type checking with basedpyright (fully enabled - schema system passes all type checks)

The pre-commit hooks ensure code quality standards are enforced across the entire schema-compliant WCT codebase.

## Important Schema Implementation Notes

**Schema-Driven Development Guidelines:**
- All connectors must implement `get_output_schema()` and schema-specific transform methods
- All plugins must implement `get_input_schema()`, `get_output_schema()`, and `process_data()` with Message objects
- Plugins no longer need to implement `validate_input()` - validation is handled by the Message mechanism
- Use `@override` decorators for all abstract method implementations
- Schema names must match between connector outputs and plugin inputs for automatic data flow
- JSON schema files in `src/wct/schemas/` define the structure for runtime validation
- Runbooks specify schema names (e.g., `input_schema_name: "text"`) not file paths
- The executor automatically matches schemas and uses automatic validation in `process()`

**Message-Based Validation System:**
- All plugins now use Message objects for unified data flow between connectors and plugins
- Input and output Messages are automatically validated against declared schemas
- The `process()` method handles Message validation transparently
- Plugin implementations work with Message objects in `process_data()` methods
- Schema files are discovered dynamically across multiple search paths
- Validation errors provide detailed messages about schema compliance failures

**Testing Schema Components:**
- Use `uv run wct run sample_runbook.yaml -v` to see detailed schema matching and validation
- The executor logs which connectors are skipped due to unneeded schemas
- Schema validation errors provide clear messages about data structure mismatches
- Test both valid and invalid data to verify comprehensive validation coverage
