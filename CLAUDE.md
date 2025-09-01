# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Configuration

WCT supports environment variables for sensitive configuration data like database credentials. This keeps sensitive information out of runbook files that are committed to version control.

**Environment Variable Setup:**
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Edit `.env` with your actual credentials
3. Environment variables take precedence over runbook properties

**Supported Environment Variables:**

*MySQL Database:*
- `MYSQL_HOST` - Database server hostname
- `MYSQL_PORT` - Database server port (default: 3306)
- `MYSQL_USER` - Database username
- `MYSQL_PASSWORD` - Database password
- `MYSQL_DATABASE` - Database name

*LLM Configuration:*
- `ANTHROPIC_API_KEY` - Anthropic API key for AI-powered compliance analysis
- `ANTHROPIC_MODEL` - Anthropic model name (optional, defaults to claude-sonnet-4-20250514)

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
- `uv run wct run runbooks/<runbook.yaml>` - Run WCT analysis with a runbook
- `uv run wct ls-connectors` - List available connectors
- `uv run wct ls-analysers` - List available analysers
- `uv run wct validate-runbook runbooks/<runbook.yaml>` - Validate a runbook
- `uv run wct generate-schema` - Generate JSON Schema for IDE support and validation
- `uv run wct test-llm` - Test LLM connectivity and configuration

**Dependencies:**
- All connector and analyser dependencies are included by default
- `uv sync --group dev` - Install development tools only when needed for contributing

**Logging Options:**
All WCT commands support logging configuration:
- `--log-level DEBUG` - Show all debug information
- `--log-level INFO` - Show informational messages (default)
- `--log-level WARNING` - Show warnings and errors only
- `--log-level ERROR` - Show errors only
- `--log-level CRITICAL` - Show critical errors only
- `--verbose` or `-v` - Shortcut for `--log-level DEBUG`

Examples:
- `uv run wct run runbooks/samples/file_content_analysis.yaml --log-level DEBUG` - Detailed debugging
- `uv run wct run runbooks/samples/LAMP_stack.yaml -v` - Verbose output
- `uv run wct ls-connectors --log-level WARNING` - Minimal output

## Architecture Overview

This codebase implements WCT (Waivern Compliance Tool), a modern compliance analysis framework with **unified schema-driven architecture**:

### WCT Schema-Driven System Architecture
- **Entry point:** `src/wct/__main__.py`
- **Schema-aware executor:** `src/wct/executor.py`
- **Unified schema system:** `src/wct/schema.py` - `WctSchema[T]` for type-safe data flow
- **Schema definitions:** `src/wct/schemas/` - JSON schema files for validation
- **Configuration:** YAML runbooks with schema-aware execution order
- **Architecture:** Schema-compliant connectors and analysers with automatic data flow matching

### Key Components
- **Connectors:** Extract data to WCT schemas
  - Filesystem, MySQL, Source code connectors
- **Analysers:** Process data using modular analysis runners with dependency injection
  - **Personal data analyser:** Detects personal data with LLM validation (supports `standard_input`, `source_code` schemas)
  - **Processing purpose analyser:** Identifies GDPR processing purposes (supports `standard_input` schema)
- **Executor:** Automatic schema matching between connectors and analysers
- **Rulesets:** Versioned YAML-based pattern definitions with Pydantic validation for compliance analysis

### Runbook Format
```yaml
name: "Runbook Name"
description: "Description of what this runbook does"
contact: "Contact Person <email@company.com>"

connectors:
  - name: "connector_name"
    type: "connector_type"
    properties: {...}

analysers:
  - name: "analyser_name"
    type: "analyser_type"
    properties: {...}

execution:
  - name: "Execution Step Name"
    description: "Description of what this step does"
    contact: "Step Contact <email@company.com>"  # Optional
    connector: "connector_name"
    analyser: "analyser_name"
    input_schema: "schema_name"
    output_schema: "output_schema"
```

## Runbooks Directory

**Runbook Organization:**
- **`runbooks/` directory** - Centralized location for all runbook configurations
- **`runbooks/samples/` directory** - Sample runbooks for demonstration and learning
  - **`file_content_analysis.yaml`** - Simple file analysis demonstration using personal data analyser
  - **`LAMP_stack.yaml`** - Comprehensive example demonstrating personal data and processing purpose analysis on MySQL and PHP source code
