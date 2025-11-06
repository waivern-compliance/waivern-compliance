# Schema Versioning with Pydantic Models

**Status:** Decided
**Date:** 2025-01-06
**Decision Makers:** Architecture Team
**Scope:** Schema evolution strategy for WCF components

## Context

The Waivern Compliance Framework implements a schema versioning system where components (Connectors and Analysers) declare support for multiple schema versions through file-based auto-discovery. As schemas evolve, we need a strategy for managing Pydantic models alongside schema changes whilst maintaining type safety and backward compatibility.

## Problem Statement

When a schema version changes (e.g., `standard_input` v1.0.0 → v1.1.0 or v2.0.0), we must decide:

1. How to structure Pydantic models to represent different schema versions
2. Whether to version model class names (`StandardInputDataModel` vs `StandardInputDataModelV1_0_0`)
3. How to handle transformations between versions
4. How to keep analysers simple whilst supporting multiple schema versions
5. Where transformation logic should live (reader/producer vs analyser)

## Research Summary

### Industry Patterns Examined

**1. Avro/Protobuf (Data Systems)**
- Strict backward/forward compatibility rules
- Schema registry tracks all versions
- Default values enable safe field addition/removal
- Transformations handle incompatibilities

**2. FastAPI (API Versioning)**
- Separate model classes per version (`UserV1`, `UserV2`)
- Inheritance for incremental changes
- Models co-located with version-specific endpoints

**3. Pydantic Community Consensus**
- Inheritance with field override (most readable)
- Avoid dynamic model creation (obscures schema)
- Keep models explicit and declarative

### Compatibility Types

- **BACKWARD**: New code reads old data (most common for consumers)
- **FORWARD**: Old code reads new data
- **FULL**: Both directions work (most restrictive)

### Key Insight

**You rarely need both old AND new models active simultaneously.** Instead, you need **transformation** between versions to a canonical format.

## Decision

**Adopt the "Canonical Model + Adapter Pattern":**

- Maintain **ONE canonical Pydantic model** per schema concept
- The canonical model represents the **current stable internal format**
- Reader modules transform **FROM** version-specific wire format **TO** canonical format
- Producer modules transform **FROM** canonical format **TO** version-specific wire format
- Analysers work exclusively with canonical models (version-agnostic)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  waivern-core/schemas/                      │
├─────────────────────────────────────────────────────────────┤
│  StandardInputDataModel  (canonical - latest stable)        │
│  - Used by analysers internally                             │
│  - Stable API for components                                │
│  - Evolves carefully with version bumps                     │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    Pydantic model validation
                              │
             ┌────────────────┴────────────────┐
             │                                  │
┌────────────┴────────────┐    ┌──────────────┴──────────────┐
│  schema_readers/        │    │  schema_producers/          │
├─────────────────────────┤    ├─────────────────────────────┤
│ standard_input_1_0_0.py │    │ finding_1_0_0.py            │
│ standard_input_1_1_0.py │    │ finding_1_1_0.py            │
│ standard_input_2_0_0.py │    │ finding_2_0_0.py            │
├─────────────────────────┤    ├─────────────────────────────┤
│ - Transform TO canonical│    │ - Transform FROM canonical  │
│ - Version-specific logic│    │ - Version-specific output   │
│ - Pydantic validation   │    │ - Dict or Pydantic output   │
└─────────────────────────┘    └─────────────────────────────┘
```

## Implementation Guidelines

### 1. Canonical Model Structure

**Location:** `waivern-core/schemas/{schema_name}.py` (for shared schemas) or component-specific location

**Pattern:**
```python
class StandardInputDataModel[MetadataT: BaseMetadata](BaseModel):
    """Canonical model representing the current stable internal format.

    This model is used by all analysers for processing. Readers transform
    wire-format data to this canonical structure.

    Current canonical version: 1.0.0

    Version History:
    - 1.0.0 (2024-10-01): Initial release
    - 1.1.0 (2024-11-15): Added optional 'tags' field

    Migration Notes:
    - When bumping to v2.0.0, update all schema_readers to transform to new structure
    """
    schemaVersion: str
    name: str
    data: list[StandardInputDataItemModel[MetadataT]]
    description: str | None = None
    contentEncoding: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**Guidelines:**
