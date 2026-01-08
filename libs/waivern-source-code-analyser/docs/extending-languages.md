# Extending Language Support

This guide explains how to add support for new programming languages to the Source Code Analyser.

## Overview

The Source Code Analyser uses a plugin architecture based on:

- **tree-sitter** for parsing source code into Abstract Syntax Trees (ASTs)
- **Python entry points** for plugin discovery
- **LanguageSupport protocol** for implementation contracts

## Prerequisites

Before adding a new language, ensure:

1. A tree-sitter grammar exists for the language (check [tree-sitter grammars](https://tree-sitter.github.io/tree-sitter/))
2. Python bindings are available (usually as `tree-sitter-{language}` on PyPI)

## Implementation Guide

This guide follows a test-first approach. Write failing tests, then implement to make them pass.

### Step 1: Create the Module Structure

Create the directory structure for your language:

```
languages/
├── your_language/
│   ├── __init__.py
│   ├── support.py           # Main LanguageSupport implementation
│   ├── callable_extractor.py # Extract functions/methods
│   ├── type_extractor.py     # Extract classes/interfaces
│   └── helpers.py            # Language-specific utilities (optional)
```

### Step 2: Write Tests First

Start with failing tests that define the expected behaviour:

```python
# tests/waivern_source_code_analyser/languages/your_language/test_extraction.py
import pytest
from tree_sitter import Parser

from waivern_source_code_analyser.languages.your_language import YourLanguageSupport


@pytest.fixture
def language_support() -> YourLanguageSupport:
    return YourLanguageSupport()


@pytest.fixture
def parser(language_support: YourLanguageSupport) -> Parser:
    parser = Parser()
    parser.language = language_support.get_tree_sitter_language()
    return parser


class TestFunctionExtraction:
    def test_extracts_simple_function(
        self, language_support: YourLanguageSupport, parser: Parser
    ) -> None:
        source = """
        function hello() {
            return "world"
        }
        """
        tree = parser.parse(source.encode())
        result = language_support.extract(tree.root_node, source)

        assert len(result.callables) == 1
        assert result.callables[0].name == "hello"
        assert result.callables[0].kind == "function"


class TestClassExtraction:
    def test_extracts_simple_class(
        self, language_support: YourLanguageSupport, parser: Parser
    ) -> None:
        source = """
        class User {
            function getName() {
                return this.name
            }
        }
        """
        tree = parser.parse(source.encode())
        result = language_support.extract(tree.root_node, source)

        assert len(result.type_definitions) == 1
        assert result.type_definitions[0].name == "User"
        assert len(result.type_definitions[0].methods) == 1
```

Run the tests - they should fail. Now implement to make them pass.

### Step 3: Implement the LanguageSupport Protocol

The `LanguageSupport` protocol defines the interface every language must implement:

```python
# languages/your_language/support.py
from tree_sitter import Language, Node

from waivern_source_code_analyser.languages.models import (
    LanguageExtractionResult,
)
from waivern_source_code_analyser.languages.protocols import LanguageSupport

from .callable_extractor import YourLanguageCallableExtractor
from .type_extractor import YourLanguageTypeExtractor


class YourLanguageSupport(LanguageSupport):
    """Language support for YourLanguage."""

    @property
    def name(self) -> str:
        """Canonical language name (lowercase)."""
        return "yourlanguage"

    @property
    def file_extensions(self) -> list[str]:
        """Supported file extensions (with leading dot)."""
        return [".yl", ".ylang"]

    def get_tree_sitter_language(self) -> Language:
        """Return the tree-sitter Language object."""
        import tree_sitter_yourlanguage as ts_yl
        return Language(ts_yl.language())

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract code structure from AST."""
        callable_extractor = YourLanguageCallableExtractor(source_code)
        type_extractor = YourLanguageTypeExtractor(source_code)

        return LanguageExtractionResult(
            callables=callable_extractor.extract_all(root_node),
            type_definitions=type_extractor.extract_all(root_node),
        )
```

### Step 4: Implement the CallableExtractor

Extract functions, methods, and other callable code elements:

```python
# languages/your_language/callable_extractor.py
from tree_sitter import Node

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_nodes_by_type,
    get_node_text,
)
from waivern_source_code_analyser.languages.models import (
    CallableModel,
    ParameterModel,
)

from .helpers import LINE_INDEX_OFFSET, FUNCTION_TYPES, get_docstring


class YourLanguageCallableExtractor:
    """Extract callable elements from YourLanguage AST."""

    def __init__(self, source_code: str) -> None:
        self._source_code = source_code

    def extract_all(self, root_node: Node) -> list[CallableModel]:
        """Extract all top-level functions from the AST."""
        callables: list[CallableModel] = []

        for node_type in FUNCTION_TYPES:
            for node in find_nodes_by_type(root_node, node_type):
                callable_model = self._extract_callable(node)
                if callable_model:
                    callables.append(callable_model)

        return callables

    def extract_method(self, method_node: Node) -> CallableModel | None:
        """Extract a method from within a class/type definition."""
        return self._extract_callable(method_node, is_method=True)

    def _extract_callable(
        self, node: Node, is_method: bool = False
    ) -> CallableModel | None:
        """Extract callable details from an AST node."""
        # Get function name
        name_node = find_child_by_type(node, "identifier")
        if not name_node:
            return None
        name = get_node_text(name_node, self._source_code)

        # Get parameters
        params = self._extract_parameters(node)

        # Get return type (if available)
        return_type = self._extract_return_type(node)

        # Get docstring
        docstring = get_docstring(node, self._source_code)

        return CallableModel(
            name=name,
            kind="method" if is_method else "function",
            parameters=params,
            return_type=return_type,
            line_start=node.start_point[0] + LINE_INDEX_OFFSET,
            line_end=node.end_point[0] + LINE_INDEX_OFFSET,
            docstring=docstring,
            visibility="public" if is_method else None,
            is_static=False,
            is_async=False,
        )

    def _extract_parameters(self, node: Node) -> list[ParameterModel]:
        """Extract function parameters."""
        params: list[ParameterModel] = []
        param_list = find_child_by_type(node, "formal_parameters")

        if param_list:
            for param in param_list.children:
                if param.type == "parameter":
                    # Extract parameter name and type
                    param_name = get_node_text(
                        find_child_by_type(param, "identifier"),
                        self._source_code
                    )
                    params.append(ParameterModel(
                        name=param_name,
                        type=None,  # Extract type annotation if available
                        default=None,
                    ))

        return params

    def _extract_return_type(self, node: Node) -> str | None:
        """Extract return type annotation."""
        # Implementation depends on language syntax
        return None
```

### Step 5: Implement the TypeExtractor

Extract classes, interfaces, enums, and other type definitions:

```python
# languages/your_language/type_extractor.py
from tree_sitter import Node

from waivern_source_code_analyser.languages.base import (
    find_child_by_type,
    find_children_by_type,
    find_nodes_by_type,
    get_node_text,
)
from waivern_source_code_analyser.languages.models import (
    MemberModel,
    TypeDefinitionModel,
)

from .callable_extractor import YourLanguageCallableExtractor
from .helpers import CLASS_TYPES, LINE_INDEX_OFFSET, get_docstring


class YourLanguageTypeExtractor:
    """Extract type definitions from YourLanguage AST."""

    def __init__(self, source_code: str) -> None:
        self._source_code = source_code
        self._callable_extractor = YourLanguageCallableExtractor(source_code)

    def extract_all(self, root_node: Node) -> list[TypeDefinitionModel]:
        """Extract all type definitions from the AST."""
        types: list[TypeDefinitionModel] = []

        for node_type, kind in CLASS_TYPES.items():
            for node in find_nodes_by_type(root_node, node_type):
                type_def = self._extract_type(node, kind)
                if type_def:
                    types.append(type_def)

        return types

    def _extract_type(
        self, node: Node, kind: str
    ) -> TypeDefinitionModel | None:
        """Extract type definition details from an AST node."""
        # Get type name
        name_node = find_child_by_type(node, "identifier")
        if not name_node:
            return None
        name = get_node_text(name_node, self._source_code)

        # Get inheritance
        extends = self._extract_extends(node)
        implements = self._extract_implements(node)

        # Get members (properties, fields)
        members = self._extract_members(node)

        # Get methods
        methods = self._extract_methods(node)

        # Get docstring
        docstring = get_docstring(node, self._source_code)

        return TypeDefinitionModel(
            name=name,
            kind=kind,
            extends=extends,
            implements=implements,
            members=members,
            methods=methods,
            line_start=node.start_point[0] + LINE_INDEX_OFFSET,
            line_end=node.end_point[0] + LINE_INDEX_OFFSET,
            docstring=docstring,
        )

    def _extract_extends(self, node: Node) -> list[str]:
        """Extract base class/type names."""
        # Implementation depends on language syntax
        return []

    def _extract_implements(self, node: Node) -> list[str]:
        """Extract implemented interface names."""
        # Implementation depends on language syntax
        return []

    def _extract_members(self, node: Node) -> list[MemberModel]:
        """Extract class members (properties, fields)."""
        # Implementation depends on language syntax
        return []

    def _extract_methods(self, node: Node) -> list[CallableModel]:
        """Extract methods from a class body."""
        methods = []
        body = find_child_by_type(node, "class_body")

        if body:
            for child in body.children:
                if child.type == "method_definition":
                    method = self._callable_extractor.extract_method(child)
                    if method:
                        methods.append(method)

        return methods
```

### Step 6: Export from Package

Create the `__init__.py` to export the main class:

```python
# languages/your_language/__init__.py
from .support import YourLanguageSupport

__all__ = ["YourLanguageSupport"]
```

### Step 7: Register via Entry Points

Add the entry point in `pyproject.toml`:

```toml
[project.optional-dependencies]
yourlanguage = ["tree-sitter-yourlanguage>=0.21.0"]

[project.entry-points."waivern.source_code_languages"]
yourlanguage = "waivern_source_code_analyser.languages.your_language:YourLanguageSupport"
```

At this point, your tests from Step 2 should pass.

## AST Utilities

The `languages/base.py` module provides common utilities:

| Function                                  | Description                          |
| ----------------------------------------- | ------------------------------------ |
| `get_node_text(node, source_code)`        | Extract text content from a node     |
| `find_nodes_by_type(node, node_type)`     | Recursively find all nodes of a type |
| `find_child_by_type(node, child_type)`    | Find first direct child of a type    |
| `find_children_by_type(node, child_type)` | Find all direct children of a type   |
| `is_trivial_node(node)`                   | Check if node is whitespace/trivial  |

## Data Models

### CallableModel

```python
CallableModel(
    name: str,                    # Function/method name
    kind: str,                    # "function", "method", "arrow_function", etc.
    parameters: list[ParameterModel],
    return_type: str | None,
    line_start: int,              # 1-based line number
    line_end: int,                # 1-based line number (inclusive)
    docstring: str | None,
    visibility: str | None,       # "public", "private", "protected"
    is_static: bool,
    is_async: bool,
)
```

### TypeDefinitionModel

```python
TypeDefinitionModel(
    name: str,                    # Type name
    kind: str,                    # "class", "interface", "enum", etc.
    extends: list[str],           # Base types
    implements: list[str],        # Implemented interfaces
    members: list[MemberModel],   # Properties, fields
    methods: list[CallableModel], # Method definitions
    line_start: int,
    line_end: int,
    docstring: str | None,
)
```

### ParameterModel

```python
ParameterModel(
    name: str,
    type: str | None,
    default: str | None,
)
```

### MemberModel

```python
MemberModel(
    name: str,
    kind: str,                    # "property", "field", "enum_variant"
    type: str | None,
    visibility: str | None,
    is_static: bool,
    default: str | None,
)
```

## Testing Language Support

### Isolating the Registry

Use the `isolate_language_registry` fixture to prevent test pollution:

```python
@pytest.fixture(autouse=True)
def isolate_language_registry():
    """Isolate language registry state for each test."""
    from waivern_source_code_analyser.languages.registry import LanguageRegistry

    registry = LanguageRegistry()
    state = registry.snapshot_state()
    yield
    registry.restore_state(state)
```

### Testing Without Tree-sitter Bindings

If tree-sitter bindings aren't installed, tests should skip gracefully:

```python
pytest.importorskip("tree_sitter_yourlanguage")
```

## Built-in Language Reference

### PHP (`languages/php/`)

**Extensions:** `.php`, `.php3`, `.php4`, `.php5`, `.phtml`

**Extracted Elements:**

- Functions (`function_definition`)
- Classes (`class_declaration`)
- Methods (`method_declaration`)
- Properties
- Visibility modifiers
- Static modifiers
- Docstrings (PHPDoc comments)

### TypeScript (`languages/typescript/`)

**Extensions:** `.ts`, `.tsx`

**Extracted Elements:**

- Functions (`function_declaration`)
- Arrow functions (`arrow_function`)
- Classes (`class_declaration`)
- Interfaces (`interface_declaration`)
- Enums (`enum_declaration`)
- Type aliases (`type_alias_declaration`)
- Methods
- Properties with visibility
- Async functions
- Docstrings (JSDoc comments)

## Tips for Implementation

1. **Use tree-sitter playground:** Test AST structure at [tree-sitter.github.io/tree-sitter/playground](https://tree-sitter.github.io/tree-sitter/playground)

2. **Handle edge cases:** Empty files, syntax errors, partial code

3. **Preserve raw content:** The analyser keeps `raw_content` for downstream pattern matching

4. **Follow existing patterns:** Study `languages/php/` and `languages/typescript/` for reference

5. **Validate with contract tests:** Inherit from `AnalyserContractTests` to ensure schema compliance
