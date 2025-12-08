# Personal Data Analyser Migration Notes

## Task
Migrate `waivern-personal-data-analyser` to the new Analyser interface (Task 7c).

## New Interface

**Before:**
```python
def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message
def get_supported_input_schemas(cls) -> list[Schema]
```

**After:**
```python
def process(self, inputs: list[Message], output_schema: Schema) -> Message
def get_input_requirements(cls) -> list[list[InputRequirement]]
```

## Key Changes Made

1. **Import `InputRequirement`** from `waivern_core`
2. **Replace `get_supported_input_schemas()`** with `get_input_requirements()` returning `list[list[InputRequirement]]`
3. **Update `process()` signature** to accept `list[Message]` instead of single `Message`
4. **Implement fan-in merge** - iterate over all input messages and collect data items
5. **Use `cast()`** for type safety with dynamic module loading (avoid `# type: ignore`)
6. **Update all tests** to pass `[message]` instead of `message`

## Issues Found During Review

### 1. `context` field was dead code
We added a `context` field to `PersonalDataFindingMetadata` for extensibility but:
- The pattern matcher only copied `source`, not `context`
- No tests verified the field worked

**Fix:** Added `context` to `BaseMetadata` in waivern-core (so it flows from connectors), and updated pattern matcher to copy it.

### 2. `sample_findings` fixture was misleading
The test fixture used `matched_patterns=["support@example.com"]` but the real pattern matcher matches **keywords** like `"email"`, not email addresses.

**Fix:** Updated fixture to use realistic patterns (`["email"]`, `["telephone"]`) and added docstring explaining the behaviour.

### 3. No test for JSON serialisation validator
We added a validator to ensure `context` is JSON-serialisable, but no test covered it.

**Fix:** Created `test_standard_input.py` in waivern-core with tests for valid/invalid context values.

### 4. Unused fixture parameters
Several test methods declared fixtures they didn't use (e.g., `mock_llm_service`).

**Fix:** Removed unused parameters.

### 5. Missing `dev-checks.sh` script
The package had `lint.sh`, `format.sh`, `type-check.sh` but no unified `dev-checks.sh`.

**Fix:** Created `scripts/dev-checks.sh` following the waivern-core pattern.

### 6. VS Code schema configuration was broken
The `.vscode/settings.json` pointed to a non-existent schema path, causing YAML validation errors.

**Fix:** Updated path from `./apps/wct/src/wct/schemas/json_schemas/runbook/1.0.0/runbook.json` to `./apps/wct/runbook.schema.json`.

### 7. Runbook schema was outdated
The `runbook.schema.json` was for the old format (connectors/analysers/execution) not the new artifact-centric format.

**Fix:** Regenerated with `uv run wct generate-schema`.

## Schema Refactoring

During the migration, we identified that schema types were poorly organised. We performed the following refactoring:

### Created `BaseFindingMetadata` base class

All analyser finding metadata classes now extend `BaseFindingMetadata` which provides:
- `source: str` - Source file or location where the data was found
- `context: dict[str, object]` - Extensible context for pipeline metadata

**Before:**
```python
class PersonalDataFindingMetadata(BaseModel):
    source: str = Field(...)
    context: dict[str, Any] = Field(...)
    # Duplicated validator for JSON serialisation
```

**After:**
```python
from waivern_core.schemas import BaseFindingMetadata

class PersonalDataFindingMetadata(BaseFindingMetadata):
    """Extends BaseFindingMetadata which provides source and context."""
    pass
```

### Split schema module files

The `waivern_core.schemas` module was reorganised for single responsibility:

| Old | New |
|-----|-----|
| `base.py` (408 lines) | `loader.py` - `SchemaLoader`, `JsonSchemaLoader`, `SchemaLoadError` |
| | `registry.py` - `SchemaRegistry` |
| | `schema.py` - `Schema` class |
| `types.py` | `connector_types.py` - `BaseMetadata`, `RelationalDatabaseMetadata`, `FilesystemMetadata` |
| | `finding_types.py` - `BaseFindingMetadata`, `BaseFindingModel`, `BaseFindingEvidence`, etc. |
| `standard_input.py` | Cleaned up - imports `BaseMetadata` from `connector_types.py` |

**Public API unchanged** - all exports go through `waivern_core.schemas.__init__.py`.

### Naming convention

- **`connector_types.py`** - Types for connector-generated data (input to analysers)
- **`finding_types.py`** - Types for analyser findings (output from analysers)

## Lessons Learned

1. **Always review tests after interface changes** - check fixtures match real behaviour
2. **New fields need end-to-end validation** - adding a schema field means updating all code that populates it
3. **Run the actual application** - unit tests passing doesn't mean the runbook works
4. **Check IDE integration** - schema paths and validation configurations can become stale
5. **Use base classes for shared fields** - `BaseFindingMetadata` ensures consistency across all finding types
6. **Single responsibility for modules** - splitting `base.py` into `loader.py`, `registry.py`, `schema.py` improves maintainability

