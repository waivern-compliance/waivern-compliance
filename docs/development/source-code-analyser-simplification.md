# Source Code Analyser Simplification

- **Status:** Implemented
- **Last Updated:** 2026-01-08
- **Related:** [waivern-source-code-analyser](../../libs/waivern-source-code-analyser/)

## Problem

The source code analyser currently performs detailed structural extraction (functions, classes, methods, properties, inheritance chains) from PHP and TypeScript source code. This adds significant complexity with minimal compliance value:

- **Compliance analysis uses pattern matching on raw_content** - structural data is largely unused
- **LLMs understand code semantically** - they don't need pre-extracted structure
- **Structural extraction is lossy** - edge cases (nested classes, generics, multiple extends) are hard to handle correctly
- **Maintenance burden** - keeping extractors correct across languages is ongoing work
- **Unclear value proposition** - if we're just passing raw content, what distinguishes this from filesystem connector?

## Solution

**Simplify the schema** - remove structural extraction, keep only raw content with language detection. Position the source code analyser as the layer for source-code-specific compliance concerns (not syntactic structure).

```
Filesystem Connector     → "Here are the files" (raw content)
                           ↓
Source Code Analyser     → "Here's what this codebase IS"
                           - Language detection
                           - [Future] Dependencies from manifests
                           - [Future] Framework detection
                           - [Future] Security pattern flags
                           ↓
Compliance Analysers     → "Here's what's WRONG" (specific findings)
```

**Context margin for LLM validation** - instead of complex "semantic chunking" based on function boundaries, use a simple configurable line margin around pattern matches.

## Design

### Simplified Schema

**Before:**
```python
class SourceCodeFileDataModel(BaseModel):
    file_path: str
    language: str
    raw_content: str
    metadata: SourceCodeFileMetadataModel
    functions: list[SourceCodeFunctionModel]      # Complex extraction
    classes: list[SourceCodeClassModel]           # Complex extraction
```

**After:**
```python
class SourceCodeFileDataModel(BaseModel):
    file_path: str
    language: str
    raw_content: str
    metadata: SourceCodeFileMetadataModel  # file_size, line_count, last_modified
```

### Context Margin Configuration

For LLM validation, instead of extracting function boundaries for chunking:

```python
class LLMValidationConfig(BaseModel):
    context_margin: int | Literal["all"] = 100  # lines before/after match
```

- Pattern match at line 200 with `margin=50` → send lines 150-250
- Pattern match with `margin="all"` → send entire file
- User controls context vs cost trade-off directly

### Architectural Positioning

The source code analyser's role is **not** syntactic structure extraction. LLMs understand code structure natively from raw content.

Instead, source_code_analyser is the layer for **source-code-specific compliance concerns**:

| Current | Future Extensions |
|---------|-------------------|
| Language detection | Dependencies from package.json, composer.json |
| File metadata | Framework detection (Laravel, Express, React) |
| | Security patterns (encryption, auth mechanisms) |
| | Third-party service integrations |
| | Secrets/credentials detection |

## Implementation Path

### Phase 1: Schema Simplification ✅

1. Removed from `schemas/source_code.py`:
   - `SourceCodeFunctionParameterModel`
   - `SourceCodeFunctionModel`
   - `SourceCodeClassPropertyModel`
   - `SourceCodeClassModel`

2. Simplified `SourceCodeFileDataModel` to only: file_path, language, raw_content, metadata

3. Updated `schemas/__init__.py` exports

4. Regenerated JSON schema

### Phase 2: Analyser Simplification ✅

1. Removed from `analyser.py`:
   - `_convert_callables_to_functions()`
   - `_convert_type_definitions_to_classes()`
   - `_callable_to_function_model()`
   - `_type_def_to_class_model()`

2. Simplified `_extract_file_data()` to `_build_file_data()` returning only file_path, language, raw_content, metadata

3. Fixed line count calculation: uses `len(source_code.splitlines())` instead of `count("\n") + 1`

### Phase 3: Remove Extractor Code ✅

Deleted from `languages/` directory:
- `typescript/callable_extractor.py`
- `typescript/type_extractor.py`
- `typescript/helpers.py`
- `php/callable_extractor.py`
- `php/type_extractor.py`
- `php/helpers.py`
- `models.py` (CallableModel, TypeDefinitionModel, etc.)
- `base.py`
- Related test files

Kept:
- `registry.py` - still needed for language detection by extension
- `protocols.py` - simplified, just for tree-sitter language binding
- Language support classes - simplified to only provide name, extensions, and tree-sitter binding

### Phase 4: Context Margin Configuration (Deferred)

Future enhancement - not required for simplification:
```python
context_margin: int | Literal["all"] = 100
```

Can be added when requirements arise for finer control over LLM context windows.

### Phase 5: Update Downstream Analysers ✅

Cleaned up `waivern-processing-purpose-analyser`:
- Removed stale TypedDicts (`SourceCodeFunctionDict`, `SourceCodeClassDict`, `SourceCodeImportDict`)
- Removed dead code in `_analyse_structured_elements()` that processed removed fields
- Updated tests to use simplified schema format

`waivern-personal-data-analyser` had no references to removed fields.

### Phase 6: Update Tests ✅

- Removed tests for structural extraction
- Updated tests to use simplified schema
- Test coverage maintained for core functionality

## Additional Fixes

**Hardcoded UTF-8 Assumption**
- Keep UTF-8 as default (covers 99% of modern codebases)
- Optionally add `encoding` config parameter if real-world issues arise

**Memory Usage**
- Document that large codebases (100MB+) may have high memory usage
- Consider streaming for large codebases only if proven bottleneck

## Benefits

- **Simpler codebase** - removes ~1000 lines of extractor code
- **Fewer edge cases** - no more nested class, generic, interface bugs
- **Clear component purpose** - language detection + future compliance enrichment
- **Better LLM integration** - raw code is what LLMs understand best
- **User control** - context margin gives direct control over LLM token usage

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking change for downstream consumers | Check all schema consumers before proceeding |
| Loss of functionality | Git history preserves everything; can be re-added if needed |
| Future regret | Clear extension points for compliance-relevant metadata |

## Future Extensions

When requirements arise, the source code analyser can be extended with:

- **Dependency analysis** - parse package.json, composer.json, requirements.txt
- **Framework detection** - identify Laravel, Express, React, etc.
- **Security pattern detection** - encryption usage, authentication mechanisms
- **Third-party integrations** - detect external service calls
- **Secrets detection** - hardcoded API keys, credentials
