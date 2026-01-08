# waivern-source-code-analyser

Source code analyser for the Waivern Compliance Framework (WCF).

## Overview

The Source Code Analyser detects programming languages and provides raw source code content for downstream compliance analysis. It transforms file content from the `standard_input` schema into the `source_code` schema.

**Key characteristics:**

- **Pure analyser** - No file I/O; receives input from connectors (typically FilesystemConnector)
- **Tree-sitter based** - Uses tree-sitter for language detection and syntax validation
- **Extensible** - Plugin architecture for adding new language support
- **Pipeline-ready** - Designed to chain with downstream compliance analysers

### Supported Languages

| Language   | Extensions                                  |
| ---------- | ------------------------------------------- |
| PHP        | `.php`, `.php3`, `.php4`, `.php5`, `.phtml` |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts`               |

## Installation

```bash
# Basic installation
pip install waivern-source-code-analyser

# With PHP support
pip install waivern-source-code-analyser[php]

# With TypeScript support
pip install waivern-source-code-analyser[typescript]

# All languages
pip install waivern-source-code-analyser[tree-sitter]
```

## Quick Start

### In WCF Runbooks

```yaml
artifacts:
  # Read files from filesystem
  php_files:
    source:
      type: filesystem
      properties:
        path: ./src
        include_patterns: ["**/*.php"]

  # Detect language and prepare for analysis
  parsed_code:
    inputs: php_files
    process:
      type: source_code_analyser
      properties:
        language: php # Optional: auto-detected from extensions

  # Feed to downstream analysers
  findings:
    inputs: parsed_code
    process:
      type: processing_purpose_analyser
    output: true
```

### Programmatic Usage

```python
from waivern_source_code_analyser import SourceCodeAnalyser, SourceCodeAnalyserConfig
from waivern_core import Message, Schema

# Create analyser
config = SourceCodeAnalyserConfig.from_properties({"language": "php"})
analyser = SourceCodeAnalyser(config)

# Process (input typically comes from FilesystemConnector)
result = analyser.process(
    inputs=[input_message],
    output_schema=Schema("source_code", "1.0.0")
)

# Access parsed data
for file_data in result.content["data"]:
    print(f"File: {file_data['file_path']}")
    print(f"Language: {file_data['language']}")
    print(f"Lines: {file_data['metadata']['line_count']}")
```

## Schema Contracts

| Direction | Schema                 | Description                        |
| --------- | ---------------------- | ---------------------------------- |
| Input     | `standard_input/1.0.0` | File content with metadata         |
| Output    | `source_code/1.0.0`    | Language-detected source code      |

### Output Structure

```json
{
  "schemaVersion": "1.0.0",
  "data": [
    {
      "file_path": "/src/User.php",
      "language": "php",
      "raw_content": "<?php class User { ... }",
      "metadata": {
        "file_size": 1024,
        "line_count": 50,
        "last_modified": "2024-01-01T00:00:00Z"
      }
    }
  ],
  "metadata": {
    "total_files": 1,
    "total_lines": 50,
    "analysis_timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Configuration

| Property        | Type     | Default     | Description                         |
| --------------- | -------- | ----------- | ----------------------------------- |
| `language`      | `string` | Auto-detect | Override language detection         |
| `max_file_size` | `int`    | `10485760`  | Skip files larger than this (bytes) |

## Documentation

For detailed documentation, see the `docs/` directory:

- **[Architecture](docs/architecture.md)** - Component relationships and information flow
