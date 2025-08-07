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

**Example .env file:**
```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=your_database_name

# LLM Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

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
- `uv run wct list-connectors` - List available connectors
- `uv run wct ls-analysers` - List available analysers
- `uv run wct validate-runbook runbooks/<runbook.yaml>` - Validate a runbook
- `uv run wct test-llm` - Test LLM connectivity and configuration

**Dependency Groups:**
WCT uses optional dependency groups for specific features:
- `uv sync --group mysql` - Install MySQL connector dependencies (pymysql, cryptography)
- `uv sync --group source-code` - Install source code analysis dependencies (tree-sitter, tree-sitter-php)
- `uv sync --group dev` - Install development tools
- `uv sync --group mysql --group source-code --group dev` - Install multiple groups

**Core Dependencies:**
LLM functionality (langchain, langchain-anthropic) is now included as core dependencies and available by default for AI-powered compliance analysis and validation.

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
- `uv run wct list-connectors --log-level WARNING` - Minimal output

## Architecture Overview

This codebase implements WCT (Waivern Compliance Tool), a modern compliance analysis framework with **unified schema-driven architecture**:

### WCT Schema-Driven System Architecture
- **Entry point:** `src/wct/__main__.py`
- **Schema-aware executor:** `src/wct/executor.py`
- **Unified schema system:** `src/wct/schema.py` - `WctSchema[T]` for type-safe data flow
- **Schema definitions:** `src/wct/schemas/` - JSON schema files for validation
- **Configuration:** YAML runbooks with schema-aware execution order
- **Architecture:** Schema-compliant connectors and analysers with automatic data flow matching

### Key Schema-Compliant Components
- **Schema-Compliant Connectors:** Extract and transform data to WCT schemas - **Modular Architecture**
  - Filesystem connector (`src/wct/connectors/filesystem/`) - Produces "text" schema
  - MySQL connector (`src/wct/connectors/mysql/`) - Produces "mysql_database" schema
  - Source code connector (`src/wct/connectors/source_code/`) - Produces "source_code" schema
  - WordPress connector (`src/wct/connectors/wordpress/`) - Produces "wordpress_site" schema
- **Schema-Aware Analysers:** Process validated data with input/output schema contracts - **Modular Architecture**
  - Personal data analyser (`src/wct/analysers/personal_data_analyser/`) - Enhanced with LLM-powered false positive detection
- **Schema-Aware Executor:** Matches connector output schemas to analyser input schemas automatically
- **Schema System:** `WctSchema[T]` with JSON schema validation for runtime type safety
- **Rulesets:** Schema-compliant reusable rule definitions for compliance checks
  - Personal data ruleset (`src/wct/rulesets/personal_data.py`)

### Schema-Driven Modular Architecture
Each connector and analyser is organized as an independent module with schema contracts:
- **Directory Structure:** Each component has its own directory with `__init__.py` and implementation files
- **Schema Contracts:** Clear input/output schema declarations for type safety
- **Dependency Isolation:** Optional dependencies grouped by component (e.g., `mysql` group, `source-code` group)
- **Encapsulation:** Components can contain supporting files, utilities, configuration, and tests
- **Extensibility:** Easy to add complex logic and dependencies per component
- **Import Compatibility:** Main `__init__.py` files maintain backward-compatible imports

### Modern Execution Configuration Format
WCT runbooks use a comprehensive execution format with explicit connector-analyser mapping:

**Required Execution Format:**
```yaml
execution:
  - connector: "connector_name"
    analyser: "analyser_name"
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
- `analysers`: Specify analysis analysers with metadata
- `execution`: Comprehensive execution steps with connector-analyser mapping and context

### Schema-Compliant Base Classes with Automatic Validation
- **Connector base:** `src/wct/connectors/base.py` - Abstract connector with `WctSchema[T]` support and transform methods
- **Analyser base:** `src/wct/analysers/base.py` - Abstract analyser with Message-based architecture and automatic validation
  - `process()` - Automatic end-to-end Message validation with processing
  - `process_data()` - Abstract method for analyser-specific processing logic using Message objects
  - Message validation handled automatically by base class (no manual validation needed)
