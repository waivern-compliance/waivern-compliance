# Tests Directory Structure

This directory mirrors the `src/wct/` structure to make it easy to find tests for specific modules.

## Structure

```
tests/
├── __init__.py                     # Test package init
├── test_placeholder.py             # Placeholder test
├── README.md                       # This file
└── wct/                           # Mirror of src/wct/
    ├── __init__.py
    ├── connectors/                # Tests for connectors
    │   └── __init__.py
    ├── analysers/                   # Tests for analysers
    │   └── __init__.py
    ├── prompts/                   # Tests for prompts
    │   └── __init__.py
    └── rulesets/                  # Tests for rulesets
        ├── __init__.py
        └── test_processing_purposes.py  # Tests for processing_purposes.py
```

## Naming Convention

- Test files should be named `test_<module_name>.py` to match the source file
- For example: `src/wct/rulesets/processing_purposes.py` → `tests/wct/rulesets/test_processing_purposes.py`
- Test classes should be named `Test<ClassName>` (e.g., `TestProcessingPurposesRuleset`)

## Adding New Tests

When adding tests for a new module:

1. Create the test file in the corresponding location under `tests/wct/`
2. Follow the existing naming conventions
3. Add proper imports and documentation
4. Use the existing test patterns as examples

## Running Tests

```bash
# Run all tests
uv run pytest

# Run tests for a specific module
uv run pytest tests/wct/rulesets/test_processing_purposes.py

# Run tests with verbose output
uv run pytest -v

# Run tests for a specific directory
uv run pytest tests/wct/rulesets/
```
