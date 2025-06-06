# Waivern Connectors Core

Core framework for building data connectors in the Waivern Analyser ecosystem. This package provides the base classes and interfaces that all connectors must implement.

## Overview

Connectors are responsible for extracting and gathering data from various sources such as:
- Source code repositories
- Databases
- APIs
- File systems
- Cloud services
- Configuration files

## Architecture

The core connector framework defines three main components:

### 1. ConnectorInputSchema
A dataclass that defines the input parameters for a connector:

```python
from dataclasses import dataclass
from waivern_connectors_core import ConnectorInputSchema

@dataclass(frozen=True, slots=True)
class MyConnectorInputSchema(ConnectorInputSchema):
    source_path: str
    include_patterns: list[str] = None
    exclude_patterns: list[str] = None
```

### 2. ConnectorOutputSchema
A dataclass that defines the output format of a connector:

```python
from dataclasses import dataclass
from waivern_connectors_core import ConnectorOutputSchema

@dataclass(frozen=True, slots=True)
class MyConnectorOutputSchema(ConnectorOutputSchema):
    files_analyzed: int
    data: dict
    metadata: dict
```

### 3. Connector
The abstract base class that all connectors must inherit from:

```python
from waivern_connectors_core import Connector

class MyConnector(Connector):
    def run(self, input: MyConnectorInputSchema) -> MyConnectorOutputSchema:
        # Implement your data extraction logic here
        return MyConnectorOutputSchema(
            files_analyzed=10,
            data={"key": "value"},
            metadata={"timestamp": "2024-01-01"}
        )
```

## Creating a Custom Connector

### Step 1: Define Input Schema

```python
from dataclasses import dataclass
from waivern_connectors_core import ConnectorInputSchema

@dataclass(frozen=True, slots=True)
class DatabaseConnectorInputSchema(ConnectorInputSchema):
    connection_string: str
    query: str
    timeout: int = 30
```

### Step 2: Define Output Schema

```python
from dataclasses import dataclass
from waivern_connectors_core import ConnectorOutputSchema

@dataclass(frozen=True, slots=True)
class DatabaseConnectorOutputSchema(ConnectorOutputSchema):
    rows_count: int
    columns: list[str]
    data: list[dict]
    execution_time: float
```

### Step 3: Implement the Connector

```python
import time
from waivern_connectors_core import Connector

class DatabaseConnector(Connector):
    def run(self, input: DatabaseConnectorInputSchema) -> DatabaseConnectorOutputSchema:
        start_time = time.time()
        
        # Your database connection and query logic here
        # This is a simplified example
        rows = [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"}
        ]
        
        execution_time = time.time() - start_time
        
        return DatabaseConnectorOutputSchema(
            rows_count=len(rows),
            columns=["id", "name"],
            data=rows,
            execution_time=execution_time
        )
```

### Step 4: Create a Plugin (Optional)

To make your connector discoverable by the Waivern Analyser framework:

```python
from waivern_analyser.plugin import Plugin

class DatabaseConnectorPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "database-connector"
    
    @classmethod
    def get_connectors(cls):
        return (DatabaseConnector(),)
```

### Step 5: Register the Plugin

Add to your package's `pyproject.toml`:

```toml
[project.entry-points."waivern-plugins"]
database-connector = "your_package:DatabaseConnectorPlugin"
```

## Design Principles

### Immutability
- Input and output schemas use `frozen=True` dataclasses
- This ensures data integrity and prevents accidental modifications

### Type Safety
- All schemas are strongly typed
- Use type hints for better IDE support and runtime validation

### Slots Optimization
- Schemas use `slots=True` for memory efficiency
- Important for processing large datasets

### Single Responsibility
- Each connector should focus on one type of data source
- Keep the `run` method focused and delegate complex logic to helper methods

## Testing

Example test for a connector:

```python
from waivern_connectors_core import ConnectorInputSchema, ConnectorOutputSchema

def test_my_connector():
    connector = MyConnector()
    input_data = MyConnectorInputSchema(source_path="/path/to/data")
    
    result = connector.run(input_data)
    
    assert isinstance(result, MyConnectorOutputSchema)
    assert result.files_analyzed >= 0
    assert isinstance(result.data, dict)
```

## Best Practices

1. **Error Handling**: Implement proper error handling and provide meaningful error messages
2. **Logging**: Use structured logging to help with debugging
3. **Configuration**: Make connectors configurable through input schemas
4. **Performance**: Consider memory usage and processing time for large datasets
5. **Documentation**: Document the expected input format and output structure
6. **Validation**: Validate input parameters before processing

## Integration with Waivern Analyser

Connectors are automatically discovered and loaded by the Waivern Analyser framework when:

1. They are properly registered as plugins via entry points
2. They inherit from the `Connector` base class
3. They implement the required `run` method

The framework handles plugin loading, dependency injection, and execution orchestration.

## Dependencies

This package has no external dependencies and only requires Python 3.9+.

## Contributing

When contributing to the connectors core framework:

1. Maintain backward compatibility
2. Add comprehensive tests for any changes
3. Update documentation for new features
4. Follow the existing code style and patterns