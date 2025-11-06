# Step 11: Implement Executor Version Matching

**Phase:** 4 - Executor Version Matching
**Dependencies:** Step 10 complete (Phase 3 done)
**Status:** ✅ COMPLETED
**Estimated Scope:** Core executor logic changes

## Purpose

Implement version negotiation in the WCT Executor so it can match compatible schema versions between connectors and analysers, and pass resolved schemas to components during execution.

## Files to Modify

1. **`apps/wct/src/wct/executor.py`** - Main implementation
2. **`apps/wct/src/wct/schemas/runbook.py`** - Add version fields to ExecutionStep

## Implementation

### 1. Update ExecutionStep Dataclass

In `apps/wct/src/wct/schemas/runbook.py`:

```python
@dataclass
class ExecutionStep:
    """Execution step configuration."""

    name: str
    connector: str
    analyser: str
    input_schema: str
    output_schema: str
    input_schema_version: str | None = None   # NEW - optional version pin
    output_schema_version: str | None = None  # NEW - optional version pin
```

### 2. Add Version Resolution Method

In `apps/wct/src/wct/executor.py`:

```python
def _resolve_step_schemas(
    self,
    step: ExecutionStep,
    connector: Connector,
    analyser: Analyser,
) -> tuple[Schema, Schema]:
    """Resolve input and output schemas with version matching.

    Args:
        step: Execution step with schema requirements
        connector: Connector instance
        analyser: Analyser instance

    Returns:
        Tuple of (input_schema, output_schema) to use

    Raises:
        SchemaNotFoundError: If schema not supported
        VersionMismatchError: If no compatible versions found
    """
    connector_outputs = connector.get_supported_output_schemas()
    analyser_inputs = analyser.get_supported_input_schemas()
    analyser_outputs = analyser.get_supported_output_schemas()

    # Resolve input schema (connector output → analyser input)
    input_schema = self._find_compatible_schema(
        schema_name=step.input_schema,
        requested_version=step.input_schema_version,
        producer_schemas=connector_outputs,
        consumer_schemas=analyser_inputs,
    )

    # Resolve output schema (analyser output)
    output_schema = self._find_compatible_schema(
        schema_name=step.output_schema,
        requested_version=step.output_schema_version,
        producer_schemas=analyser_outputs,
        consumer_schemas=[],  # No consumer for final output
    )

    return (input_schema, output_schema)
```

### 3. Add Compatible Schema Finder

```python
def _find_compatible_schema(
    self,
    schema_name: str,
    requested_version: str | None,
    producer_schemas: list[Schema],
    consumer_schemas: list[Schema],
) -> Schema:
    """Find compatible schema version between producer and consumer.

    Strategy:
    - If version explicitly requested: validate and use it
    - Otherwise: select latest version both support

    Args:
        schema_name: Name of schema to find
        requested_version: Optional specific version requested
        producer_schemas: Schemas the producer can output
        consumer_schemas: Schemas the consumer can accept (empty if no consumer)

    Returns:
        Compatible Schema object

    Raises:
        SchemaNotFoundError: If schema not supported by producer/consumer
        VersionMismatchError: If no compatible versions found
        VersionNotSupportedError: If requested version not compatible
    """
    # Filter by name
    producer_by_name = [s for s in producer_schemas if s.name == schema_name]
    consumer_by_name = [s for s in consumer_schemas if s.name == schema_name]

    # Validate schema is supported
    if not producer_by_name:
        raise SchemaNotFoundError(
            f"Producer does not support schema '{schema_name}'. "
            f"Available: {[s.name for s in producer_schemas]}"
        )

    if consumer_schemas and not consumer_by_name:
        raise SchemaNotFoundError(
            f"Consumer does not support schema '{schema_name}'. "
            f"Available: {[s.name for s in consumer_schemas]}"
        )

    # Find compatible versions (exact match)
    producer_versions = {s.version: s for s in producer_by_name}

    if consumer_schemas:
        consumer_versions = {s.version for s in consumer_by_name}
        compatible_versions = set(producer_versions.keys()) & consumer_versions
    else:
        # No consumer - all producer versions are compatible
        compatible_versions = set(producer_versions.keys())

    if not compatible_versions:
        raise VersionMismatchError(
            f"No compatible versions for schema '{schema_name}'. "
            f"Producer supports: {sorted(producer_versions.keys())}. "
            f"Consumer supports: {sorted(consumer_versions) if consumer_schemas else 'N/A'}"
        )

    # Select version
    if requested_version:
        # Explicit version requested
        if requested_version not in compatible_versions:
            raise VersionNotSupportedError(
                f"Requested version '{requested_version}' for schema '{schema_name}' "
                f"not compatible. Compatible versions: {sorted(compatible_versions)}"
            )
        return producer_versions[requested_version]
    else:
        # Auto-select latest compatible version
        latest_version = max(compatible_versions, key=self._version_sort_key)
        return producer_versions[latest_version]
```

### 4. Add Version Sorting Utility

```python
def _version_sort_key(self, version: str) -> tuple[int, int, int]:
    """Convert version string to sortable tuple.

    Args:
        version: Version string like "1.2.3"

    Returns:
        Tuple of (major, minor, patch) for sorting
    """
    try:
        parts = version.split(".")
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return (0, 0, 0)  # Invalid version sorts first
```

### 5. Update Execute Step Method