- Document current canonical version
- Maintain version history in docstring
- Use clear field names (avoid abbreviations)
- Provide sensible defaults for optional fields

### 2. Reader Module Pattern

**Location:** `{component}/schema_readers/{schema_name}_{major}_{minor}_{patch}.py`

**Signature:**
```python
def read(content: dict[str, Any]) -> CanonicalModel:
    """Transform {schema_name} v{version} to canonical format."""
```

**Implementation Patterns:**

#### Pattern A: Pass-Through (Version Matches Canonical)

```python
# schema_readers/standard_input_1_0_0.py
from typing import Any
from waivern_core.schemas import StandardInputDataModel, BaseMetadata


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform standard_input v1.0.0 to canonical format.

    This version matches the canonical model structure, so we use
    direct Pydantic validation without transformation.

    Args:
        content: Data conforming to standard_input v1.0.0 schema

    Returns:
        Validated StandardInputDataModel instance

    Raises:
        ValidationError: If content doesn't match schema structure
    """
    return StandardInputDataModel[BaseMetadata].model_validate(content)
```

#### Pattern B: Non-Breaking Addition (New Optional Fields)

```python
# schema_readers/standard_input_1_1_0.py
from typing import Any
from waivern_core.schemas import StandardInputDataModel, BaseMetadata


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform standard_input v1.1.0 to canonical format.

    v1.1.0 added optional 'tags' field. If canonical has been updated
    to include this field, direct validation works. If not, we strip it.

    Args:
        content: Data conforming to standard_input v1.1.0 schema

    Returns:
        Validated StandardInputDataModel instance
    """
    # If canonical model has 'tags' field, this works directly
    return StandardInputDataModel[BaseMetadata].model_validate(content)

    # If canonical doesn't have 'tags' yet, strip it:
    # filtered = {k: v for k, v in content.items() if k != 'tags'}
    # return StandardInputDataModel[BaseMetadata].model_validate(filtered)
```

#### Pattern C: Breaking Change (Field Rename/Restructure)

```python
# schema_readers/standard_input_2_0_0.py
from typing import Any
from pydantic import BaseModel
from waivern_core.schemas import StandardInputDataModel, BaseMetadata


class _StandardInputV2WireFormat(BaseModel):
    """Private model representing v2.0.0 wire format structure.

    v2.0.0 renamed 'data' → 'items' and restructured metadata.
    This model is only for parsing the wire format.
    """
    schemaVersion: str
    name: str
    items: list[dict[str, Any]]  # Renamed from 'data'
    tags: list[str] = []
    # ... other v2.0.0 specific fields


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform standard_input v2.0.0 to canonical v1.x format.

    v2.0.0 introduced breaking changes (renamed fields, new structure).
    We transform back to the stable v1.x canonical format so analysers
    don't need updates.

    Transformations:
    - Rename 'items' back to 'data'
    - Strip v2.0.0-specific fields not in canonical
    - Restructure metadata if needed

    Args:
        content: Data conforming to standard_input v2.0.0 schema

    Returns:
        StandardInputDataModel in canonical v1.x format
    """
    # Parse with v2 structure for validation
    v2_data = _StandardInputV2WireFormat.model_validate(content)

    # Transform to canonical v1.x structure
    canonical_dict = {
        "schemaVersion": "1.0.0",  # Normalize to canonical version
        "name": v2_data.name,
        "data": v2_data.items,  # Rename back to 'data'
        "description": None,  # v2 might not have this
        "contentEncoding": None,
        "source": None,
        "metadata": {},  # Transform metadata if needed
    }

    return StandardInputDataModel[BaseMetadata].model_validate(canonical_dict)
```

### 3. Producer Module Pattern

**Location:** `{component}/schema_producers/{schema_name}_{major}_{minor}_{patch}.py`

**Signature:**
```python
def produce(internal_data: ...) -> dict[str, Any]:
    """Transform internal data to {schema_name} v{version} format."""
```

**Implementation:**

