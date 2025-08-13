# WCT Test Suite

This directory contains comprehensive tests for the Waivern Compliance Tool, mirroring the `src/wct/` structure for easy navigation and ensuring production-ready code quality.

## Test Coverage Overview

WCT maintains comprehensive test coverage across all components:

- **Connectors**: FilesystemConnector, MySQLConnector, SourceCodeConnector with comprehensive integration tests
- **Analysers**: Personal data analyser, processing purpose analyser with real-world test scenarios
- **Schema System**: JSON Schema validation, Message system, runbook configuration
- **Core Components**: Executor, logging, rulesets with edge case coverage
- **Extractors**: Source code analysis (functions, classes) with 35+ comprehensive tests

## Directory Structure

```
tests/
├── __init__.py                     # Test package init
├── README.md                       # This documentation
└── wct/                           # Mirror of src/wct/ structure
    ├── __init__.py
    ├── connectors/                # Connector integration tests
    │   ├── filesystem/
    │   │   └── test_connector.py  # FilesystemConnector comprehensive tests
    │   ├── mysql/
    │   │   └── test_connector.py  # MySQLConnector integration tests
    │   └── source_code/
    │       └── extractors/
    │           ├── test_functions.py  # FunctionExtractor tests (16 tests)
    │           └── test_classes.py   # ClassExtractor tests (19 tests)
    ├── analysers/                 # Analyser functionality tests
    │   └── personal_data_analyser/
    │       ├── test_analyser.py   # Core analyser tests
    │       ├── test_source_code_handler_architecture.py
    │       └── source_code_mock_php/  # Realistic PHP test data (25 files)
    ├── schemas/                   # Schema validation tests
    │   ├── test_base.py          # Base schema functionality
    │   ├── test_standard_input.py
    │   ├── test_personal_data_finding.py
    │   ├── test_processing_purpose_finding.py
    │   ├── test_source_code.py
    │   └── test_runbook.py       # Runbook schema validation
    ├── rulesets/                 # Pattern and rule tests
    │   ├── test_base.py
    │   ├── test_personal_data.py
    │   ├── test_processing_purposes.py
    │   └── test_types.py
    ├── prompts/
    │   └── __init__.py
    ├── test_executor.py          # Pipeline execution tests
    ├── test_logging.py           # Logging configuration tests
    ├── test_message.py           # Message system tests
    └── test_runbook.py           # Runbook loading tests
```

## Testing Philosophy

WCT follows **industrial best practices** for test development:

### 🎯 **Public API Focus**
- Tests focus on public interfaces, not implementation details
- No testing of private methods or internal constants
- Black-box testing approach for component reliability

### 🔒 **Proper Encapsulation**
- No imports of private constants or methods
- Tests use only public APIs that users would access
- Validates component behaviour through documented interfaces

### 🌍 **Real-World Scenarios**
- Comprehensive test fixtures with realistic data
- Temporary files and databases for integration testing
- Edge cases based on actual usage patterns

### 📊 **Comprehensive Coverage**
- **35 extractor tests** across function and class analysis
- **Multiple test categories** per component: initialisation, basic cases, edge cases, complex scenarios
- **British English** spelling throughout test documentation
- **Type safety** with comprehensive validation

## Key Test Features

### Connector Tests
- **Filesystem**: File encoding, directory traversal, exclude patterns, large file handling
- **MySQL**: Database connectivity, schema extraction, connection pooling, error handling
- **Source Code**: PHP parsing, AST extraction, docstring handling, compliance-focused data

### Extractor Tests (35 Total)
- **FunctionExtractor** (16 tests): PHP function analysis, parameter extraction, docstring parsing
- **ClassExtractor** (19 tests): Class structure analysis, method extraction, inheritance handling
- **Edge Cases**: Invalid syntax, anonymous functions, empty files, complex nested structures
- **Compliance Focus**: Validates exclusion of non-relevant fields (visibility, return_type, etc.)

### Schema Validation Tests
- JSON Schema compliance across all data flow schemas
- Message system validation with automatic error reporting
- Runbook configuration validation with cross-reference checking

## Running Tests

### Basic Commands
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov

# Run specific test categories
uv run pytest tests/wct/connectors/     # All connector tests
uv run pytest tests/wct/schemas/        # All schema tests
uv run pytest tests/wct/rulesets/       # All ruleset tests
```

### Specific Component Tests
```bash
# Connector integration tests
uv run pytest tests/wct/connectors/filesystem/test_connector.py
uv run pytest tests/wct/connectors/mysql/test_connector.py

