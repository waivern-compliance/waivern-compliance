# Task: Create SourceCodeAnalyser Class

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** TODO
- **Prerequisites:** Step 7 (SourceCodeAnalyserConfig created)
- **GitHub Issue:** #213

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser. The previous step created the configuration class.

**See:** the parent implementation plan for full context.

## Purpose

Create SourceCodeAnalyser that implements Analyser interface, accepting `standard_input` schema (file content) and producing `source_code` schema (parsed code structure).

## Problem

Current SourceCodeConnector has two responsibilities:
1. File discovery/collection (using FilesystemConnector internally)
2. Code parsing/transformation (tree-sitter analysis)

This violates single responsibility principle and creates a hardcoded dependency on FilesystemConnector, breaking the plugin architecture.

## Solution

Extract the parsing logic from SourceCodeConnector into SourceCodeAnalyser:
- Accept `standard_input` schema containing file content
- Parse using existing tree-sitter infrastructure
- Output `source_code` schema with parsed structure
- Reuse existing extractors (FunctionExtractor, ClassExtractor)

## Decisions Made

1. **Implement Analyser interface** - get_supported_input_schemas(), get_supported_output_schemas(), process_data()
2. **Accept standard_input schema** - Compatible with FilesystemConnector output
3. **Output source_code schema** - Same schema as current connector
4. **Reuse existing code** - Parser, extractors, schema producers remain unchanged
5. **No file system access** - All file content comes from input Message
6. **Process each file independently** - standard_input can contain single file or multiple files

## Implementation

### File to Create

`libs/waivern-source-code/src/waivern_source_code/analyser.py`

### Class Structure

**Supported schemas:**
```
Input schemas: [Schema("standard_input", "1.0.0")]
Output schemas: [Schema("source_code", "1.0.0")]
```

**Key methods to implement:**

#### 1. Constructor

Accept `SourceCodeAnalyserConfig` and initialise parser/extractors without file system dependencies.

**Pseudo-code:**
```
function __init__(config):
    self._config = config
    # Don't create FilesystemConnector
    # Parser created on-demand per file based on language
```

#### 2. get_supported_input_schemas()

Return list with `standard_input` schema v1.0.0.

#### 3. get_supported_output_schemas()

Return list with `source_code` schema v1.0.0.

#### 4. process_data()

Transform input Message containing file content to output Message with parsed code structure.

**Algorithm (pseudo-code):**
```
function process_data(input_message):
    # Extract file content from standard_input schema
    input_data = input_message.content
    files_list = input_data["files"]  # List of file entries

    # Parse each file
    parsed_files = []
    total_files = 0
    total_lines = 0

    for file_entry in files_list:
        file_path = Path(file_entry["path"])
        file_content = file_entry["content"]

        # Skip files exceeding max_file_size
        if len(file_content.encode()) > config.max_file_size:
            log warning and skip
            continue

        # Detect language or use config override
        language = config.language or detect_language_from_file(file_path)

        # Parse file with tree-sitter
        parser = SourceCodeParser(language)
        root_node, source_code = parser.parse_string(file_content)

        # Extract structural information
        file_data = extract_file_data(file_path, root_node, source_code)
        parsed_files.append(file_data)

        total_files += 1
        total_lines += source_code.count("\n") + 1

    # Transform to source_code schema using existing producer
    output_schema = self.get_supported_output_schemas()[0]
    producer = load_producer(output_schema)

    output_data = producer.produce(
        schema_version=output_schema.version,
        source_config={...},  # Derived from input
        analysis_summary={total_files, total_lines},
        files_data=parsed_files
    )

    return Message(
        id="Source code analysis",
        content=output_data,
        schema=output_schema
    )
```

**Key differences from connector:**
- No file system traversal
- Input comes from Message.content, not disk
- File path extracted from standard_input schema
- File content extracted from standard_input schema

#### 5. Helper methods (extract from connector)

Reuse and adapt these private methods from SourceCodeConnector:
- `_load_producer()` - unchanged
- `_extract_file_data()` - adapt to not use Path.stat()
- `_get_relative_path()` - adapt to work with string paths

## Testing

### Testing Strategy

Test through **public API only**: `process_data()` method using Message objects.

Create test Messages with `standard_input` schema containing various file scenarios.

### Test Scenarios

**File:** `libs/waivern-source-code/tests/test_analyser.py`

#### 1. Single PHP file analysis

**Setup:**
- Create Message with standard_input schema containing single PHP file
- File contains functions and classes
- Use default config (auto-detect language)

**Expected behaviour:**
- Returns Message with source_code schema
- Parsed output contains functions and classes
- Language detected as "php"
- Line count matches input

#### 2. Multiple files analysis

**Setup:**
- Create Message with standard_input schema containing 3 PHP files
- Files have different structures

**Expected behaviour:**
- All 3 files parsed successfully
- Output contains 3 file entries
- Each file has correct structure

#### 3. Language override

**Setup:**
- Config specifies language="php"
- Input file has no extension (.txt)

**Expected behaviour:**
- File parsed as PHP (config overrides detection)
- No errors raised

#### 4. File exceeds max_file_size

**Setup:**
- Config max_file_size=1KB
- Input file content is 2KB

**Expected behaviour:**
- File skipped (not in output)
- Warning logged
- No exception raised

#### 5. Unsupported language

**Setup:**
- Input file with unsupported language (e.g., .rs Rust file)

**Expected behaviour:**
- File skipped or error logged
- Graceful degradation (no crash)

#### 6. Empty file list

**Setup:**
- Message with standard_input containing empty files array

**Expected behaviour:**
- Returns Message with source_code schema
- Empty files list in output
- Zero totals

## Success Criteria

**Functional:**
- [ ] SourceCodeAnalyser implements Analyser interface correctly
- [ ] Accepts standard_input schema (v1.0.0)
- [ ] Outputs source_code schema (v1.0.0)
- [ ] Parses PHP files using tree-sitter
- [ ] Extracts functions and classes correctly
- [ ] Handles multiple files in single Message
- [ ] Respects max_file_size configuration
- [ ] Language detection works when config.language=None
- [ ] Language override works when config.language specified

**Quality:**
- [ ] All tests pass
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] No file system access in analyser code

**Code Quality:**
- [ ] Tests use public API (process_data) only
- [ ] Reuses existing parser/extractor code
- [ ] No duplication from connector
- [ ] Clear separation: transformation only, no I/O
- [ ] Error handling matches analyser patterns

## Implementation Notes

**Design considerations:**
- Analyser is stateless - no file system state
- All data flows through Message objects
- Existing parser/extractor infrastructure unchanged
- Schema producer logic reused completely

**Code reuse strategy:**
- Copy parsing logic from connector
- Remove file system traversal
- Adapt to read from Message.content instead of disk
- Keep extractor instantiation and usage identical

**Future enhancements:**
- Support source_code schema as input (passthrough/enrichment)
- Parallel file processing for large inputs
- Streaming mode for very large codebases