```python
# schema_producers/personal_data_finding_1_0_0.py
from typing import Any
from waivern_core.schemas import BaseAnalysisOutputMetadata
from waivern_personal_data_analyser.schemas.types import PersonalDataFindingModel


def produce(
    findings: list[PersonalDataFindingModel],
    summary: dict[str, Any],
    analysis_metadata: BaseAnalysisOutputMetadata,
    validation_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform internal result to personal_data_finding v1.0.0 format.

    Args:
        findings: List of validated PersonalDataFindingModel instances
        summary: Summary statistics dictionary
        analysis_metadata: Analysis metadata model
        validation_summary: Optional LLM validation summary (v1.0.0 doesn't include this)

    Returns:
        Dictionary conforming to personal_data_finding v1.0.0 JSON schema
    """
    # Convert Pydantic models to dicts
    findings_dicts = [
        finding.model_dump(mode="json", exclude_none=True)
        for finding in findings
    ]

    # Build v1.0.0 output structure
    return {
        "findings": findings_dicts,
        "summary": summary,
        "analysis_metadata": analysis_metadata.model_dump(
            mode="json", exclude_none=True
        ),
        # validation_summary intentionally omitted for v1.0.0
    }
```

### 4. When to Update Canonical Models

#### DO Update Canonical When:

✅ **Non-breaking addition** (new optional field)
```python
# Before
class Model(BaseModel):
    name: str

# After - SAFE to update canonical
class Model(BaseModel):
    name: str
    tags: list[str] = []  # New optional field
```

✅ **Field type widening** (more permissive)
```python
# Before
class Model(BaseModel):
    count: int

# After - SAFE if semantically correct
class Model(BaseModel):
    count: int | str  # Now accepts both
```

✅ **Relaxing constraints**
```python
# Before
class Model(BaseModel):
    email: str = Field(min_length=5)

# After - SAFE
class Model(BaseModel):
    email: str = Field(min_length=3)  # Less restrictive
```

#### DON'T Update Canonical When:

❌ **Breaking rename/removal**
```python
# Before
class Model(BaseModel):
    data: list[dict]

# After - BREAKING! Don't update canonical
class Model(BaseModel):
    items: list[dict]  # Field renamed
```

**Instead:** Keep canonical stable, have readers transform:
```python
def read_v2(content: dict) -> Model:
    # Transform v2's 'items' to canonical 'data'
    return Model(data=content['items'])
```

❌ **Structure reorganization**
```python
# Before
class Model(BaseModel):
    user_name: str
    user_email: str

# After - BREAKING! Don't update canonical
class Model(BaseModel):
    user: UserInfo  # Nested structure
```

❌ **Major version bump with semantic changes**

**Instead:** Keep canonical on stable major version, transform newer versions to it.

### 5. Evolution Scenarios

#### Scenario 1: Add Optional Field (v1.0.0 → v1.1.0)

**Schema Change:** Add optional `tags: list[str]` field

**Actions:**
1. ✅ Update canonical model with new optional field
2. ✅ Create `standard_input_1_1_0.py` reader (pass-through)
3. ✅ Old `standard_input_1_0_0.py` reader still works (Pydantic fills defaults)
4. ✅ No analyser changes needed

**Code:**
```python
# Update canonical
class StandardInputDataModel(BaseModel):
    # ... existing fields
    tags: list[str] = Field(default_factory=list)  # NEW

# New reader (pass-through)
def read(content: dict) -> StandardInputDataModel:
    return StandardInputDataModel.model_validate(content)
```

#### Scenario 2: Rename Field (v1.1.0 → v2.0.0)

**Schema Change:** Rename `data` → `items`

**Actions - Option A (Keep Canonical Stable - Recommended):**
1. ✅ Keep canonical model at v1.x structure
2. ✅ Create `standard_input_2_0_0.py` reader with transformation
3. ✅ Analysers unchanged (still use `data` field)

**Code:**
```python
# Canonical unchanged (still has 'data' field)
class StandardInputDataModel(BaseModel):
    data: list[dict]  # Stable

# v2.0.0 reader transforms new format
def read(content: dict) -> StandardInputDataModel:
    return StandardInputDataModel(
        data=content['items'],  # Transform items → data
        # ... other fields
    )
```

**Actions - Option B (Bump Canonical - More Disruptive):**
1. ⚠️ Update canonical model to v2.0.0 structure
2. ⚠️ Update ALL old readers to transform to v2.0.0
3. ⚠️ **Refactor ALL analysers** to use new field names

