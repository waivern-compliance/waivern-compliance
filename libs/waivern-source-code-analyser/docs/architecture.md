# Source Code Analyser Architecture

This document explains the internal architecture of the Source Code Analyser, how information flows through the system, and how the various components work together.

## Overview

The Source Code Analyser is a **pure analyser** that transforms file content into structured code representations. It accepts input from any connector that produces the `standard_input` schema and outputs the `source_code` schema with parsed code structure.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ FilesystemConnector │────▶│ SourceCodeAnalyser   │────▶│ Downstream         │
│ (or other source)   │     │                      │     │ Analysers          │
└─────────────────────┘     └──────────────────────┘     └────────────────────┘
   standard_input              standard_input ──▶           source_code
   schema output               source_code schema           schema input
```

## Information Flow

### High-Level Pipeline

```
1. Input Reception
   └── standard_input schema (file content + metadata)
        ↓
2. Language Detection
   └── Auto-detect from file extension OR use config override
        ↓
3. Tree-sitter Parsing
   └── Generate Abstract Syntax Tree (AST)
        ↓
4. Language-Specific Extraction
   ├── CallableExtractor → Functions, methods, arrow functions
   └── TypeExtractor → Classes, interfaces, enums, type aliases
        ↓
5. Model Conversion
   └── Internal models → Schema models
        ↓
6. Output Generation
   └── source_code schema (parsed structure + raw content)
```

### Detailed Processing Flow

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
│   ├── 2c. Parse with tree-sitter
│   │       └── SourceCodeParser.parse() → AST root node
│   │
│   ├── 2d. Extract code structure
│   │       └── LanguageSupport.extract() → LanguageExtractionResult
│   │           ├── CallableExtractor.extract_all() → [CallableModel]
│   │           └── TypeExtractor.extract_all() → [TypeDefinitionModel]
│   │
│   └── 2e. Convert to schema models
│           ├── CallableModel → SourceCodeFunctionModel
│           └── TypeDefinitionModel → SourceCodeClassModel
│
└── 3. Build and return source_code Message
```

## Code Organisation: Types vs Callables

The analyser separates code elements into two distinct categories, each with specialised extractors:

### Callables

**Definition:** Executable code units that can be invoked.

| Kind             | Description                      | Examples                       |
| ---------------- | -------------------------------- | ------------------------------ |
| `function`       | Standalone function declarations | `function foo() {}`            |
| `method`         | Functions defined within a class | `public function bar() {}`     |
| `arrow_function` | Arrow/lambda expressions         | `const fn = () => {}`          |
| `lambda`         | Anonymous functions              | `$fn = function() {}`          |
| `closure`        | Closures with captured scope     | `$fn = function() use ($x) {}` |

**Extraction Rule:** Only standalone functions appear in the top-level `functions` array. Methods are **nested within their parent class** in the `classes` array.

### Types

**Definition:** Type declarations that define structure.

| Kind         | Description                | Examples                           |
| ------------ | -------------------------- | ---------------------------------- |
| `class`      | Class definitions          | `class User {}`                    |
| `interface`  | Interface declarations     | `interface Serializable {}`        |
| `enum`       | Enumeration types          | `enum Status { Active, Inactive }` |
| `struct`     | Structure types (Rust, Go) | `struct Point { x: i32 }`          |
| `trait`      | Trait definitions          | `trait Comparable {}`              |
| `type_alias` | Type alias declarations    | `type UserId = number`             |

**Extraction Includes:**

- Type name and kind
- Inheritance (`extends`, `implements`)
- Members (properties, fields, enum variants)
- Methods (via recursive CallableExtractor)
- Documentation (docstrings/comments)

## Component Architecture

### Core Components

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
│  - Orchestrates parsing and extraction                          │
│  - Handles fan-in merging of multiple inputs                    │
│  - Converts internal models to schema models                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│    SourceCodeParser      │          │    LanguageRegistry      │
│  - Wraps tree-sitter     │─────────▶│  - Singleton pattern     │
│  - Language detection    │  uses    │  - Plugin discovery      │
│  - AST generation        │          │  - Extension mapping     │
└──────────────────────────┘          └──────────────────────────┘
                                                  │
                                                  ▼
                                      ┌──────────────────────────┐
                                      │    LanguageSupport       │
                                      │  - Protocol interface    │
                                      │  - Per-language impl     │
                                      └──────────────────────────┘
                                                  │
                                      ┌───────────┴───────────┐
                                      ▼                       ▼
                            ┌──────────────────┐     ┌────────────────┐
                            │ CallableExtractor│     │ TypeExtractor  │
                            │  - Functions     │     │  - Classes     │
                            │  - Methods       │     │  - Interfaces  │
                            │  - Arrows        │     │  - Enums       │
                            └──────────────────┘     └────────────────┘
