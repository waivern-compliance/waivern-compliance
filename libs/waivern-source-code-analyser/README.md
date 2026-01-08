# waivern-source-code-analyser

Source code analyser for the Waivern Compliance Framework (WCF).

## Overview

The Source Code Analyser parses source code files and extracts structured information about functions, classes, interfaces, and other code elements. It transforms file content from the `standard_input` schema into the `source_code` schema.

**Key characteristics:**

- **Pure analyser** - No file I/O; receives input from connectors (typically FilesystemConnector)
- **Tree-sitter based** - Uses tree-sitter for language-agnostic AST parsing
- **Extensible** - Plugin architecture for adding new language support
- **Pipeline-ready** - Designed to chain with downstream compliance analysers

### Supported Languages

| Language   | Extensions       | Extracted Elements                                                   |
| ---------- | ---------------- | -------------------------------------------------------------------- |
| PHP        | `.php`, `.phtml` | Functions, classes, methods, properties                              |
| TypeScript | `.ts`, `.tsx`    | Functions, arrow functions, classes, interfaces, enums, type aliases |

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

  # Parse into structured code
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

# Access parsed structure
for file_data in result.content["data"]:
    print(f"File: {file_data['file_path']}")
    print(f"Functions: {len(file_data['functions'])}")
    print(f"Classes: {len(file_data['classes'])}")
```

## Schema Contracts

| Direction | Schema                 | Description                |
| --------- | ---------------------- | -------------------------- |
| Input     | `standard_input/1.0.0` | File content with metadata |
| Output    | `source_code/1.0.0`    | Parsed code structure      |

### Output Structure

```json
{
  "schemaVersion": "1.0.0",
  "data": [
    {
      "file_path": "/src/User.php",
      "language": "php",
      "functions": [
        {
          "name": "validateEmail",
          "parameters": [{"name": "email", "type": "string"}],
          "return_type": "bool",
          "line_start": 10,
          "line_end": 15
        }
      ],
      "classes": [
        {
          "name": "User",
          "kind": "class",
          "extends": ["BaseModel"],
          "implements": ["Serializable"],
          "methods": [...],
          "properties": [...]
        }
      ],
      "raw_content": "<?php ...",
      "metadata": {
        "file_size": 1024,
        "line_count": 50
      }
    }
  ]
}
```

## Configuration

| Property        | Type     | Default     | Description                         |
| --------------- | -------- | ----------- | ----------------------------------- |
| `language`      | `string` | Auto-detect | Override language detection         |
| `max_file_size` | `int`    | `10485760`  | Skip files larger than this (bytes) |

## Documentation

For detailed documentation, see the `docs/` directory:

- **[Architecture](docs/architecture.md)** - How information flows through the analyser, the separation of types vs callables, and component relationships
- **[Extending Languages](docs/extending-languages.md)** - Guide for adding support for new programming languages