**Code:**
```python
# Bump canonical to v2.0.0
class StandardInputDataModel(BaseModel):
    items: list[dict]  # RENAMED

# v1.0.0 reader now transforms OLD format
def read(content: dict) -> StandardInputDataModel:
    return StandardInputDataModel(
        items=content['data'],  # Transform data → items
        # ... other fields
    )

# All analysers must be updated:
# OLD: for item in data.data:
# NEW: for item in data.items:
```

**Recommendation:** Use Option A unless you have compelling reasons to standardize on v2.0.0 internally.

#### Scenario 3: Add Validation Summary (Finding Output)

**Schema Change:** personal_data_finding v1.0.0 → v1.1.0 adds optional `validation_summary`

**Actions:**
1. ✅ Update internal result dict to include `validation_summary` when present
2. ✅ Create `personal_data_finding_1_1_0.py` producer that includes it
3. ✅ Keep `personal_data_finding_1_0_0.py` producer that omits it
4. ✅ No analyser changes (already produces validation_summary in internal format)

**Code:**
```python
# v1.0.0 producer (omits validation_summary)
def produce(..., validation_summary=None) -> dict:
    return {
        "findings": [...],
        "summary": {...},
        # validation_summary omitted for v1.0.0 compatibility
    }

# v1.1.0 producer (includes validation_summary)
def produce(..., validation_summary=None) -> dict:
    result = {
        "findings": [...],
        "summary": {...},
    }
    if validation_summary:
        result["validation_summary"] = validation_summary
    return result
```

### 6. Testing Strategy

**Test Each Reader/Producer Module Independently:**

```python
# tests/schema_readers/test_standard_input_1_0_0.py
class TestStandardInputV1_0_0Reader:
    def test_read_transforms_required_fields(self):
        """Test v1.0.0 reader extracts all required fields."""
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "test",
            "data": [{"content": "test", "metadata": {}}],
        }

        result = standard_input_1_0_0.read(input_data)

        assert isinstance(result, StandardInputDataModel)
        assert result.schemaVersion == "1.0.0"
        assert result.name == "test"
        assert len(result.data) == 1

    def test_read_handles_optional_fields(self):
        """Test v1.0.0 reader preserves optional fields."""
        # ...

    def test_read_raises_on_invalid_data(self):
        """Test v1.0.0 reader raises ValidationError for invalid data."""
        with pytest.raises(ValidationError):
            standard_input_1_0_0.read({"invalid": "data"})
```

**Test Transformation Logic:**

```python
# tests/schema_readers/test_standard_input_2_0_0.py
class TestStandardInputV2_0_0Reader:
    def test_transforms_items_to_data(self):
        """Test v2.0.0 reader transforms 'items' field to 'data'."""
        v2_input = {
            "schemaVersion": "2.0.0",
            "name": "test",
            "items": [{"content": "test"}],  # v2.0.0 uses 'items'
        }

        result = standard_input_2_0_0.read(v2_input)

        assert isinstance(result, StandardInputDataModel)
        assert hasattr(result, "data")  # Canonical uses 'data'
        assert len(result.data) == 1
```

### 7. File Organization

```
libs/waivern-core/src/waivern_core/schemas/
├── __init__.py
├── base.py                      # Schema class, registry
├── types.py                     # Shared base types
├── standard_input.py            # Canonical StandardInputDataModel
└── json_schemas/
    └── standard_input/
        ├── 1.0.0/
        │   └── standard_input.json
        ├── 1.1.0/
        │   └── standard_input.json
        └── 2.0.0/
            └── standard_input.json

libs/waivern-personal-data-analyser/
├── src/waivern_personal_data_analyser/
│   ├── analyser.py
│   ├── schema_readers/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── standard_input_1_0_0.py
│   │   ├── standard_input_1_1_0.py
│   │   └── standard_input_2_0_0.py
│   ├── schema_producers/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── personal_data_finding_1_0_0.py
│   │   └── personal_data_finding_1_1_0.py
│   └── schemas/
│       ├── types.py             # PersonalDataFindingModel (canonical)
│       └── json_schemas/
│           └── personal_data_finding/
│               ├── 1.0.0/
│               │   └── personal_data_finding.json
│               └── 1.1.0/
│                   └── personal_data_finding.json
└── tests/waivern_personal_data_analyser/
    ├── schema_readers/
    │   ├── test_standard_input_1_0_0.py
    │   ├── test_standard_input_1_1_0.py
    │   └── test_standard_input_2_0_0.py
    └── schema_producers/
        ├── test_personal_data_finding_1_0_0.py
        └── test_personal_data_finding_1_1_0.py
```

