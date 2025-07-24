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
- `uv run wct analyze <runbook.yaml>` - Run WCT analysis with a runbook
- `uv run wct list-connectors` - List available connectors
- `uv run wct list-plugins` - List available plugins
- `uv run wct validate-runbook <runbook.yaml>` - Validate a runbook

**Logging Options:**
All WCT commands support logging configuration:
- `--log-level DEBUG` - Show all debug information
- `--log-level INFO` - Show informational messages (default)
- `--log-level WARNING` - Show warnings and errors only
- `--log-level ERROR` - Show errors only
- `--log-level CRITICAL` - Show critical errors only
- `--verbose` or `-v` - Shortcut for `--log-level DEBUG`

Examples:
- `uv run wct analyze runbook.yaml --log-level DEBUG` - Detailed debugging
- `uv run wct analyze runbook.yaml -v` - Verbose output
- `uv run wct list-connectors --log-level WARNING` - Minimal output

## Architecture Overview

This codebase implements WCT (Waivern Compliance Tool), a modern compliance analysis framework:

### WCT System Architecture
- **Entry point:** `src/wct/__main__.py`
- **Core orchestrator:** `src/wct/orchestrator.py`
- **Configuration:** YAML runbooks defining connectors, plugins, and execution order
- **Architecture:** Plugin-based system with connectors for data extraction and plugins for analysis

### Key Components
- **Connectors:** Extract data from various sources (files, databases, etc.) - **Modular Architecture**
  - File connector (`src/wct/connectors/file/`)
  - MySQL connector (`src/wct/connectors/mysql/`)
  - WordPress connector (`src/wct/connectors/wordpress/`)
- **Plugins:** Process extracted data to perform compliance analysis - **Modular Architecture**
  - File content analyser (`src/wct/plugins/file_content_analyser/`)
  - Personal data analyser (`src/wct/plugins/personal_data_analyser/`)
- **Orchestrator:** Manages the pipeline execution and data flow between components
- **Rulesets:** Reusable rule definitions for compliance checks
  - Personal data ruleset (`src/wct/rulesets/personal_data.py`)

### Modular Component Structure
Each connector and plugin is organized as an independent module:
- **Directory Structure:** Each component has its own directory with `__init__.py` and implementation files
- **Encapsulation:** Components can contain supporting files, utilities, configuration, and tests
- **Extensibility:** Easy to add complex logic and dependencies per component
- **Import Compatibility:** Main `__init__.py` files maintain backward-compatible imports

### Configuration Format
WCT uses runbook YAML files with three main sections:
- `connectors`: Define data sources and their configuration
- `plugins`: Specify analysis plugins to run
- `execution_order`: Control the sequence of connector→plugin execution

### Base Classes and Extension Points
- **Connector base:** `src/wct/connectors/base.py`
- **Plugin base:** `src/wct/plugins/base.py`
- **Ruleset base:** `src/wct/rulesets/base.py`
- All components support dynamic registration and configuration

## Project Structure Notes
- Uses `uv` for dependency management
- Type annotations are enforced with `basedpyright`
- Main package is `wct` located in `src/wct/`
- Sample configurations: `wct.yaml` and `sample_runbook.yaml`

## Development Setup

**Pre-commit hooks are configured** for the WCT system:
- Ruff linting and formatting
- Basic file checks (YAML/TOML validation, trailing whitespace, etc.)
- Security checks with bandit
- Type checking with basedpyright (currently disabled while WCT architecture stabilizes)

The pre-commit hooks ensure code quality standards are enforced across the entire WCT codebase.
