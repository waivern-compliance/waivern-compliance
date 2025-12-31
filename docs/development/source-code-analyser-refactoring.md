# SourceCodeAnalyser Refactoring - TypeScript Support & Language Extensibility

- **Status:** Planned
- **Created:** 2025-12-31

## Overview

Refactor `waivern-source-code-analyser` to support multiple programming languages through a plugin-based architecture. Add TypeScript support while making future languages (JavaScript, Python, Java, etc.) straightforward to add.

---

## Current Problems

1. **Hardcoded language registry** (`parser.py:10-11`): Adding a language requires modifying core files
2. **Scattered language logic** (`functions.py:51-74, 116-122, 145-166, 189-206`): Switch-statement dictionaries and inline `if self.language == "php"` checks
3. **No extension points**: Adding TypeScript requires changing 4+ files

---

## Proposed Architecture

```
SourceCodeAnalyser
       ↓
LanguageRegistry (singleton, entry point discovery)
       ↓
┌────────────────────┬────────────────────┐
│ PHPLanguageSupport │ TSLanguageSupport  │
│   └─ extract()     │   └─ extract()     │
└────────────────────┴────────────────────┘
       ↓                      ↓
       └──────────┬───────────┘
                  ↓
      LanguageExtractionResult
      ├─ callables: [CallableModel]
      └─ type_definitions: [TypeDefinitionModel]
```

**Key Design:**

- **Minimal protocol**: Single `extract()` method per language
- **Discriminated types**: `TypeDefinitionModel.kind` handles classes, interfaces, enums, traits, etc.
- **Entry point discovery**: `waivern.source_code_languages` entry points
- **Self-contained modules**: Each language in `languages/{lang}/` directory
- **Lazy loading**: Tree-sitter bindings loaded only when needed
- **Optional dependencies**: `pip install waivern-source-code-analyser[typescript]`

---

## New Data Models

All models are Pydantic `BaseModel` for consistency with the codebase.

### ParameterModel

Represents function/method parameters.

```python
class ParameterModel(BaseModel):
    """A parameter of a callable."""
    name: str
    type: str | None = None
    default_value: str | None = None
```

### CallableModel

Represents functions, methods, lambdas, closures - anything that can be called.

```python
class CallableModel(BaseModel):
    """A callable construct (function, method, lambda, etc.)."""
    name: str
    kind: str  # "function", "method", "arrow_function", "lambda", "closure"
    line_start: int
    line_end: int
    parameters: list[ParameterModel] = []
    return_type: str | None = None
    visibility: str | None = None  # "public", "private", "protected"
    is_static: bool = False
    is_async: bool = False
    docstring: str | None = None
```

### MemberModel

Represents properties, fields, enum variants.

```python
class MemberModel(BaseModel):
    """A member of a type definition (property, field, enum variant)."""
    name: str
    kind: str  # "property", "field", "enum_variant"
    type: str | None = None
    visibility: str | None = None
    is_static: bool = False
    default_value: str | None = None
```

### TypeDefinitionModel

Represents any type-defining construct - classes, interfaces, enums, structs, traits, type aliases.

```python
class TypeDefinitionModel(BaseModel):
    """A type definition (class, interface, enum, struct, trait, etc.)."""
    name: str
    kind: str  # "class", "interface", "enum", "struct", "trait", "type_alias"
    line_start: int
    line_end: int
    extends: str | None = None
    implements: list[str] = []
    members: list[MemberModel] = []  # properties, enum variants
    methods: list[CallableModel] = []
    docstring: str | None = None
```

### LanguageExtractionResult

What each language's `extract()` method returns. Uses `BaseModel` for consistency.

```python
class LanguageExtractionResult(BaseModel):
    """Result of extracting constructs from source code."""
    callables: list[CallableModel] = []
    type_definitions: list[TypeDefinitionModel] = []
```

---

## New File Structure

```
libs/waivern-source-code-analyser/src/waivern_source_code_analyser/
├── languages/                      # NEW: Language plugin system
│   ├── __init__.py                 # LanguageRegistry (singleton) + exports
│   ├── protocols.py                # LanguageSupport protocol
│   ├── models.py                   # ParameterModel, CallableModel, MemberModel, etc.
│   ├── base.py                     # Standalone AST utility functions (not a class)
│   ├── php/
│   │   ├── __init__.py             # PHPLanguageSupport class
│   │   └── node_types.py           # PHP AST node type constants
│   └── typescript/
│       ├── __init__.py             # TypeScriptLanguageSupport class
│       └── node_types.py           # TypeScript AST node type constants
├── parser.py                       # Refactored to use LanguageRegistry
├── schemas/
│   ├── source_code.py              # Updated output models
│   └── json_schemas/source_code/2.0.0/  # New schema version
├── extractors/                     # REMOVE after migration
└── (rest unchanged)
```

