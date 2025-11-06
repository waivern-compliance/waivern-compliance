# Schema Producers

Output schema version handlers for PersonalDataAnalyser.

## File Naming Convention

Format: `{schema_name}_{major}_{minor}_{patch}.py`

Examples:
- `personal_data_finding_1_0_0.py` - Produces personal_data_finding v1.0.0
- `personal_data_finding_1_1_0.py` - Produces personal_data_finding v1.1.0

## Module Interface

Each producer module should export a `produce()` function:

```python
def produce(internal_result: dict) -> dict:
    """Transform internal result to schema format.

    Args:
        internal_result: Analysis result in analyser's internal format

    Returns:
        Data conforming to the output schema version
    """
    pass
```

## Adding Version Support

To add support for a new schema version:
1. Create new file: `{schema_name}_{major}_{minor}_{patch}.py`
2. Implement `produce()` function for that version
3. Done - auto-discovered automatically!