# Comprehensive extractor tests
uv run pytest tests/wct/connectors/source_code/extractors/ -v

# Core system tests
uv run pytest tests/wct/test_executor.py
uv run pytest tests/wct/test_message.py
```

### Development Testing
```bash
# Run tests in watch mode during development
uv run pytest --watch tests/wct/connectors/

# Run only failed tests
uv run pytest --lf

# Run tests for modified files
uv run pytest --testmon
```

## Test Naming Conventions

### File Naming
- Test files: `test_<module_name>.py` matching source files
- Example: `src/wct/connectors/filesystem/connector.py` → `tests/wct/connectors/filesystem/test_connector.py`

### Class Naming
- Test classes: `Test<ComponentName><Category>` for organisation
- Examples: `TestFunctionExtractorInitialisation`, `TestFilesystemConnectorValidation`

### Method Naming
- Test methods: `test_<behaviour_description>` with clear, descriptive names
- British English spelling throughout
- Examples: `test_initialisation_with_default_language`, `test_extract_class_with_docstring`

## Adding New Tests

### 1. Create Test Structure
```bash
# Create test file in corresponding location
touch tests/wct/your_component/test_your_module.py
```

### 2. Follow Established Patterns
```python
"""Tests for YourModule following WCT testing standards."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from wct.your_component.your_module import YourClass

class TestYourComponentInitialisation:
    """Test component initialisation and basic properties."""

    def test_initialisation_with_default_parameters(self):
        """Test that component initialises correctly with defaults."""
        component = YourClass()
        assert component.property == "expected_value"

class TestYourComponentBasicCases:
    """Test standard use cases and functionality."""

    def test_basic_functionality_with_valid_input(self):
        """Test core functionality with realistic input."""
        # Use temporary files, realistic data
        with tempfile.NamedTemporaryFile() as f:
            # Test implementation
            pass

class TestYourComponentEdgeCases:
    """Test error handling and edge cases."""

    def test_handles_invalid_input_gracefully(self):
        """Test component handles malformed input appropriately."""
        # Test edge cases, error conditions
        pass
```

### 3. Include Test Categories
- **Initialisation Tests**: Constructor behaviour, parameter validation
- **Basic Cases**: Standard functionality with realistic inputs
- **Edge Cases**: Error handling, malformed input, boundary conditions
- **Complex Scenarios**: Real-world usage patterns, integration testing
- **Data Structure**: Validate output format, required fields, type safety

### 4. Add Comprehensive Coverage
- Test all public methods and properties
- Include realistic test fixtures and temporary files
- Cover error conditions and edge cases
- Validate data structure requirements
- Follow British English spelling

## Mock Data and Fixtures

### Realistic Test Data
- **Source Code Mock PHP**: 25 realistic PHP files with personal data patterns
- **Database Fixtures**: Sample MySQL schemas with compliance-relevant data
- **File Content**: Realistic file content with various encoding and format patterns

### Temporary Resources
- Use `tempfile` for file system tests
- Create temporary databases for MySQL testing
- Clean up resources in test teardown
- Realistic data that mirrors production usage

## Best Practices

### ✅ Do's
1. **Test Public APIs Only**: Focus on interfaces users interact with
2. **Use Realistic Data**: Create meaningful test scenarios
3. **Clean Up Resources**: Always clean up temporary files/databases
4. **Follow Naming Conventions**: British English, descriptive method names
5. **Include Edge Cases**: Test error conditions and boundary cases
6. **Document Purpose**: Clear docstrings explaining what each test validates

### ❌ Don'ts
1. **Don't Test Private Methods**: Focus on public behaviour
2. **Don't Import Private Constants**: Use only public interfaces
3. **Don't Skip Cleanup**: Always clean up temporary resources
4. **Don't Use American Spelling**: Follow British English throughout
5. **Don't Skip Error Cases**: Always test error handling
6. **Don't Create Brittle Tests**: Focus on behaviour, not implementation

## Continuous Integration

Tests run automatically on:
- Pull request creation and updates
- Pushes to main branch
- Pre-commit hooks for quality assurance

### Pre-commit Testing
```bash
# Install pre-commit hooks
uv run pre-commit install

# Run all quality checks
uv run pre-commit run --all-files
```

The test suite ensures WCT maintains production-ready quality with comprehensive validation across all components.
