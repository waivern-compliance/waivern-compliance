# WCF Schema Architecture

## Overview

The Waivern Compliance Framework (WCF) uses a **package-centric schema architecture** where schemas are co-located with their owning components. This design enables framework packages to be independently testable without workspace dependencies.

## Schema Ownership Principles

**A schema should be owned by the package that defines its contract:**

### 1. Framework-Wide Schemas → `waivern-core`
Schemas used by multiple components across the framework:
- `StandardInputSchema` - Universal connector output format
- `BaseFindingSchema` - Base class for analyser outputs

**Location:** `libs/waivern-core/src/waivern_core/schemas/json_schemas/`

### 2. Component-Specific Schemas → Component Package
Schemas that define a single component's output:
- Source code analyser → `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/schemas/json_schemas/source_code/`
- Personal data analyser → `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schemas/json_schemas/personal_data_finding/`
- Data subject analyser → `libs/waivern-data-subject-analyser/src/waivern_data_subject_analyser/schemas/json_schemas/data_subject_finding/`
- Processing purpose analyser → `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schemas/json_schemas/processing_purpose_finding/`

### 3. Domain-Shared Schemas → Domain Package
When multiple components in the same domain share a schema:
- Database connectors sharing metadata schema → `waivern-connectors-database`

### 4. Application Schemas → Application Package
Schemas specific to the application:
- Runbook configuration → `apps/wct/src/wct/schemas/json_schemas/runbook/`

## Schema Directory Structure

Each schema follows this structure:

```
component_package/
├── schemas/
│   ├── __init__.py
│   ├── your_schema.py              # Python schema class
│   └── json_schemas/               # JSON schema files
│       └── your_schema/
│           └── 1.0.0/              # Versioned
│               ├── your_schema.json
│               └── your_schema.sample.json
```

## Implementation Patterns

### Pattern 1: Component Schema with Custom Loader

For component-specific schemas that need to load JSON from package-relative paths:

```python
"""Component schema definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class YourComponentSchema(Schema):
    """Schema for your component output.

    This schema represents the structured format used by your component
    to report findings or extracted data.
    """

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
        """Return the schema name."""
        return "your_component_schema"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema definition for validation."""
        return self._loader.load(self.name, self.version)
```

**When to use:**
- Source code connectors
- Analysers with custom output schemas
- Any component with co-located JSON schemas

### Pattern 2: Finding Schema with Custom Loader

For analyser finding schemas that inherit from `BaseFindingSchema`:

```python
"""Finding schema for analyser output."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from waivern_core.schemas.base import BaseFindingSchema, JsonSchemaLoader, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class YourFindingSchema(BaseFindingSchema):
    """Schema for your analyser finding results.

    This schema represents the structured format used by your analyser
    to report compliance findings discovered in data sources.
    """

    _VERSION = "1.0.0"

    # Override parent loader with package-relative search path
    _loader: SchemaLoader = field(
        default_factory=lambda: JsonSchemaLoader(
            search_paths=[Path(__file__).parent / "json_schemas"]
        ),
        init=False,
    )

    @property
    @override
    def name(self) -> str:
        """Return the schema name."""
        return "your_finding"

    @property
    @override
    def version(self) -> str:
        """Return the schema version."""
        return self._VERSION
```

**When to use:**
- Personal data analysers
- Data subject analysers
- Processing purpose analysers
- Any analyser producing findings

### Pattern 3: Framework-Wide Schema (Default Loader)

For schemas in `waivern-core` that use default package-relative loading:

```python
"""Framework-wide schema definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, override

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class StandardInputSchema(Schema):
    """Universal input schema for all connectors."""

    _VERSION = "1.0.0"

    # Default loader searches in waivern-core/schemas/json_schemas/
    _loader: SchemaLoader = field(default_factory=JsonSchemaLoader, init=False)

    @property
    @override
    def name(self) -> str:
        return "standard_input"

    @property
    @override
    def version(self) -> str:
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        return self._loader.load(self.name, self.version)
```

**When to use:**
- Schemas in `waivern-core` only
- Schemas that all components share

## Schema Loading Mechanism

### JsonSchemaLoader Search Order

