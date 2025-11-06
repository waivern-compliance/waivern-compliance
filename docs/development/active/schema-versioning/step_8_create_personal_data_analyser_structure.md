# Step 8: Create Directory Structure for PersonalDataAnalyser

**Phase:** 3 - Proof of Concept Component
**Dependencies:** Step 7 complete (Phase 2 done)
**Estimated Scope:** Directory setup and scaffolding
**Status:** ✅ Completed

## Purpose

Create the `schema_readers/` and `schema_producers/` directories for PersonalDataAnalyser and set up the module structure. This establishes the reader/producer pattern.

## Current State

PersonalDataAnalyser has:
- Hardcoded version support: `_SUPPORTED_INPUT_SCHEMAS`, `_SUPPORTED_OUTPUT_SCHEMAS`
- Version-specific logic embedded in main analyser class
- No separate modules for different versions

## Target State

```
libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/
├── analyser.py
├── factory.py
├── schemas/
│   └── personal_data_finding.py
├── schema_readers/           # NEW
│   ├── __init__.py          # NEW
│   └── standard_input_1_0_0.py  # NEW (next step)
└── schema_producers/         # NEW
    ├── __init__.py          # NEW
    └── personal_data_finding_1_0_0.py  # NEW (next step)
```

## Implementation Steps

### 1. Create Directories

```bash
cd libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser

mkdir -p schema_readers
mkdir -p schema_producers
```

### 2. Create __init__.py Files

Create `schema_readers/__init__.py`:
```python
"""Input schema readers for PersonalDataAnalyser.

Each module in this directory handles reading a specific version of an input schema.
Modules are named: {schema_name}_{major}_{minor}_{patch}.py
"""
```

Create `schema_producers/__init__.py`:
```python
"""Output schema producers for PersonalDataAnalyser.

Each module in this directory handles producing a specific version of an output schema.
Modules are named: {schema_name}_{major}_{minor}_{patch}.py
"""
```

### 3. Document the Pattern

Create `schema_readers/README.md`:
```markdown
# Schema Readers

Input schema version handlers for PersonalDataAnalyser.

## File Naming Convention

Format: `{schema_name}_{major}_{minor}_{patch}.py`

Examples:
- `standard_input_1_0_0.py` - Reads standard_input v1.0.0
- `standard_input_1_1_0.py` - Reads standard_input v1.1.0

## Module Interface

Each reader module should export a `read()` function:

\```python
def read(content: dict) -> dict:
    """Transform schema data to internal format.

    Args:
        content: Data conforming to the schema version

    Returns:
        Transformed data in analyser's internal format
    """
    pass
\```

## Adding Version Support

To add support for a new schema version:
1. Create new file: `{schema_name}_{major}_{minor}_{patch}.py`
2. Implement `read()` function for that version
3. Done - auto-discovered automatically!
```

Create `schema_producers/README.md`:
```markdown
# Schema Producers

Output schema version handlers for PersonalDataAnalyser.

## File Naming Convention

Format: `{schema_name}_{major}_{minor}_{patch}.py`

Examples:
- `personal_data_finding_1_0_0.py` - Produces personal_data_finding v1.0.0
- `personal_data_finding_1_1_0.py` - Produces personal_data_finding v1.1.0

## Module Interface

Each producer module should export a `produce()` function:

\```python
def produce(internal_result: dict) -> dict:
    """Transform internal result to schema format.

    Args:
        internal_result: Analysis result in analyser's internal format

    Returns:
        Data conforming to the output schema version
    """
    pass
\```

## Adding Version Support

To add support for a new schema version:
1. Create new file: `{schema_name}_{major}_{minor}_{patch}.py`
2. Implement `produce()` function for that version
3. Done - auto-discovered automatically!
```

## Testing

Verify directory structure:
```bash
cd libs/waivern-personal-data-analyser
find src/waivern_personal_data_analyser/schema_readers -type f
find src/waivern_personal_data_analyser/schema_producers -type f
```

Expected output:
```
src/waivern_personal_data_analyser/schema_readers/__init__.py
src/waivern_personal_data_analyser/schema_readers/README.md
src/waivern_personal_data_analyser/schema_producers/__init__.py
src/waivern_personal_data_analyser/schema_producers/README.md
```

## Key Decisions

**Directory structure:**
- Both directories at package root level (next to analyser.py)
- Matches inspection path in base class auto-discovery
- Symmetrical structure for readers and producers

**Documentation:**
- README files explain the pattern
- Serves as template for migrating other components
- Examples help developers understand expectations

**Interface convention:**
- Readers export `read()` function
- Producers export `produce()` function
- Not enforced (no Protocol), just convention

## Files Created

- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_readers/__init__.py`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_readers/README.md`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_producers/__init__.py`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_producers/README.md`

## Notes

- This step just sets up structure, no logic yet
- Next steps will create the actual reader/producer modules
- READMEs serve as documentation and migration template