## Verification

1. `./scripts/dev-checks.sh` passes for both `waivern-core` and `waivern-personal-data-analyser`
2. `uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v` executes successfully

## JSON Schema Auto-Generation from Pydantic Models

### Problem

JSON schemas were manually maintained alongside Pydantic models, leading to:
- Discrepancies between Pydantic models and JSON schemas
- Missing fields in JSON schemas (e.g., `analysis_metadata`, `validation_summary`)
- Fields added by producers not reflected in Pydantic models (e.g., `analysis_timestamp`)

### Solution

Make Pydantic models the **single source of truth** by auto-generating JSON schemas.

### Implementation

#### 1. Added `BaseSchemaOutput` to waivern-core

```python
class BaseSchemaOutput(BaseModel):
    """Base class for analyser output schemas with JSON schema generation."""

    __schema_version__: ClassVar[str] = "1.0.0"

    @classmethod
    def generate_json_schema(cls, output_path: Path) -> None:
        """Generate JSON schema file from this Pydantic model."""
        schema = cls.model_json_schema(mode="serialization")
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema["version"] = cls.__schema_version__
        # Write to file...
```

Key design decisions:
- **ClassVar for version** - Not serialised as a field, but included in generated schema
- **Subclasses override version** - Each output model defines its own `__schema_version__`
- **`mode="serialization"`** - Generates schema matching JSON output (not input validation)

#### 2. Created root-level output models

Each analyser now has a complete output model representing the wire format:

**personal-data-analyser:**
```python
class PersonalDataFindingOutput(BaseSchemaOutput):
    __schema_version__: ClassVar[str] = "1.0.0"
    findings: list[PersonalDataFindingModel]
    summary: PersonalDataSummary
    analysis_metadata: BaseAnalysisOutputMetadata
    validation_summary: PersonalDataValidationSummary | None = None
```

**data-subject-analyser:**
```python
class DataSubjectFindingOutput(BaseSchemaOutput):
    __schema_version__: ClassVar[str] = "1.0.0"
    findings: list[DataSubjectFindingModel]
    summary: DataSubjectSummary
    analysis_metadata: BaseAnalysisOutputMetadata
```

#### 3. Added `analysis_timestamp` to `BaseAnalysisOutputMetadata`

```python
class BaseAnalysisOutputMetadata(BaseModel):
    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="ISO 8601 timestamp when the analysis was performed",
    )
```

This was previously added by producers but not in the Pydantic model.

#### 4. Eliminated producers

Analysers now use output models directly:

**Before (using producer):**
```python
producer = self._load_producer(output_schema)
result_data = producer.produce(findings=findings, summary=summary, ...)
```

**After (using output model):**
```python
output_model = PersonalDataFindingOutput(
    findings=findings,
    summary=summary,
    analysis_metadata=analysis_metadata,
    validation_summary=validation_summary,
)
result_data = output_model.model_dump(mode="json", exclude_none=True)
```

Benefits:
- Pydantic validates at construction
- No separate producer modules to maintain
- Type safety throughout

#### 5. Added generate-schema scripts

Each analyser has `scripts/generate-schema.sh`:

```bash
uv run python -c "
from pathlib import Path
from waivern_personal_data_analyser.schemas import PersonalDataFindingOutput

output_path = Path('src/.../personal_data_finding.json')
PersonalDataFindingOutput.generate_json_schema(output_path)
"
```

#### 6. Added unit tests for custom code

Created `test_finding_types.py` in waivern-core with focused tests for:
- Custom validators (`validate_json_serialisable`, `validate_risk_level`)
- `generate_json_schema()` method
- ClassVar version override behaviour

**Principle:** Test our custom code, not Pydantic's built-in functionality.

### Files Changed

**waivern-core:**
- `schemas/finding_types.py` - Added `BaseSchemaOutput`, `analysis_timestamp`
- `schemas/__init__.py` - Export `BaseSchemaOutput`
- `tests/waivern_core/test_finding_types.py` - New test file

**waivern-personal-data-analyser:**
- `schemas/types.py` - Added `PersonalDataSummary`, `PersonalDataValidationSummary`, `PersonalDataFindingOutput`
- `schemas/__init__.py` - Updated exports
- `analyser.py` - Use output model directly, removed `_load_producer`
- `scripts/generate-schema.sh` - New script
- Deleted `personal_data_finding.sample.json`

**waivern-data-subject-analyser:**
- `schemas/types.py` - Added `DataSubjectSummary`, `DataSubjectFindingOutput`
- `schemas/__init__.py` - Updated exports
- `analyser.py` - Use output model directly, removed `_load_producer`
- `scripts/generate-schema.sh` - New script
- Deleted `data_subject_finding.sample.json`

### Benefits

1. **Single source of truth** - Pydantic models define the contract
2. **No drift** - JSON schemas always match Pydantic models
3. **Type safety** - Output validated at construction
4. **Simpler code** - No separate producer modules
5. **Easier versioning** - Change `__schema_version__` and regenerate