1. **Custom search paths** (if provided via `search_paths` parameter)
2. **Package-relative paths** (`json_schemas/` directory alongside `base.py`)
3. **Caching** (schemas cached after first load)

### Example Search Paths

For `SourceCodeSchema` in `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/schemas/source_code.py`:

```python
search_paths=[Path(__file__).parent / "json_schemas"]
```

Resolves to: `libs/waivern-source-code-analyser/src/waivern_source_code_analyser/schemas/json_schemas/`

Loader will search: `json_schemas/source_code/1.0.0/source_code.json`

## Creating a New Component Schema

### Step 1: Create Directory Structure

```bash
cd libs/your-package
mkdir -p src/your_package/component_name/schemas/json_schemas/your_schema/1.0.0
```

### Step 2: Create JSON Schema File

`src/your_package/component_name/schemas/json_schemas/your_schema/1.0.0/your_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Your Schema",
  "version": "1.0.0",
  "type": "object",
  "properties": {
    "schemaVersion": {
      "type": "string",
      "const": "1.0.0"
    },
    "name": {
      "type": "string"
    },
    "data": {
      "type": "array",
      "items": {
        "type": "object"
      }
    }
  },
  "required": ["schemaVersion", "name", "data"]
}
```

### Step 3: Create Python Schema Class

`src/your_package/component_name/schemas/your_schema.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override

from waivern_core.schemas.base import JsonSchemaLoader, Schema, SchemaLoader


@dataclass(frozen=True, slots=True, eq=False)
class YourSchema(Schema):
    """Schema for your component."""

    _VERSION = "1.0.0"

    _loader: SchemaLoader = field(
        default_factory=lambda: JsonSchemaLoader(
            search_paths=[Path(__file__).parent / "json_schemas"]
        ),
        init=False,
    )

    @property
    @override
    def name(self) -> str:
        return "your_schema"

    @property
    @override
    def version(self) -> str:
        return self._VERSION

    @property
    @override
    def schema(self) -> dict[str, Any]:
        return self._loader.load(self.name, self.version)
```

### Step 4: Test from Package Directory

```bash
cd libs/your-package
uv run pytest tests/
```

### Step 5: Verify Workspace Tests

```bash
cd /path/to/workspace
uv run pytest
```

## Testing Schema Loading

### Test Schema Can Be Loaded

```python
def test_schema_loads_from_package_directory():
    """Test that schema can be loaded from package-relative path."""
    schema = YourSchema()

    # This should not raise
    schema_dict = schema.schema

    assert schema_dict["version"] == "1.0.0"
    assert "properties" in schema_dict
```

### Test Schema Validation

```python
from waivern_core.message import Message

def test_message_validates_against_schema():
    """Test that message validates against schema."""
    schema = YourSchema()

    content = {
        "schemaVersion": "1.0.0",
        "name": "test",
        "data": []
    }

    message = Message(
        id="test-message",
        content=content,
        schema=schema
    )

    # This should not raise
    message.validate()
```

## When Schemas are Shared

### Scenario: Two Components Share Output Schema

If two components in the same domain share a schema:

1. **Extract to domain package**:
   ```
   libs/domain-package/
   └── schemas/
       └── json_schemas/
           └── shared_schema/
   ```

2. **Both components reference it**:
   ```python
   # Component A
   from domain_package.schemas.shared import SharedSchema

   # Component B
   from domain_package.schemas.shared import SharedSchema
   ```

### Scenario: Cross-Domain Schema Usage

If truly cross-domain:

1. **Move to waivern-core**
2. **Update to use default loader**

Example: `standard_input` is used by MySQL, SQLite, and Filesystem connectors across multiple domains.

## Benefits of Package-Centric Architecture

- ✅ **Independent Testing**: Packages can run tests without workspace context
- ✅ **Clear Ownership**: Each schema is owned by one package
- ✅ **Self-Contained**: Components bundle their schemas
- ✅ **Version Control**: Schemas tracked alongside component code
- ✅ **Type Safety**: Python classes provide type-safe schema access

## Migration History

Prior to October 2025, all schemas were centralized in `apps/wct/src/wct/schemas/json_schemas/`. This created dependency issues where framework libraries couldn't run tests independently.

All component schemas have been migrated to their owning packages. See git history for migration details.
