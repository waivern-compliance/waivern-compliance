# ADR-0001: Use Explicit Configuration for Schema Loading

## Status

Accepted

## Context

The Waivern Compliance Framework (WCF) is architected as a monorepo with multiple independent packages (waivern-core, waivern-community, waivern-mysql, etc.). Each package must be independently testable and distributable without requiring the entire workspace or application context.

### Requirements

Any solution must satisfy:

- **Package independence**: Each package can be tested and distributed independently
- **Schema co-location**: Schemas live with their owning components
- **Zero runtime magic**: Debuggable schema loading without hidden conventions
- **Production-ready**: Works in both development (editable installs) and production (pip install from PyPI)
- **Type-safe**: Full type-checker support without special configuration

### Alternative Approaches Considered

We evaluated 7 architectural patterns from similar open-source tools:

#### 1. Entry Points Pattern (pytest, setuptools)

**How it works**: Components register via `pyproject.toml` entry points, discovered at runtime via `importlib.metadata`.

```toml
[project.entry-points."waivern.schemas"]
source_code = "waivern_community.connectors.source_code:SourceCodeSchema"
```

**Pros**:
- Standard Python packaging mechanism
- Automatic discovery across installed packages
- Enables third-party extensions

**Cons**:
- Requires installation to work (breaks development workflow)
- Magic discovery makes debugging harder
- Adds packaging complexity
- Overkill for monorepo where all components are known

#### 2. Autodiscovery Pattern (Django, Airflow)

**How it works**: Framework scans filesystem for modules matching naming conventions (e.g., `schemas.py`).

```python
def discover_schemas():
    for module in scan_modules("schemas"):
        import_module(module)
```

**Pros**:
- Zero configuration per component
- Convention over configuration

**Cons**:
- Implicit conventions are fragile
- Hard to debug when discovery fails
- Namespace collisions possible
- Slower startup (filesystem scanning)
- Type checkers can't validate discovered items

#### 3. Declarative Base Pattern (SQLAlchemy)

**How it works**: Shared base class with metaclass magic for automatic registration.

```python
class SchemaBase(metaclass=SchemaMeta):
    __schema_registry__ = {}
```

**Pros**:
- Automatic registration on class definition
- Clean inheritance hierarchy

**Cons**:
- Heavy metaclass magic
- Still requires explicit schema file paths somewhere
- Doesn't solve the "where to load files from" problem

#### 4. importlib.resources Pattern (Python stdlib)

**How it works**: Use `importlib.resources` for package resource management.

```python
from importlib.resources import files
schema_path = files("waivern_community") / "schemas" / "source_code.json"
```

**Pros**:
- Official Python standard for package resources
- Works with zip-installed packages
- Type-checker friendly

**Cons**:
- Still requires each component to specify its path
- More verbose than `Path(__file__)`
- No actual boilerplate reduction
- Added stdlib dependency

#### 5. RPC Plugin Pattern (Terraform providers)

**How it works**: External binaries communicate via RPC, each responsible for own resources.

**Pros**:
- Complete independence
- Language-agnostic

**Cons**:
- Massive complexity overhead
- Not applicable to Python monorepo

#### 6. Explicit Registration Pattern (Pydantic, FastAPI)

**How it works**: Components explicitly import and register.

```python
from waivern_core import register_schema
register_schema(SourceCodeSchema)
```

**Pros**:
- Explicit and debuggable
- Full type-checker support
- No magic

**Cons**:
- Requires import-time side effects
- Still needs each component to specify schema file location
- Doesn't reduce configuration burden

#### 7. Package-relative Pattern (WCF current approach)

**How it works**: Each component explicitly configures its schema location using `Path(__file__)`.

```python
from pathlib import Path
from waivern_core.schemas.base import JsonSchemaLoader

@dataclass(frozen=True, slots=True, eq=False)
class SourceCodeSchema(Schema):
    _loader: SchemaLoader = field(
        default_factory=lambda: JsonSchemaLoader(
            search_paths=[Path(__file__).parent / "json_schemas"]
        ),
        init=False,
    )
```

**Pros**:
- Zero magic: path resolution is explicit and traceable
- Package independence: each component self-contained
- Type-safe: full static analysis support
- Production-ready: works in all installation modes
- Debuggable: clear stack traces, no hidden imports
- Standard Python: uses `pathlib.Path` and `__file__`

**Cons**:
- 6 lines of boilerplate per schema class
- Repetitive pattern across components

### Comparison Matrix

| Pattern | Boilerplate | Debuggability | Package Independence | Magic | Production Ready |
|---------|-------------|---------------|---------------------|-------|------------------|
| Entry Points | Low | Medium | High | Medium | High |
| Autodiscovery | None | Low | Medium | High | Medium |
| Declarative Base | Low | Medium | Medium | High | High |
| importlib.resources | Medium | High | High | None | High |
| RPC Plugin | N/A | High | High | None | High |
| Explicit Registration | Medium | High | High | Low | High |
| **Package-relative** | **Medium** | **High** | **High** | **None** | **High** |