```python
def _execute_step(self, step: ExecutionStep) -> Message:
    """Execute a single step with version resolution.

    Args:
        step: Execution step configuration

    Returns:
        Analysis result message
    """
    connector = self._get_connector(step.connector)
    analyser = self._get_analyser(step.analyser)

    # Resolve schemas with version matching
    input_schema, output_schema = self._resolve_step_schemas(
        step, connector, analyser
    )

    logger.info(
        f"Resolved schemas: input={input_schema.name} v{input_schema.version}, "
        f"output={output_schema.name} v{output_schema.version}"
    )

    # Execute connector with explicit output schema
    connector_message = connector.extract(output_schema=input_schema)

    # Execute analyser with explicit input/output schemas
    result = analyser.process(
        input_schema=input_schema,
        output_schema=output_schema,
        message=connector_message,
    )

    return result
```

### 6. Add Custom Error Classes

Create `apps/wct/src/wct/errors.py` (if doesn't exist) or add to existing error file:

```python
class SchemaNotFoundError(Exception):
    """Raised when required schema is not supported by component."""
    pass


class VersionMismatchError(Exception):
    """Raised when no compatible schema versions found."""
    pass


class VersionNotSupportedError(Exception):
    """Raised when explicitly requested version is not compatible."""
    pass
```

## Testing

### Unit Tests

Create `apps/wct/tests/test_executor_version_matching.py`:

```python
def test_resolve_schemas_auto_selects_latest():
    """Test executor auto-selects latest compatible version."""
    # Setup connector with multiple versions
    # Setup analyser with multiple versions
    # Verify latest version selected

def test_resolve_schemas_respects_explicit_version():
    """Test executor uses explicit version when specified."""

def test_resolve_schemas_raises_on_no_compatible():
    """Test raises VersionMismatchError when no overlap."""

def test_version_sorting():
    """Test version sorting utility works correctly."""
    assert _version_sort_key("1.0.0") < _version_sort_key("1.1.0")
    assert _version_sort_key("1.1.0") < _version_sort_key("2.0.0")
```

### Integration Tests

Update `apps/wct/tests/integration/test_schema_integration.py`:

```python
def test_executor_multi_version_support():
    """Test executor can handle components with multiple schema versions."""
    # Create runbook with components supporting multiple versions
    # Verify correct version selected and execution succeeds
```

### Run Tests

```bash
cd apps/wct
./scripts/dev-checks.sh
```

## Key Decisions

**Version matching strategy:**
- Exact version matching only (no semver compatibility)
- Latest compatible version selected by default
- Explicit version request always honored if compatible

**Error messages:**
- List available versions when mismatch occurs
- Clear distinction between schema not found vs version mismatch
- Help users understand what went wrong

**Logging:**
- Log resolved versions for each step
- Helps with debugging version issues
- Users can see what versions were selected

## Files Modified

- `apps/wct/src/wct/runbook.py` - Added `input_schema_version` and `output_schema_version` fields to `ExecutionStep`
- `apps/wct/src/wct/executor.py` - Implemented version matching with 4 extracted helper methods
- `apps/wct/tests/test_executor_version_matching.py` - Added 5 comprehensive integration tests
- `apps/wct/tests/test_executor.py` - Updated 2 existing tests for new error messages

## Implementation Summary

**Version Matching Features:**
- ✅ Auto-selects latest compatible version when not specified
- ✅ Respects explicit version requests in runbook
- ✅ Validates schema existence (producer and consumer)
- ✅ Raises clear errors for version mismatches
- ✅ Semantic version sorting (1.10.0 > 1.2.0)

**Error Classes Added:**
- `SchemaNotFoundError` - Schema not supported by component
- `VersionMismatchError` - No compatible versions found
- `VersionNotSupportedError` - Requested version not available

**Refactoring Applied:**
- Extracted `_filter_schemas_by_name()` - eliminates duplication
- Extracted `_validate_schema_existence()` - SRP compliance
- Extracted `_find_compatible_versions()` - clear responsibility
- Extracted `_select_version()` - single purpose
- `_find_compatible_schema()` reduced from 76 lines to 22 lines
- Fixed silent error swallowing in `_version_sort_key()` - now raises ExecutorError
- Test file reduced by 334 lines (58% reduction) using base classes and Protocol

**Test Quality:**
- ✅ 5 integration tests through public API (`execute_runbook()`)
- ✅ Mock classes respect classmethod contract (no Liskov violations)
- ✅ `ComponentClassProtocol` for type safety (zero `type: ignore` comments)
- ✅ 905 tests passing, 0 type errors, 0 warnings

## Test Results

```bash
./scripts/dev-checks.sh
```

Results:
- ✅ **905 tests passed** (5 new version matching tests)
- ✅ **0 type errors, 0 warnings**
- ✅ All formatting, linting, and quality checks passed

## Notes

- ✅ **Phase 4 (Executor Version Matching) COMPLETE!**
- ✅ Core version matching logic fully implemented and tested
- ✅ Follows industry best practices (TDD, SOLID, no code smells)
- ✅ Production-ready: clean, tested, type-safe, well-documented
- 📋 **Next: End-to-end testing and documentation updates**

## Related Documentation

- **Step 10:** [Update PersonalDataAnalyser to Use Dynamic Loading](step_10_update_analyser_dynamic_loading.md) - Analyser-side implementation
- **Decision Doc:** [Schema Versioning with Pydantic Models](../schema-versioning-pydantic-models.md) - Overall architecture
