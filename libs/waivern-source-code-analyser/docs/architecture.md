# Source Code Analyser Architecture

This document explains the internal architecture of the Source Code Analyser.

## Overview

The Source Code Analyser is a **pure analyser** that transforms file content into language-detected source code representations. It accepts input from any connector that produces the `standard_input` schema and outputs the `source_code` schema with raw content and language metadata.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ FilesystemConnector │────▶│ SourceCodeAnalyser   │────▶│ Downstream         │
│ (or other source)   │     │                      │     │ Analysers          │
└─────────────────────┘     └──────────────────────┘     └────────────────────┘
   standard_input              standard_input ──▶           source_code
   schema output               source_code schema           schema input
```

## Design Philosophy

**LLMs understand code structure natively from raw content.** The analyser intentionally does not extract structural information (functions, classes, methods) because:

1. Compliance analysis uses pattern matching on raw content
2. LLM validation receives raw code and understands it semantically
3. Structural extraction added complexity without proportional compliance value

The source code analyser focuses on **language detection** and provides a foundation for future compliance-relevant metadata (dependencies, frameworks, security patterns).

## Information Flow

```
1. Input Reception
   └── standard_input schema (file content + metadata)
        ↓
2. Language Detection
   └── Auto-detect from file extension OR use config override
        ↓
3. Tree-sitter Parsing
   └── Validate syntax (ensures file is valid source code)
        ↓
4. Output Generation
   └── source_code schema (raw content + language + metadata)
```

### Processing Flow

```python
SourceCodeAnalyser.process(inputs, output_schema)
│
├── 1. Merge input messages (fan-in support)
│
├── 2. For each file entry:
│   │
│   ├── 2a. Validate file size (skip if > max_file_size)
│   │
│   ├── 2b. Detect language
│   │       ├── Config override (if specified)
│   │       └── Auto-detect from file extension
│   │
│   ├── 2c. Parse with tree-sitter (validates syntax)
│   │       └── SourceCodeParser.parse() → AST root node
│   │
│   └── 2d. Build file data
│           └── file_path, language, raw_content, metadata
│
└── 3. Build and return source_code Message
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SourceCodeAnalyserFactory                    │
│  - Creates analyser instances with validated configuration      │
│  - Implements ComponentFactory pattern                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SourceCodeAnalyser                         │
│  - Main entry point for processing                              │
│  - Orchestrates parsing and language detection                  │
│  - Handles fan-in merging of multiple inputs                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│    SourceCodeParser      │          │    LanguageRegistry      │
│  - Wraps tree-sitter     │─────────▶│  - Singleton pattern     │
│  - Language detection    │  uses    │  - Plugin discovery      │
│  - Syntax validation     │          │  - Extension mapping     │
└──────────────────────────┘          └──────────────────────────┘
                                                  │
                                                  ▼
                                      ┌──────────────────────────┐
                                      │    LanguageSupport       │
                                      │  - Protocol interface    │
                                      │  - Per-language impl     │
                                      │  - Tree-sitter binding   │
                                      └──────────────────────────┘
```

## Language Plugin System

Languages are discovered via Python entry points:

```
┌─────────────────────────────────────────────────────────────────┐
│                      LanguageRegistry                           │
│  - Singleton managing all language plugins                      │
│  - Discovers plugins via waivern.source_code_languages          │
│  - Maps file extensions to language implementations             │
└─────────────────────────────────────────────────────────────────┘
         │
         │ discovers via entry points
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LanguageSupport Protocol                     │
│  @property name: str                                            │
│  @property file_extensions: list[str]                           │
│  def get_tree_sitter_language() -> Language                     │
└─────────────────────────────────────────────────────────────────┘
         │
         │ implemented by
         ▼
┌─────────────────┐  ┌─────────────────┐
│ PHPLanguage     │  │ TypeScript      │
│ Support         │  │ LanguageSupport │
├─────────────────┤  ├─────────────────┤
│ .php, .phtml    │  │ .ts, .tsx, .mts │
│ tree-sitter-php │  │ tree-sitter-ts  │
└─────────────────┘  └─────────────────┘
```

### Supported Languages

| Language   | Extensions                                  |
| ---------- | ------------------------------------------- |
| PHP        | `.php`, `.php3`, `.php4`, `.php5`, `.phtml` |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts`               |

## Schema Contracts

### Input Schema: `standard_input/1.0.0`

```json
{
  "schemaVersion": "1.0.0",
  "name": "Analysis name",
  "source": "/path/to/source",
  "data": [
    {
      "content": "<?php function example() {}",
      "metadata": {
        "file_path": "/path/to/file.php",
        "file_size": 1024,
        "last_modified": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```

### Output Schema: `source_code/1.0.0`

```json
{
  "schemaVersion": "1.0.0",
  "name": "Analysis name",
  "source": "/path/to/source",
  "data": [
    {
      "file_path": "/path/to/file.php",
      "language": "php",
      "raw_content": "<?php function example() {}",
      "metadata": {
        "file_size": 1024,
        "line_count": 1,
        "last_modified": "2024-01-01T00:00:00Z"
      }
    }
  ],
  "metadata": {
    "total_files": 1,
    "total_lines": 1,
    "analysis_timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## Error Handling

The analyser implements graceful degradation:

| Scenario                     | Behaviour                                |
| ---------------------------- | ---------------------------------------- |
| File exceeds `max_file_size` | Skipped with warning, analysis continues |
| Unsupported file extension   | Skipped, no error                        |
| Parse failure                | File skipped, analysis continues         |
| Missing tree-sitter binding  | Language silently unavailable            |
| Invalid configuration        | `AnalyserConfigError` raised at startup  |

## Configuration

```python
SourceCodeAnalyserConfig(
    language="php",        # Optional: Override auto-detection
    max_file_size=10485760 # Optional: Max file size in bytes (default: 10MB)
)
```

## Directory Structure

```
waivern-source-code-analyser/
├── src/waivern_source_code_analyser/
│   ├── __init__.py              # Package exports
│   ├── analyser.py              # Main SourceCodeAnalyser
│   ├── analyser_config.py       # Configuration with validation
│   ├── analyser_factory.py      # Factory for DI
│   ├── parser.py                # Tree-sitter wrapper
│   ├── validators.py            # Utility validators
│   ├── schemas/
│   │   ├── source_code.py       # Pydantic output models
│   │   └── json_schemas/        # JSON schema definitions
│   └── languages/
│       ├── protocols.py         # LanguageSupport protocol
│       ├── registry.py          # LanguageRegistry singleton
│       ├── php/
│       │   └── support.py       # PHP language support
│       └── typescript/
│           └── support.py       # TypeScript language support
├── docs/
│   └── architecture.md          # This document
└── tests/                       # Test suite
```

## Future Extensions

The source code analyser is positioned for future compliance-relevant metadata:

| Current           | Future Extensions                           |
| ----------------- | ------------------------------------------- |
| Language detection| Dependencies from package.json, composer.json |
| File metadata     | Framework detection (Laravel, Express, React) |
|                   | Security patterns (encryption, auth mechanisms) |
|                   | Third-party service integrations            |
|                   | Secrets/credentials detection               |
