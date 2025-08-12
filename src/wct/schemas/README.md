# WCT Schemas Directory

This directory contains WCT's strongly typed schema system that provides JSON Schema-based validation and type safety throughout the compliance analysis framework.

## Schema Architecture Overview

WCT uses two distinct types of schemas that serve different purposes in the system:

### 📊 **Data Flow Schemas**
*Validate data that flows between connectors and analysers*

These schemas define the structure of data as it moves through the WCT analysis pipeline:

- **`StandardInputSchema`** - Common input format for filesystem and basic connectors
- **`SourceCodeSchema`** - Source code analysis input format with file content and metadata
- **`PersonalDataFindingSchema`** - Output format for personal data analysis results
- **`ProcessingPurposeFindingSchema`** - Output format for GDPR processing purpose analysis results

**Purpose**: Ensure type-safe data exchange between system components during runtime analysis.

### ⚙️ **Configuration Schemas**
*Validate configuration files and system setup*

These schemas define the structure of configuration files that set up and orchestrate WCT:

- **`RunbookSchema`** - YAML runbook configuration files that define analysis pipelines

**Purpose**: Validate configuration files at load time to ensure proper system setup before execution.

## Key Differences

| Aspect | Data Flow Schemas | Configuration Schemas |
|--------|-------------------|----------------------|
| **Validates** | Runtime data between components | Configuration files (YAML/JSON) |
| **Used by** | Connectors, Analysers, Message system | RunbookLoader, CLI validation |
| **When** | During analysis execution | At system startup/configuration load |
| **Content** | Analysis results, file content, findings | Pipeline definitions, component configs |
| **Examples** | Personal data findings, source code content | Runbook YAML files |

## Directory Structure

```
src/wct/schemas/
├── README.md                   # This documentation
├── __init__.py                 # Schema exports and module documentation
├── base.py                     # Abstract Schema base class and JsonSchemaLoader
├──
├── # Data Flow Schema Classes
├── standard_input.py           # Standard input data format
├── source_code.py              # Source code analysis format
├── personal_data_finding.py    # Personal data analysis results
├── processing_purpose_finding.py # Processing purpose analysis results
├──
├── # Configuration Schema Classes
├── runbook.py                  # Runbook configuration validation
├──
└── json_schemas/               # Versioned JSON Schema definitions
    ├── standard_input/1.0.0/
    ├── source_code/1.0.0/
    ├── personal_data_finding/1.0.0/
    ├── processing_purpose_finding/1.0.0/
    └── runbook/1.0.0/
        ├── runbook.json        # JSON Schema for runbook validation
        └── runbook.sample.yaml # Example runbook configuration
```

## Schema Versioning

All schemas follow WCT's versioned architecture:

- **Schema classes** (e.g., `StandardInputSchema`) provide the Python interface
- **JSON Schema files** in `json_schemas/{name}/{version}/` contain validation rules
- **Version matching** ensures loaded schema matches the class version
- **Automatic loading** with caching for performance

Example:
```python
from wct.schemas import StandardInputSchema

# Loads JSON schema from json_schemas/standard_input/1.0.0/standard_input.json
schema = StandardInputSchema()
data = schema.schema  # Returns JSON Schema dict for validation
```

## Usage Patterns

### Data Flow Validation (Connectors & Analysers)

```python
from wct.schemas import StandardInputSchema
from wct.message import Message

# Connector extracts data and creates validated message
schema = StandardInputSchema()
message = Message(content=extracted_data, schema=schema)
message.validate()  # Ensures data matches schema

# Analyser processes validated input
processed_result = analyser.process_data(message)
```

### Configuration Validation (System Setup)

```python
from wct.runbook import RunbookLoader

# Load and validate runbook configuration
runbook = RunbookLoader.load(Path("runbooks/analysis.yaml"))
# RunbookSchema automatically validates structure, required fields,
# connector/analyser configurations, and execution steps
```

## Adding New Schemas

### For Data Flow Schemas:

1. **Create schema class** in `schemas/{name}.py` extending `Schema`
2. **Add JSON Schema file** in `json_schemas/{name}/{version}/{name}.json`
3. **Create sample file** in `json_schemas/{name}/{version}/{name}.sample.json`
4. **Export in `__init__.py`** and update documentation
5. **Add comprehensive tests** in `tests/wct/schemas/test_{name}.py`

### For Configuration Schemas:

1. **Create schema class** following `RunbookSchema` pattern
2. **Add JSON Schema file** with validation rules for the configuration format
3. **Create sample file** showing proper configuration structure
4. **Integrate with loading/parsing logic** in the relevant system component
5. **Add tests** covering both schema validation and integration

## Testing

Each schema has comprehensive test coverage:

- **Schema class tests**: Interface, versioning, immutability
- **JSON Schema validation tests**: Structure requirements, field validation, error handling
- **Integration tests**: Real-world usage with system components

Run schema tests:
```bash
uv run pytest tests/wct/schemas/ -v
```
