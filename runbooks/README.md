# WCT Runbooks

This directory contains various runbook configurations for different testing and analysis scenarios.

## Available Runbooks

### `sample_runbook.yaml`
A comprehensive example runbook that demonstrates:
- File content analysis
- MySQL database analysis
- PHP source code analysis
- Personal data detection across multiple data sources
- Multi-analyser execution with different configurations

## Usage

Run any runbook from the project root:

```bash
# Validate a runbook
uv run wct validate-runbook runbooks/sample_runbook.yaml

# Execute a runbook
uv run wct run runbooks/sample_runbook.yaml

# Execute with debug logging
uv run wct run runbooks/sample_runbook.yaml --log-level DEBUG
```

## Creating New Runbooks

When creating new runbooks for specific scenarios:

1. Use relative paths from project root (e.g., `./tests/...`)
2. Follow the established naming convention: `scenario_description.yaml`
3. Include appropriate metadata for compliance frameworks
4. Document the purpose and expected outcomes

## Scenario Ideas

Future runbooks could include:
- `file_only_analysis.yaml` - Focus solely on file content analysis
- `database_only_analysis.yaml` - MySQL/database-specific analysis
- `source_code_only_analysis.yaml` - Source code analysis without other connectors
- `llm_validation_test.yaml` - Testing LLM validation features
- `performance_test.yaml` - Large dataset performance testing