## Consequences

### Positive

✅ **Type Safety:** Pydantic validation at every boundary
✅ **Analyser Simplicity:** Components work with one canonical type
✅ **Clear Separation:** Version complexity isolated in readers/producers
✅ **Flexibility:** Easy to add new versions without touching analysers
✅ **Gradual Evolution:** Can choose when to bump canonical version
✅ **Testability:** Each reader/producer tested independently
✅ **IDE Support:** Autocomplete, refactoring, type checking all work

### Negative

⚠️ **Transformation Cost:** Non-trivial transformations add processing overhead
⚠️ **Cognitive Load:** Developers must understand canonical vs wire format
⚠️ **Documentation Burden:** Must document version history clearly
⚠️ **Migration Planning:** Bumping canonical requires careful coordination

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Canonical model diverges too far from reality | Regular review of canonical fit, bump when needed |
| Transformation bugs introduce data corruption | Comprehensive testing, schema validation both sides |
| Performance degradation from transformations | Profile critical paths, optimize hot transformations |
| Confusion about which version is canonical | Clear documentation, version history in docstrings |

## Alternatives Considered

### Alternative 1: Version-Specific Model Classes

**Pattern:**
```python
class StandardInputDataModelV1_0_0(BaseModel): ...
class StandardInputDataModelV1_1_0(StandardInputDataModelV1_0_0): ...
class StandardInputDataModelV2_0_0(BaseModel): ...
```

**Rejected Because:**
- Model explosion (12 versions = 12 classes)
- Analysers must handle Union types
- Migration burden when bumping versions
- Doesn't solve transformation problem

### Alternative 2: Dict-Based Internal Format

**Pattern:**
```python
def read(content: dict) -> dict:
    return {"name": content["name"], ...}
```

**Rejected Because:**
- No type safety
- No validation at boundaries
- Error-prone (key typos)
- Inconsistent with existing WCF patterns

### Alternative 3: Dynamic Model Creation

**Pattern:**
```python
Model = create_model('Model', **fields)
```

**Rejected Because:**
- Obscures schema definition
- Poor IDE support
- Violates "readability counts"
- Debugging difficulty

## Implementation Checklist

When adding a new schema version:

- [ ] Create JSON schema file in `json_schemas/{schema}/{version}/`
- [ ] Decide: Does this require canonical model update?
  - [ ] If non-breaking addition: Update canonical model
  - [ ] If breaking change: Keep canonical stable OR plan migration
- [ ] Create reader module `schema_readers/{schema}_{major}_{minor}_{patch}.py`
  - [ ] Implement `read(content: dict) -> CanonicalModel`
  - [ ] Add docstring explaining transformations
  - [ ] Handle all fields (required + optional)
- [ ] Create producer module (if output schema) `schema_producers/{schema}_{major}_{minor}_{patch}.py`
  - [ ] Implement `produce(...) -> dict`
  - [ ] Add docstring explaining output structure
  - [ ] Handle version-specific fields
- [ ] Write comprehensive tests
  - [ ] Test required field transformation
  - [ ] Test optional field handling
  - [ ] Test edge cases (empty arrays, None values)
  - [ ] Test validation errors
- [ ] Update canonical model docstring with version history
- [ ] Update any affected documentation
- [ ] Run all tests to ensure no regressions

## References

- [Pydantic Documentation - Model Configuration](https://docs.pydantic.dev/)
- [Schema Evolution in Avro](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [FastAPI Versioning Patterns](https://fastapi.tiangolo.com/)
- [WCF Schema Versioning Design](./active/schema-versioning/design.md)
- [Building Custom Components Guide](./building-custom-components.md)

## Related Documents

- [Schema Versioning Implementation Steps](./active/schema-versioning/)
- [WCF Core Components](../core-concepts/wcf-core-components.md)
- [Extending WCF](./extending-wcf.md)

---

**Document Maintenance:**
- Review after each major schema version release
- Update with new evolution scenarios as they arise
- Collect feedback from component developers
- Refine guidelines based on real-world usage