## Decision

We will use **explicit package-relative configuration** with `Path(__file__)` for schema loading.

Each schema class explicitly configures its loader with the path to its JSON schema files:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class SourceCodeSchema(Schema):
    """Schema for source code analysis data format."""

    _VERSION = "1.0.0"

    # Custom loader with package-relative search path
    _loader: SchemaLoader = field(
        default_factory=lambda: JsonSchemaLoader(
            search_paths=[Path(__file__).parent / "json_schemas"]
        ),
        init=False,
    )

    @property
    @override
    def name(self) -> str:
        return "source_code"

    @property
    @override
    def version(self) -> str:
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        return self._loader.load(self.name, self.version)
```

This pattern is applied consistently across all component schemas in `waivern-community`:
- Source code connector schema
- Personal data analyser finding schema
- Data subject analyser finding schema
- Processing purpose analyser finding schema

Framework-wide schemas in `waivern-core` (like `StandardInputSchema`) use the default loader which searches `waivern_core/schemas/json_schemas/`.

## Consequences

### Positive

1. **Package independence achieved**: All packages (waivern-core, waivern-community, waivern-mysql) can run tests from their own directories without workspace context
   - waivern-mysql: 25/25 tests pass independently
   - waivern-community: 453/453 tests pass independently
   - waivern-core: 16/16 tests pass independently

2. **Clear ownership**: Schema files co-located with owning components make ownership explicit
   ```
   waivern-community/
   └── connectors/
       └── source_code/
           ├── schemas/
           │   ├── source_code.py
           │   └── json_schemas/
           │       └── source_code/
           │           └── 1.0.0/
           │               └── source_code.json
   ```

3. **Zero magic**: Path resolution is explicit and traceable - no hidden conventions, no runtime scanning, no metaclass magic

4. **Production-ready**: Works in all installation modes (editable installs, pip install, wheel distributions) without special handling

5. **Type-safe**: Full type-checker support with no special configuration or type: ignore comments needed

6. **Debuggable**: Clear stack traces pointing to exact schema locations, no import-time side effects

7. **Industry alignment**: Pattern similar to established tools like Pydantic (explicit model definition) and Terraform (explicit provider configuration)

### Negative

1. **Boilerplate**: Each schema class requires ~6 lines of loader configuration code

2. **Repetition**: The pattern is repeated across all component schemas (currently 4 in waivern-community)

3. **Potential for copy-paste errors**: Developers might forget to update the path when copying schema classes

### Neutral

1. **No third-party plugin support**: This pattern doesn't enable external packages to contribute schemas, but this is not a current requirement

2. **Manual configuration**: Schema loading requires explicit configuration rather than automatic discovery, but this aligns with the framework's preference for explicitness

### Mitigation Strategies

The boilerplate concern is acknowledged with a TODO comment in `JsonSchemaLoader`:

```python
"""Loads schemas from local JSON files with caching.

TODO: Reduce boilerplate by making loader automatically search relative to
calling schema's location (Phase 5). Current approach requires each schema
to explicitly provide custom search_paths, which is repetitive.
"""
```

Future enhancements could include:
- Helper function to generate loader configuration
- Automatic path detection based on calling module location
- Schema class decorator to reduce configuration

However, these optimizations are deferred in favor of shipping a working, debuggable solution that solves the immediate problem of package independence.

### Trade-offs Accepted

We explicitly choose **clarity and debuggability over DRY (Don't Repeat Yourself)**:

- The "boilerplate" is actually component-specific configuration - each component truly needs to declare where its schemas live
- 6 lines per schema is acceptable given the framework has ~10 total schemas
- The explicitness makes onboarding easier (no magic to learn)
- Troubleshooting is straightforward (no hidden path resolution logic)

This aligns with the framework's design philosophy: favour explicitness and type safety over clever abstractions.

## References

- [Michael Nygard's ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [pytest entry points documentation](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#making-your-plugin-installable-by-others)
- [Django app autodiscovery](https://docs.djangoproject.com/en/stable/ref/applications/)
- [SQLAlchemy declarative base](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html)
- [Python importlib.resources](https://docs.python.org/3/library/importlib.resources.html)
- [Terraform provider protocol](https://developer.hashicorp.com/terraform/plugin/how-terraform-works)
- [Pydantic model configuration](https://docs.pydantic.dev/latest/concepts/models/)

## Related Decisions

None yet. This is the first ADR for the Waivern Compliance Framework.

## History

- **2025-10-20**: Decision accepted and implemented across all framework packages
- **2025-10-21**: ADR created to document architectural decision
