# Schema Readers

Input schema version handlers for PersonalDataAnalyser.

## File Naming Convention

Format: `{schema_name}_{major}_{minor}_{patch}.py`

Examples:
- `standard_input_1_0_0.py` - Reads standard_input v1.0.0
- `standard_input_1_1_0.py` - Reads standard_input v1.1.0

## Module Interface

Each reader module should export a `read()` function:

```python
def read(content: dict) -> dict:
    """Transform schema data to internal format.

    Args:
        content: Data conforming to the schema version

    Returns:
        Transformed data in analyser's internal format
    """
    pass
```

## Adding Version Support

To add support for a new schema version:
1. Create new file: `{schema_name}_{major}_{minor}_{patch}.py`
2. Implement `read()` function for that version
3. Done - auto-discovered automatically!