---

## LanguageSupport Protocol

Simple, minimal interface:

```python
# languages/protocols.py

from typing import Protocol, runtime_checkable
from tree_sitter import Language, Node

@runtime_checkable
class LanguageSupport(Protocol):
    """Protocol for language support plugins."""

    @property
    def name(self) -> str:
        """Canonical language name (e.g., 'php', 'typescript')."""
        ...

    @property
    def file_extensions(self) -> list[str]:
        """Supported file extensions including dot (e.g., ['.ts', '.tsx'])."""
        ...

    def get_tree_sitter_language(self) -> Language:
        """Get tree-sitter Language object. May raise ImportError if not installed."""
        ...

    def extract(self, root_node: Node, source_code: str) -> LanguageExtractionResult:
        """Extract all constructs from parsed source code.

        Each language implementation decides what to extract:
        - PHP: functions, classes
        - TypeScript: functions, classes, interfaces, enums, type aliases
        - Rust: functions, structs, traits, enums
        """
        ...
```

---

## LanguageRegistry

Singleton registry for language support plugins with entry point discovery. Follows the same pattern as `RulesetRegistry` in `waivern-rulesets`.

```python
# languages/__init__.py

from importlib.metadata import entry_points
from typing import Any

from .protocols import LanguageSupport


class LanguageNotFoundError(Exception):
    """Raised when a requested language is not registered."""
    pass


class LanguageAlreadyRegisteredError(Exception):
    """Raised when attempting to register a language that already exists."""
    pass


class LanguageRegistryState(TypedDict):
    """State snapshot for LanguageRegistry (used for test isolation)."""
    registry: dict[str, LanguageSupport]
    extension_map: dict[str, str]


class LanguageRegistry:
    """Singleton registry for language support plugins.

    Discovers language plugins via entry points and provides lookup
    by language name or file extension.
    """

    _instance: "LanguageRegistry | None" = None
    _registry: dict[str, LanguageSupport]
    _extension_map: dict[str, str]  # ".ts" → "typescript"
    _discovered: bool

    def __new__(cls, *args: Any, **kwargs: Any) -> "LanguageRegistry":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
            cls._instance._extension_map = {}
            cls._instance._discovered = False
        return cls._instance

    def discover(self) -> None:
        """Discover and register language plugins from entry points.

        Entry point group: waivern.source_code_languages
        """
        if self._discovered:
            return

        eps = entry_points(group="waivern.source_code_languages")
        for ep in eps:
            try:
                language_class = ep.load()
                language = language_class()
                self.register(language)
            except ImportError:
                # Language's tree-sitter binding not installed - skip
                pass

        self._discovered = True

    def register(self, language: LanguageSupport) -> None:
        """Register a language support instance.

        Args:
            language: LanguageSupport implementation

        Raises:
            LanguageAlreadyRegisteredError: If language already registered
        """
        if language.name in self._registry:
            raise LanguageAlreadyRegisteredError(
                f"Language '{language.name}' is already registered"
            )

        self._registry[language.name] = language
        for ext in language.file_extensions:
            self._extension_map[ext] = language.name

    def get(self, name: str) -> LanguageSupport:
        """Get a language by name.

        Args:
            name: Canonical language name (e.g., 'php', 'typescript')

        Returns:
            LanguageSupport implementation

        Raises:
            LanguageNotFoundError: If language not registered
        """
        self.discover()  # Ensure discovery on first access

        if name not in self._registry:
            raise LanguageNotFoundError(f"Language '{name}' not registered")
        return self._registry[name]

    def get_by_extension(self, extension: str) -> LanguageSupport:
        """Get a language by file extension.

        Args:
            extension: File extension including dot (e.g., '.ts', '.php')

        Returns:
            LanguageSupport implementation

        Raises:
            LanguageNotFoundError: If no language supports the extension
        """
        self.discover()

        if extension not in self._extension_map:
            raise LanguageNotFoundError(
                f"No language registered for extension '{extension}'"
            )
        return self._registry[self._extension_map[extension]]

    def list_languages(self) -> list[str]:
        """List all registered language names."""
        self.discover()
        return list(self._registry.keys())

    def list_extensions(self) -> list[str]:
        """List all supported file extensions."""
        self.discover()
        return list(self._extension_map.keys())

    def is_registered(self, name: str) -> bool:
        """Check if a language is registered."""
        self.discover()
        return name in self._registry

    def clear(self) -> None:
        """Clear all registered languages (for testing)."""
        self._registry.clear()
        self._extension_map.clear()
        self._discovered = False

    @classmethod
    def snapshot_state(cls) -> LanguageRegistryState:
        """Capture current state for later restoration (test isolation)."""
        instance = cls()
        return {
            "registry": instance._registry.copy(),
            "extension_map": instance._extension_map.copy(),
        }

    @classmethod
    def restore_state(cls, state: LanguageRegistryState) -> None:
        """Restore state from a previously captured snapshot."""
        instance = cls()
        instance._registry = state["registry"].copy()
        instance._extension_map = state["extension_map"].copy()
```

