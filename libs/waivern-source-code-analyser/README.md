# waivern-source-code-analyser

Source code analyser for WCF

## Overview

The Source Code Analyser transforms file content from `standard_input` schema to `source_code` schema with parsed code structure. It accepts file content from any connector (typically FilesystemConnector) and parses it using tree-sitter to extract functions, classes, and code patterns.

This is a **pure analyser** - it does not perform file I/O. Use FilesystemConnector to read files, then pipe the output to SourceCodeAnalyser.

Key features:
- Parses source code (currently PHP) using tree-sitter
- Extracts functions, classes, and code structure
- Transforms `standard_input` schema → `source_code` schema
- Works in pipelines with any connector that produces file content

## Installation

Basic installation:
```bash
pip install waivern-source-code-analyser
```

With tree-sitter support for PHP parsing:
```bash
pip install waivern-source-code-analyser[tree-sitter]
```

## Usage

### In WCF Pipelines (Recommended)

The analyser is designed for use in multi-step pipelines:

```yaml
# Example runbook
connectors:
  - name: filesystem_reader
    type: filesystem_connector
    properties:
      path: ./src

analysers:
  - name: code_parser
    type: source_code_analyser
    properties:
      language: php

  - name: purpose_detector
    type: processing_purpose_analyser

execution:
  - id: read_files
    connector: filesystem_reader
    analyser: code_parser
    input_schema: standard_input
    output_schema: source_code
    save_output: true

  - id: analyse_purposes
    input_from: read_files
    analyser: purpose_detector
    input_schema: source_code
    output_schema: processing_purpose_finding
```

### Programmatic Usage

```python
from waivern_source_code_analyser import SourceCodeAnalyser, SourceCodeAnalyserConfig
from waivern_core import Message, Schema
from waivern_core.schemas import StandardInputDataModel, StandardInputDataItemModel

# Create analyser
config = SourceCodeAnalyserConfig.from_properties({"language": "php"})
analyser = SourceCodeAnalyser(config)

# Prepare input (typically from FilesystemConnector)
input_data = StandardInputDataModel(
    schemaVersion="1.0.0",
    name="PHP analysis",
    source="/path/to/source",
    data=[
        StandardInputDataItemModel(
            content="<?php function example() { return true; } ?>",
            metadata={"file_path": "/path/to/file.php"}
        )
    ]
)

message = Message(
    id="parse",
    content=input_data.model_dump(exclude_none=True),
    schema=Schema("standard_input", "1.0.0")
)

# Process
result = analyser.process(
    Schema("standard_input", "1.0.0"),
    Schema("source_code", "1.0.0"),
    message
)

# Result contains parsed functions, classes, etc.
print(result.content["data"][0]["functions"])
```

## Schema Support

**Input:** `standard_input` (v1.0.0) - File content from any connector
**Output:** `source_code` (v1.0.0) - Parsed code structure

## Configuration

```python
SourceCodeAnalyserConfig(
    language="php",           # Programming language (currently only PHP supported)
    max_file_size=10485760   # Max file size in bytes (default: 10MB)
)
```

## Architecture

This package follows WCF's analyser pattern:
- **Pure transformation** - No file I/O, only data processing
- **Schema-driven** - Input/output validated against JSON schemas
- **Pipeline-ready** - Designed to chain with other analysers
- **Independent** - No dependencies on connectors

For file collection, use `waivern-filesystem` connector.

## Migration from waivern-source-code

The old `waivern-source-code` package included a connector. This has been refactored:

**Old (deprecated):**
```python
from waivern_source_code import SourceCodeConnector  # ❌ No longer available
```

**New (pipeline):**
```yaml
# Use FilesystemConnector + SourceCodeAnalyser pipeline
execution:
  - id: read_files
    connector: filesystem_reader  # Handles file I/O
    analyser: code_parser         # Handles parsing
```

This separation follows the single-responsibility principle and enables better reusability.
