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

**Running the Applications:**
- `uv run wct analyze <runbook.yaml>` - Run WCT analysis with a runbook
- `uv run wct list-connectors` - List available connectors
- `uv run wct list-plugins` - List available plugins
- `uv run wct validate-runbook <runbook.yaml>` - Validate a runbook configuration
- `uv run python -m waivern_analyser run --config <config.yaml>` - Run legacy Waivern analyser
- `uv run python -m waivern_analyser ls-plugins` - List plugins for legacy analyser

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

This codebase contains two main systems that are being unified:

### 1. WCT (Waivern Compliance Tool) - New System
- **Entry point:** `src/wct/__main__.py`
- **Core orchestrator:** `src/wct/orchestrator.py`
- **Configuration:** YAML runbooks defining connectors, plugins, and execution order
- **Architecture:** Plugin-based system with connectors for data extraction and plugins for analysis
- **Key components:**
  - **Connectors:** Extract data from various sources (files, databases, etc.)
  - **Plugins:** Process extracted data to perform compliance analysis
  - **Orchestrator:** Manages the pipeline execution and data flow between components

### 2. Waivern Analyser - Legacy System
- **Entry point:** `src/waivern_analyser/__main__.py`
- **Core analyser:** `src/waivern_analyser/analyser.py`
- **Configuration:** YAML config files with sources, connectors, and rulesets
- **Architecture:** Three-stage pipeline: sources → connectors → rulesets

### Plugin System
- **Location:** `src/plugins/` contains external plugins (workspace members)
- **WordPress plugin:** `src/plugins/wordpress/` - Example plugin for WordPress compliance analysis
- **Plugin discovery:** Both systems use plugin registries for component discovery
- **Base classes:** `src/wct/plugins/base.py` and `src/wct/connectors/base.py`

### Configuration Patterns
- **WCT:** Uses runbook YAML files with `connectors`, `plugins`, and `execution_order` sections
- **Legacy:** Uses config YAML files with `sources`, `connectors`, and `rulesets` sections
- **Base config:** All config classes inherit from `src/waivern_analyser/config/base.py:Config` (Pydantic models)

### Key Abstractions
- **Connectors:** Bridge between data sources and analysis plugins
- **Plugins/Rulesets:** Perform the actual compliance analysis logic
- **Sources:** Represent data input sources (files, databases, etc.)
- **Schema-based data flow:** Components communicate through well-defined data schemas

## Project Structure Notes
- Uses `uv` workspace with `src/plugins/*` as workspace members
- Type annotations are enforced with `basedpyright`
- Main package is `wct` (new system), with `waivern_analyser` as legacy
- Sample configurations: `wct.yaml` and `sample_runbook.yaml`

## Development Setup

**Pre-commit hooks are configured** to automatically run on the **new WCT system only**:
- Ruff linting and formatting (excludes legacy `src/waivern_analyser/` and `src/plugins/`)
- Basic file checks (YAML/TOML validation, trailing whitespace, etc.)
- Security checks with bandit (excludes legacy code)
- Type checking with basedpyright (currently disabled while WCT architecture stabilizes)

**Legacy code exclusions:** The pre-commit hooks intentionally ignore:
- `src/waivern_analyser/` - Legacy Waivern Analyser system being migrated
- `src/plugins/` - Plugin system being migrated to new WCT architecture
- `tests/test_plugins.py` - Tests for legacy plugin system

This approach ensures code quality standards are enforced for new WCT development while allowing legacy code migration to proceed without constant pre-commit failures.