---

## Base Utility Functions

Standalone helper functions for AST traversal, migrated from `extractors/base.py`. These are not tied to any language and can be used by all language implementations.

```python
# languages/base.py

from tree_sitter import Node

_DEFAULT_ENCODING = "utf-8"

# Node types considered whitespace or trivial
_TRIVIAL_NODE_TYPES = frozenset({
    "text",
    "whitespace",
    "\n",
    " ",
    "\t",
    "newline",
    "indent",
    "dedent",
    ";",
})


def get_node_text(node: Node, source_code: str) -> str:
    """Get the text content of an AST node.

    Args:
        node: Tree-sitter node
        source_code: Original source code string

    Returns:
        Text content of the node
    """
    source_bytes = source_code.encode(_DEFAULT_ENCODING)
    return source_bytes[node.start_byte : node.end_byte].decode(_DEFAULT_ENCODING)


def find_nodes_by_type(node: Node, node_type: str) -> list[Node]:
    """Find all descendant nodes of a specific type (recursive).

    Args:
        node: Root node to search from
        node_type: Type of nodes to find

    Returns:
        List of matching nodes (depth-first order)
    """
    results: list[Node] = []
    _collect_nodes_by_type(node, node_type, results)
    return results


def find_child_by_type(node: Node, child_type: str) -> Node | None:
    """Find the first direct child of a specific type.

    Args:
        node: Parent node to search in
        child_type: Type of child node to find

    Returns:
        First matching child node or None
    """
    for child in node.children:
        if child.type == child_type:
            return child
    return None


def find_children_by_type(node: Node, child_type: str) -> list[Node]:
    """Find all direct children of a specific type.

    Args:
        node: Parent node to search in
        child_type: Type of children to find

    Returns:
        List of matching child nodes
    """
    return [child for child in node.children if child.type == child_type]


def is_trivial_node(node: Node) -> bool:
    """Check if a node represents whitespace or trivial content.

    Args:
        node: Tree-sitter node to check

    Returns:
        True if node is whitespace or trivial
    """
    return node.type in _TRIVIAL_NODE_TYPES


def _collect_nodes_by_type(
    node: Node, node_type: str, results: list[Node]
) -> None:
    """Recursively collect nodes of a specific type.

    Args:
        node: Current node to examine
        node_type: Type of nodes to collect
        results: List to append matching nodes to
    """
    if node.type == node_type:
        results.append(node)

    for child in node.children:
        _collect_nodes_by_type(child, node_type, results)
```

---

## How Languages Handle Different Constructs

Each language extracts what makes sense for it:

| Language   | Callables                                      | Type Definitions                           |
| ---------- | ---------------------------------------------- | ------------------------------------------ |
| PHP        | `function`, `method`                           | `class`                                    |
| TypeScript | `function`, `method`, `arrow_function`         | `class`, `interface`, `enum`, `type_alias` |
| Python     | `function`, `method`, `lambda`                 | `class`                                    |
| Java       | `method`                                       | `class`, `interface`, `enum`               |
| Go         | `function`, `method`                           | `struct`, `interface`                      |
| Rust       | `function`, `method`                           | `struct`, `trait`, `enum`                  |

Downstream consumers filter by `kind`:

```python
# Get only interfaces
interfaces = [t for t in result.type_definitions if t.kind == "interface"]

# Get only async functions
async_funcs = [c for c in result.callables if c.is_async]
```

---

## Task Breakdown

### Phase 1: New Data Models & Infrastructure

| Task    | Description                                                            | Files                            |
| ------- | ---------------------------------------------------------------------- | -------------------------------- |
| **1.1** | Create `languages/models.py` with `CallableModel`, `TypeDefinitionModel`, `MemberModel`, `LanguageExtractionResult` | `languages/models.py` (new)      |
| **1.2** | Create `languages/protocols.py` with `LanguageSupport` protocol        | `languages/protocols.py` (new)   |
| **1.3** | Create `languages/base.py` with shared AST utilities (from `extractors/base.py`) | `languages/base.py` (new)        |
| **1.4** | Implement `LanguageRegistry` with entry point discovery                | `languages/__init__.py` (new)    |
| **1.5** | Add tests for models and registry                                      | `tests/languages/` (new)         |

### Phase 2: Migrate PHP to Plugin

| Task    | Description                                                 | Files                               |
| ------- | ----------------------------------------------------------- | ----------------------------------- |
| **2.1** | Create `languages/php/node_types.py` with PHP AST constants | `languages/php/node_types.py` (new) |
| **2.2** | Implement `PHPLanguageSupport.extract()` method             | `languages/php/__init__.py` (new)   |
| **2.3** | Migrate existing PHP tests to new structure                 | `tests/languages/php/` (new)        |