```

**Key relationships:**

- `SourceCodeAnalyser` uses `SourceCodeParser` for AST generation
- `SourceCodeAnalyser` uses `LanguageRegistry` directly for extraction
- `SourceCodeParser` depends on `LanguageRegistry` for tree-sitter language objects and extension mapping

### Data Models

The analyser uses two model layers:

#### Internal Extraction Models (`languages/models.py`)

Used during language-specific extraction:

```python
ParameterModel             # Function/method parameter
CallableModel              # Function/method with metadata
MemberModel                # Class member (property, field)
TypeDefinitionModel        # Class/interface/enum definition
LanguageExtractionResult   # Container for extraction output
```

#### Schema Output Models (`schemas/source_code.py`)

Used for wire format output:

```python
SourceCodeFunctionParameterModel  # Parameter in output schema
SourceCodeFunctionModel           # Function in output schema
SourceCodeClassPropertyModel      # Class property in output
SourceCodeClassModel              # Class in output schema
SourceCodeFileDataModel           # Per-file parsed data
SourceCodeDataModel               # Root output model
```

**Conversion Flow:**

```
CallableModel ──────▶ SourceCodeFunctionModel
TypeDefinitionModel ─▶ SourceCodeClassModel
```

## Language Plugin System

### Architecture

The analyser supports multiple languages through a plugin system based on Python entry points.

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
│  def extract(root_node, source_code) -> LanguageExtractionResult│
└─────────────────────────────────────────────────────────────────┘
         │
         │ implemented by
         ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ PHPLanguage     │  │ TypeScript      │  │ (Your Language) │
│ Support         │  │ LanguageSupport │  │                 │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ .php, .phtml    │  │ .ts, .tsx       │  │ .ext            │
│ tree-sitter-php │  │ tree-sitter-ts  │  │ tree-sitter-x   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Discovery Flow

1. **Startup:** `LanguageRegistry.discover()` scans entry points
2. **Validation:** Each plugin's tree-sitter binding is verified
3. **Registration:** Valid plugins are mapped by name and extension
4. **Runtime:** Parser requests language support by extension

### Built-in Languages

| Language   | Extensions                                  | Extracted Elements                                                   |
| ---------- | ------------------------------------------- | -------------------------------------------------------------------- |
| PHP        | `.php`, `.php3`, `.php4`, `.php5`, `.phtml` | Functions, classes, methods, properties                              |
| TypeScript | `.ts`, `.tsx`                               | Functions, arrow functions, classes, interfaces, enums, type aliases |

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
      "functions": [
        {
          "name": "example",
          "parameters": [],
          "return_type": null,
          "line_start": 1,
          "line_end": 1,
          "docstring": null
        }
      ],
      "classes": [],
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

## Line Number Conventions

- **Tree-sitter:** Uses 0-based line indexing
- **Output Schema:** Uses 1-based line indexing (human-readable)
- **Conversion:** Applied via `LINE_INDEX_OFFSET = 1`
- **Range:** Both `line_start` and `line_end` are inclusive

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

**Priority:** Config override > Auto-detection from file extension

## Design Patterns

| Pattern       | Usage                                                |
| ------------- | ---------------------------------------------------- |
| **Factory**   | `SourceCodeAnalyserFactory` for dependency injection |
| **Singleton** | `LanguageRegistry` for plugin management             |
| **Protocol**  | `LanguageSupport` for language extensibility         |
| **Strategy**  | Language-specific extractors                         |
| **Adapter**   | Converting extraction models to schema models        |
| **Fan-in**    | Merging multiple input messages of same schema       |

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
│       ├── base.py              # Common AST utilities
│       ├── models.py            # Internal extraction models
│       ├── protocols.py         # LanguageSupport protocol
│       ├── registry.py          # LanguageRegistry singleton
│       ├── php/                 # PHP language support
│       │   ├── support.py
│       │   ├── callable_extractor.py
│       │   ├── type_extractor.py
│       │   └── helpers.py
│       └── typescript/          # TypeScript language support
│           ├── support.py
│           ├── callable_extractor.py
│           ├── type_extractor.py
│           └── helpers.py
├── docs/
│   ├── architecture.md          # This document
│   └── extending-languages.md   # Language plugin guide
└── tests/                       # Test suite
```