- **`runbooks/README.md`** - Detailed documentation on runbook usage and creation guidelines

**Available Sample Runbooks:**
- **File content analysis**: `runbooks/samples/file_content_analysis.yaml` - Demonstrates personal data detection
- **LAMP stack analysis**: `runbooks/samples/LAMP_stack.yaml` - Comprehensive analysis with both personal data and processing purpose detection on MySQL database and PHP source code
- **Quick start**: Begin with `uv run wct run runbooks/samples/file_content_analysis.yaml -v`

## Project Structure Notes
- Uses `uv` for dependency management with all dependencies included by default
- **Core Dependencies:** `jsonschema` for comprehensive JSON schema validation, `langchain` and `langchain-anthropic` for AI-powered compliance analysis
- Type annotations are enforced with `basedpyright` (schema system is fully type-safe)
- Main package is `wct` located in `src/wct/`
- Schema definitions in `src/wct/schemas/` (JSON Schema format)
- **Ruleset architecture**: `src/wct/rulesets/data/{ruleset}/{version}/{ruleset}.yaml` - Versioned YAML configuration with Pydantic validation
- Runbook configurations: `runbooks/` directory with scenario-based runbooks organized in `samples/` subdirectory
- Sample configurations:
  - `runbooks/samples/file_content_analysis.yaml` - Simple demonstration using personal data analyser
  - `runbooks/samples/LAMP_stack.yaml` - Comprehensive multi-connector analysis

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
- All analysers must implement `get_input_schema()`, `get_output_schema()`, and `process_data()` with Message objects
- Analysers no longer need to implement `validate_input()` - validation is handled by the Message mechanism
- Use `@override` decorators for all abstract method implementations
- Schema names must match between connector outputs and analyser inputs for automatic data flow
- JSON schema files in `src/wct/schemas/` define the structure for runtime validation
- Runbooks specify schema names (e.g., `input_schema: "standard_input"`) not file paths
- The executor automatically matches schemas and uses automatic validation in `process()`

**Message-Based Validation System:**
- All analysers now use Message objects for unified data flow between connectors and analysers
- Input and output Messages are automatically validated against declared schemas
- The `process()` method handles Message validation transparently
- Analyser implementations work with Message objects in `process_data()` methods
- Schema files are discovered dynamically across multiple search paths
- Validation errors provide detailed messages about schema compliance failures

**Testing Schema Components:**
- Use `uv run wct run runbooks/sample_runbook.yaml -v` to see detailed schema matching and validation
- The executor logs which connectors are skipped due to unneeded schemas
- Schema validation errors provide clear messages about data structure mismatches
- Test both valid and invalid data to verify comprehensive validation coverage

# Git and PR Requirements

**Branch Management:**
- ALWAYS create a new branch before making commits if currently on main branch
- NEVER commit directly to main branch - always use feature/fix/docs branches
- Use descriptive branch naming conventions:
  - `feature/feature-name` - For new features
  - `fix/issue-description` - For bug fixes
  - `docs/documentation-updates` - For documentation changes
  - `refactor/component-name` - For refactoring work

**Pull Request Guidelines:**
- When creating PRs, ensure proper branch naming as described above
- Use descriptive PR titles that clearly summarize the main change
- Write comprehensive PR descriptions that summarize all changes made
- Include rationale for changes and any breaking changes
- Reference related issues or previous work when applicable

# important-instruction-reminders
DO what has been asked—nothing more, nothing less. DO NOT overcomplicate things.
NEVER create a 'backwards compatibility' branch of code unless explicitly instructed; always refactor.
ALWAYS analyse and verify that every single variable, function and class is necessary after a refactoring task. Remove all unnecessary leftover code.
DO NOT be afraid of breaking changes. Refactoring is BETTER than 'backwards compatibility'.
When doing refactoring, DO NOT try to preserve the old context in code or comments. Just update them to reflect the current state.
Adhere to software craftsmanship principles. Break large classes and functions into smaller ones to represent granular concepts.
CRITICAL: NEVER attempt to bypass code quality checks. Carefully analyse errors and determine their cause.
DO NOT attempt quick fixes for errors. If an error indicates a design flaw, advise on options to refactor the codebase.
Use British English spelling.