### Phase 3: Add TypeScript Support

| Task    | Description                                                      | Files                                      |
| ------- | ---------------------------------------------------------------- | ------------------------------------------ |
| **3.1** | Create `languages/typescript/node_types.py`                      | `languages/typescript/node_types.py` (new) |
| **3.2** | Implement `TypeScriptLanguageSupport.extract()` for functions    | `languages/typescript/__init__.py` (new)   |
| **3.3** | Add TypeScript class extraction                                  | `languages/typescript/__init__.py`         |
| **3.4** | Add TypeScript interface extraction                              | `languages/typescript/__init__.py`         |
| **3.5** | Add TypeScript enum extraction                                   | `languages/typescript/__init__.py`         |
| **3.6** | Add TypeScript tests with real code samples                      | `tests/languages/typescript/` (new)        |

### Phase 4: Refactor Core & Update Schema

| Task    | Description                                               | Files                             |
| ------- | --------------------------------------------------------- | --------------------------------- |
| **4.1** | Update `schemas/source_code.py` with new models           | `schemas/source_code.py`          |
| **4.2** | Create JSON schema v2.0.0                                 | `schemas/json_schemas/.../2.0.0/` |
| **4.3** | Refactor `parser.py` to use LanguageRegistry              | `parser.py`                       |
| **4.4** | Refactor `analyser.py` to use new extraction flow         | `analyser.py`                     |
| **4.5** | Update `pyproject.toml` with entry points + optional deps | `pyproject.toml`                  |
| **4.6** | Update `ProcessingPurposeAnalyser` schema reader for v2.0.0 | `waivern-processing-purpose-analyser/schema_readers/` |

### Phase 5: Testing & Cleanup

| Task    | Description                                    | Files          |
| ------- | ---------------------------------------------- | -------------- |
| **5.1** | Integration tests for PHP + TypeScript         | `tests/`       |
| **5.2** | Test language auto-detection                   | `tests/`       |
| **5.3** | Remove deprecated `extractors/` directory      | `extractors/`  |
| **5.4** | Run `./scripts/dev-checks.sh` and fix issues   | -              |

---

## Updated pyproject.toml

```toml
[project.optional-dependencies]
php = ["tree-sitter-php>=0.22.0"]
typescript = ["tree-sitter-typescript>=0.21.0"]
all-languages = ["waivern-source-code-analyser[php,typescript]"]
tree-sitter = ["waivern-source-code-analyser[php]"]  # Backwards compat
all = ["waivern-source-code-analyser[all-languages]"]

[project.entry-points."waivern.source_code_languages"]
php = "waivern_source_code_analyser.languages.php:PHPLanguageSupport"
typescript = "waivern_source_code_analyser.languages.typescript:TypeScriptLanguageSupport"
```

---

## TypeScript Specifics

**Extensions:** `.ts`, `.tsx`

**Tree-sitter binding:** Use `tree_sitter_typescript.language_tsx()` to handle both TS and TSX

**Extracted constructs:**

| Construct    | `kind`         | Notes                                |
| ------------ | -------------- | ------------------------------------ |
| Functions    | `function`     | Regular function declarations        |
| Arrow funcs  | `arrow_function` | `const foo = () => {}`             |
| Methods      | `method`       | Inside classes                       |
| Classes      | `class`        | Class declarations                   |
| Interfaces   | `interface`    | Interface declarations               |
| Enums        | `enum`         | Enum declarations                    |
| Type aliases | `type_alias`   | `type Foo = ...`                     |

---

## Schema Migration

Output schema changes from v1.0.0 to v2.0.0:

**v1.0.0 (current):**
```python
functions: list[SourceCodeFunctionModel]
classes: list[SourceCodeClassModel]
```

**v2.0.0 (new):**
```python
callables: list[CallableModel]
type_definitions: list[TypeDefinitionModel]
```

This is a breaking change. Downstream analysers (e.g., `ProcessingPurposeAnalyser`) that consume `source_code` schema will need updates.

---

## Critical Files to Modify

1. `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/parser.py`
2. `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/analyser.py`
3. `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/schemas/source_code.py`
4. `libs/waivern-source-code-analyser/pyproject.toml`
5. `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schema_readers/source_code_2_0_0.py` (new)
6. Remove: `extractors/functions.py`, `extractors/classes.py`, `extractors/base.py`

---

## Execution Order

1. **Phase 1** → Create models and infrastructure (foundation)
2. **Phase 2** → Migrate PHP (validates the new design works)
3. **Phase 3** → Add TypeScript (main deliverable)
4. **Phase 4** → Refactor core and update schema
5. **Phase 5** → Test and cleanup