- **Ruleset base:** `src/wct/rulesets/base.py` - Schema-aware rule definitions
- **Schema system:** `src/wct/schema.py` - `WctSchema[T]` generic container for type safety
- All components support dynamic registration, configuration, and comprehensive schema validation

## Runbooks Directory

**Runbook Organization:**
- **`runbooks/` directory** - Centralized location for all runbook configurations
- **`runbooks/samples/` directory** - Sample runbooks for demonstration and learning
  - **`file_content_analysis.yaml`** - Simple file analysis demonstration using personal data analyser
  - **`LAMP_stack.yaml`** - Comprehensive example demonstrating file, database, and source code analysis
- **`runbooks/README.md`** - Detailed documentation on runbook usage and creation guidelines

**Available Sample Runbooks:**
- **File content analysis**: `runbooks/samples/file_content_analysis.yaml` - Demonstrates personal data detection
- **LAMP stack analysis**: `runbooks/samples/LAMP_stack.yaml` - Multi-connector analysis for complete stack compliance
- **Quick start**: Begin with `uv run wct run runbooks/samples/file_content_analysis.yaml -v`

**Scenario-Based Testing:**
Create focused runbooks for specific testing scenarios:
- Database-only analysis: `runbooks/database_analysis.yaml`
- Source code analysis: `runbooks/source_code_analysis.yaml`
- LLM validation testing: `runbooks/llm_validation_test.yaml`
- Performance testing: `runbooks/performance_test.yaml`

**Best Practices:**
- Use relative paths from project root (e.g., `./tests/...`)
- Follow naming convention: `scenario_description.yaml`
- Include appropriate metadata for compliance frameworks
- Document purpose and expected outcomes in runbook descriptions

## Project Structure Notes
- Uses `uv` for dependency management with optional dependency groups
- **Core Dependencies:** `jsonschema` for comprehensive JSON schema validation, `langchain` and `langchain-anthropic` for AI-powered compliance analysis
- Type annotations are enforced with `basedpyright` (schema system is fully type-safe)
- Main package is `wct` located in `src/wct/`
- Schema definitions in `src/wct/schemas/` (JSON Schema format)
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
- Runbooks specify schema names (e.g., `input_schema_name: "text"`) not file paths
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

## Source Code Analysis Capabilities

**Source Code Connector** (`src/wct/connectors/source_code/`):
- Parses source code using Tree-sitter for accurate AST analysis
- Supports PHP (extensible to JavaScript, Python, Java, etc.)
- Produces comprehensive "source_code" schema with compliance-focused extractions
- **Requires:** `uv sync --group source-code` for tree-sitter dependencies

**Key Analysis Features:**
- **Function/Class Extraction:** Parameters, return types, visibility, inheritance
- **Database Interactions:** SQL queries, parameterization status, user input detection
- **Data Collection Patterns:** Form fields, session/cookie access, PII indicators
- **AI/ML Usage Detection:** ML library imports, API calls, prediction code
- **Security Patterns:** Authentication, encryption, validation, sanitization methods
- **Third-party Integrations:** External service calls, data sharing detection
- **Compliance Metadata:** File complexity, line counts, modification timestamps

**Usage Example:**
```yaml
connectors:
  - name: "php_source"
    type: "source_code"
    properties:
      path: "./src"
      language: "php"
      file_patterns: ["**/*.php"]
      max_file_size: 10485760  # 10MB
      max_files: 4000  # Maximum number of files to process (default: 4000)
      analysis_depth: "detailed"

execution:
  - connector: "php_source"
    analyser: "compliance_analyzer"
    input_schema_name: "source_code"
```

**Extensible Architecture:**
- Modular extractors in `src/wct/connectors/source_code/extractors/`
- Easy to add new programming languages via tree-sitter grammars
- Schema-driven output ensures compatibility with downstream analysis analysers
