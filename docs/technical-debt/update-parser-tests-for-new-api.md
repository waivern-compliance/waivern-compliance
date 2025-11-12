# Update Parser Tests for New parse() API

**Status:** TODO
**Priority:** HIGH
**Created:** 2025-11-12
**Context:** Step 8 - SourceCodeAnalyser implementation

## Problem

The `SourceCodeParser.parse_file()` method was removed to improve separation of concerns. The parser now only handles parsing (not file I/O), with a new public `parse(source_code: str) -> Node` API.

This breaking change affects existing tests:
- `libs/waivern-source-code/tests/waivern_source_code/test_parser.py` (11 usages)
- `libs/waivern-source-code/tests/waivern_source_code/extractors/test_functions.py` (11 usages)
- `libs/waivern-source-code/tests/waivern_source_code/extractors/test_classes.py` (10 usages)

## Solution

Update all test files to use the new pattern:

**Old code:**
```python
root_node, source_code = parser.parse_file(Path(f.name))
```

**New code:**
```python
source_code = Path(f.name).read_text(encoding="utf-8")
root_node = parser.parse(source_code)
```

## Rationale

The parser's responsibility is parsing source code strings, not file I/O. File operations belong to connectors. This change:
- Improves separation of concerns
- Makes the parser usable in pipeline architecture (analysers work with in-memory strings)
- Aligns with single responsibility principle

## Impact

- 32 test failures until fixed
- Connector class still works (updated to handle its own file reading)
- New analyser tests pass (use new API correctly)

## Estimated Effort

Low - mechanical find-replace across 3 files, approximately 15 minutes.
