# Schema Versioning Design

**Status:** Draft - Under Discussion
**Created:** 2025-11-04
**Last Updated:** 2025-11-04 (Added shared singleton loader for efficient caching)

## Key Simplification

**No individual schema type classes needed.** Schema metadata (name, version) lives in JSON files. A single generic `Schema` class instantiates from name and version parameters.

## Overview

This document outlines the design for multi-version schema support in the Waivern Compliance Framework (WCF). The design enables components (connectors and analysers) to support multiple schema versions through a file-based auto-discovery system.

## Problem Statement

Currently, WCF components are hardcoded to support a single version of each schema:

```python
class PersonalDataAnalyser:
    _SUPPORTED_INPUT_SCHEMAS = [StandardInputSchema()]  # Only v1.0.0
    _SUPPORTED_OUTPUT_SCHEMAS = [PersonalDataFindingSchema()]  # Only v1.0.0
```

**Challenges:**

1. **No multi-version support**: Components can only work with one version at a time
2. **Manual maintenance burden**: Adding schema version support requires updating hardcoded lists
3. **No version negotiation**: Executor cannot match compatible versions between components
4. **Unclear deprecation path**: No mechanism to deprecate old versions

## Design Goals

1. **Minimal maintenance**: Adding/removing version support should not require updating version lists
2. **Auto-discovery**: Components declare support by file presence, not code
3. **Clear separation**: Version-specific logic isolated in separate files
4. **Backward compatible execution**: Existing runbooks continue to work
5. **Explicit versioning**: No defaults - all schema instances must specify version
6. **Simple matching**: Exact version matching (no complex semver compatibility rules)

## Core Design Principles

### Principle 1: Single Generic Schema Class

**No individual schema type classes.** Schema metadata lives in JSON files, not Python classes.

```python
# Single Schema class - instantiate with name and version
schema = Schema("standard_input", "1.0.0")

# JSON file contains metadata
{
  "name": "standard_input",
  "version": "1.0.0",
  "$schema": "http://json-schema.org/draft-07/schema#",
  "properties": { ... }
}
```

**Benefits:**
- No `StandardInputSchema`, `PersonalDataFindingSchema` classes needed
- No schema registry needed
- JSON is single source of truth for schema metadata
- Easy to support any schema without code changes

### Principle 2: File-Based Version Declaration

Components declare version support through file presence in standard directories:

```
personal_data_analyser/
  analyser.py
  schema_readers/
    standard_input_1_0_0.py      # Supports reading v1.0.0
    standard_input_1_1_0.py      # Supports reading v1.1.0
  schema_producers/
    personal_data_finding_1_0_0.py  # Supports producing v1.0.0
```

**Key insight:** Add file = add version support, delete file = remove version support.

### Principle 3: Auto-Discovery via Base Classes

Base classes (`BaseAnalyser`, `BaseConnector`) implement auto-discovery by:
1. Scanning the component's `schema_readers/` or `schema_producers/` directories
2. Parsing filenames to extract schema name and version
3. Instantiating appropriate `Schema` objects
4. Returning them from `get_supported_*_schemas()` methods

**Result:** Components inherit version discovery - zero boilerplate code needed.

### Principle 4: Reader/Producer Pattern

Each version file exports simple functions:

```python
# schema_readers/standard_input_1_0_0.py
def read(content: dict) -> dict:
    """Transform standard_input schema v1.0.0 to internal format"""
    return {
        "source": content["source"],
        "content": content["content"],
    }

# schema_producers/personal_data_finding_1_0_0.py
def produce(internal_result: dict) -> dict:
    """Transform internal result to personal_data_finding schema v1.0.0"""
    return {
        "field_name": internal_result["field_name"],
        "data_category": internal_result["data_category"],
        # ... etc
    }
```

**Benefits:**
- Each version's logic is isolated and testable
- Easy to add new versions (copy and modify)
- Easy to remove old versions (delete file)
- Clear which versions differ in implementation

## Architecture

### 1. Single Generic Schema Class

```python
class Schema:
    """Generic schema class - no subclasses needed.

    Schema objects are lightweight descriptors. JSON schema files are loaded
    lazily only when actually needed (e.g., during Message validation).

    Schema loading uses fixed conventional search paths. All schemas must be
    placed in one of these conventional locations.
    """

    # Fixed conventional search paths - schemas must be in one of these locations
    _SEARCH_PATHS: list[Path] = [
        Path(__file__).parent / "json_schemas",  # waivern-core/schemas/json_schemas/
        # Additional conventional paths can be added here as framework grows
    ]

    # Shared singleton loader for caching across all Schema instances
    _loader: JsonSchemaLoader | None = None

    @classmethod
    def _get_loader(cls) -> JsonSchemaLoader:
        """Get or create the shared singleton loader."""
        if cls._loader is None:
            cls._loader = JsonSchemaLoader(search_paths=cls._SEARCH_PATHS)
        return cls._loader

    def __init__(self, name: str, version: str):
        """Initialise schema descriptor (does not load JSON file).

        Args:
            name: Schema name (e.g., "standard_input")
            version: Schema version (e.g., "1.0.0")
        """
        self._name = name
        self._version = version
        self._schema_def: dict[str, Any] | None = None  # Lazy - loaded on demand

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def schema(self) -> dict[str, Any]:
        """Get JSON schema definition, loading from file if needed.

        Raises:
            SchemaLoadError: If schema file cannot be loaded or validation fails
            FileNotFoundError: If schema JSON file doesn't exist
        """
        if self._schema_def is None:
            # Lazy load using shared singleton loader (for cache efficiency)
            loader = self._get_loader()
            self._schema_def = loader.load(self._name, self._version)

            # Validate JSON metadata matches parameters
            if self._schema_def.get("name") != self._name:
                raise SchemaLoadError(
                    f"Schema name mismatch: expected '{self._name}', "
                    f"found '{self._schema_def.get('name')}'"
                )
            if self._schema_def.get("version") != self._version:
                raise SchemaLoadError(
                    f"Schema version mismatch: expected '{self._version}', "
                    f"found '{self._schema_def.get('version')}'"
                )

        return self._schema_def

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Schema):
            return False
        return self.name == other.name and self.version == other.version

    def __hash__(self) -> int:
        return hash((self.name, self.version))

    def __repr__(self) -> str:
        return f"Schema(name='{self.name}', version='{self.version}')"
```

**Key design features:**
- No abstract base class or subclasses - single concrete class
- **Fixed conventional paths**: `_SEARCH_PATHS` defines where schemas must be located
- **No configuration needed**: All schemas must be in conventional locations
- **Shared singleton loader**: All Schema instances use the same `JsonSchemaLoader` for efficient caching
- **Lazy loading**: JSON schema file loaded only when `schema` property is accessed
- **Efficient caching**: Loaded schemas cached in shared loader, reused across all Schema instances
- Validates JSON metadata matches parameters (during lazy load)
- Equality based on (name, version) tuple (no need to load JSON for comparison)
- No schema registry needed
- Fast discovery: creating Schema objects during auto-discovery doesn't trigger file I/O

### 2. Directory Conventions

**Hard conventions for component structure:**
- `schema_readers/` - Input schema version handlers (analysers only)
- `schema_producers/` - Output schema version handlers (both connectors and analysers)

**File naming convention:**
- Format: `{schema_name}_{major}_{minor}_{patch}.py`
- Example: `standard_input_1_0_0.py` → `Schema("standard_input", "1.0.0")`

**No configuration or override mechanism** - these are fixed conventions. Components that need different logic can override the entire `get_supported_*_schemas()` method.

### 3. Base Class Auto-Discovery

**Base classes implement auto-discovery directly:**

```python
class BaseAnalyser(ABC):
    @classmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Auto-discover from schema_readers/ directory (convention)."""
        component_dir = Path(inspect.getfile(cls)).parent
        schema_dir = component_dir / "schema_readers"
        schemas = []

        if schema_dir.exists():
            for file in schema_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                # Parse filename: "standard_input_1_0_0.py"
                parts = file.stem.rsplit("_", 3)
                if len(parts) == 4:
                    name = parts[0]
                    version = f"{parts[1]}.{parts[2]}.{parts[3]}"
                    # Create lightweight Schema descriptor (no file I/O)
                    schemas.append(Schema(name, version))

        return schemas

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Auto-discover from schema_producers/ directory (convention)."""
        component_dir = Path(inspect.getfile(cls)).parent
        schema_dir = component_dir / "schema_producers"
        schemas = []

        if schema_dir.exists():
            for file in schema_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                parts = file.stem.rsplit("_", 3)
                if len(parts) == 4:
                    name = parts[0]
                    version = f"{parts[1]}.{parts[2]}.{parts[3]}"
                    try:
                        schemas.append(Schema(name, version))
                    except SchemaLoadError:
                        pass

        return schemas

    @abstractmethod
    def process_data(self, message: Message, output_schema: Schema | None = None) -> Message:
        """Process input message and return output message.

        Args:
            message: Input message with content and schema
            output_schema: Optional specific output schema version to produce.
                          If None, component chooses which version to output.

        Returns:
            Message with output content and schema
        """
        pass

class BaseConnector(ABC):
    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Auto-discover from schema_producers/ directory (convention)."""
        component_dir = Path(inspect.getfile(cls)).parent
        schema_dir = component_dir / "schema_producers"
        schemas = []

        if schema_dir.exists():
            for file in schema_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                parts = file.stem.rsplit("_", 3)
                if len(parts) == 4:
                    name = parts[0]
                    version = f"{parts[1]}.{parts[2]}.{parts[3]}"
                    try:
                        schemas.append(Schema(name, version))
                    except SchemaLoadError:
                        pass

        return schemas

    @abstractmethod
    def extract(self, output_schema: Schema | None = None) -> Message:
        """Extract data and return as Message.

        Args:
            output_schema: Optional specific output schema version to produce.
                          If None, component chooses which version to output.

        Returns:
            Message with extracted content and schema
        """
        pass
```

**Key points:**
- Discovery logic embedded directly in base classes
- Hard-coded directory names: `schema_readers/` and `schema_producers/`
- Components inherit this behaviour automatically
- Components can override methods if they need custom logic

### 4. Component Implementation Pattern

```python
class PersonalDataAnalyser(BaseAnalyser):
    # No version lists - auto-discovered!
    # Module caches for performance
    _reader_cache: dict[str, Any] = {}
    _producer_cache: dict[str, Any] = {}

    def process_data(self, message: Message, output_schema: Schema | None = None) -> Message:
        # Load appropriate reader for input version (from message.schema)
        reader = self._load_reader(message.schema)
        internal_data = reader.read(message.content)

        # Perform version-agnostic analysis
        internal_result = self._analyze(internal_data)

        # Determine output schema version
        if output_schema is None:
            # Use latest supported version as default
            supported = self.get_supported_output_schemas()
            output_schema = max(supported, key=lambda s: (s.name, s.version))

        # Load appropriate producer for output version
        producer = self._load_producer(output_schema)
        output_content = producer.produce(internal_result)

        return Message(
            id=self._generate_message_id(),
            content=output_content,
            schema=output_schema
        )

    def _load_reader(self, schema: Schema):
        """Dynamically import reader module with caching"""
        cache_key = f"{schema.name}_{schema.version}"

        if cache_key not in self._reader_cache:
            module_name = cache_key.replace('.', '_')
            self._reader_cache[cache_key] = importlib.import_module(
                f".schema_readers.{module_name}",
                package=__package__
            )

        return self._reader_cache[cache_key]

    def _load_producer(self, schema: Schema):
        """Dynamically import producer module with caching"""
        cache_key = f"{schema.name}_{schema.version}"

        if cache_key not in self._producer_cache:
            module_name = cache_key.replace('.', '_')
            self._producer_cache[cache_key] = importlib.import_module(
                f".schema_producers.{module_name}",
                package=__package__
            )

        return self._producer_cache[cache_key]
```

### 5. Executor Version Matching and Execution

```python
def _execute_step(self, step: ExecutionStep) -> Message:
    """Execute a single step with version resolution."""
    connector = self._get_connector(step.connector)
    analyser = self._get_analyser(step.analyser)

    # Resolve schemas
    input_schema, output_schema = self._resolve_step_schemas(step, connector, analyser)

    # Execute connector with explicit schema version to produce
    connector_message = connector.extract(output_schema=input_schema)

    # Execute analyser with explicit output schema
    result = analyser.process_data(connector_message, output_schema=output_schema)

    return result

def _resolve_step_schemas(
    self,
    step: ExecutionStep,
    connector: Connector,
    analyser: Analyser
) -> tuple[Schema, Schema]:
    """Resolve schemas with version matching."""

    connector_outputs = connector.get_supported_output_schemas()
    analyser_inputs = analyser.get_supported_input_schemas()
    analyser_outputs = analyser.get_supported_output_schemas()

    # Find compatible input schema
    input_schema = self._find_compatible_schema(
        schema_name=step.input_schema,
        requested_version=step.input_schema_version,
        producer_schemas=connector_outputs,
        consumer_schemas=analyser_inputs
    )

    # Find compatible output schema
    output_schema = self._find_compatible_schema(
        schema_name=step.output_schema,
        requested_version=step.output_schema_version,
        producer_schemas=analyser_outputs,
        consumer_schemas=[]
    )

    return (input_schema, output_schema)

def _find_compatible_schema(
    self,
    schema_name: str,
    requested_version: str | None,
    producer_schemas: list[Schema],
    consumer_schemas: list[Schema]
) -> Schema:
    """
    Find compatible schema version.

    Strategy:
    - If version explicitly requested: validate and use it
    - Otherwise: select latest version both support
    """

    # Filter by name
    producer_by_name = [s for s in producer_schemas if s.name == schema_name]
    consumer_by_name = [s for s in consumer_schemas if s.name == schema_name]

    # Validate support
    if not producer_by_name:
        raise SchemaNotFoundError(f"Producer doesn't support '{schema_name}'")
    if consumer_schemas and not consumer_by_name:
        raise SchemaNotFoundError(f"Consumer doesn't support '{schema_name}'")

    # Find compatible versions (exact match)
    producer_versions = {s.version: s for s in producer_by_name}
    if consumer_schemas:
        consumer_versions = {s.version for s in consumer_by_name}
        compatible_versions = set(producer_versions.keys()) & consumer_versions
    else:
        compatible_versions = set(producer_versions.keys())

    if not compatible_versions:
        raise VersionMismatchError(...)

    # Select version
    if requested_version:
        if requested_version not in compatible_versions:
            raise VersionNotSupportedError(...)
        return producer_versions[requested_version]
    else:
        # Select latest
        latest_version = max(compatible_versions, key=version_sort_key)
        return producer_versions[latest_version]
```

## File Naming Convention

**Format:** `{schema_name}_{major}_{minor}_{patch}.py`

**Examples:**
- `standard_input_1_0_0.py` → `Schema("standard_input", "1.0.0")`
- `personal_data_finding_1_1_0.py` → `Schema("personal_data_finding", "1.1.0")`
- `processing_purpose_finding_2_0_0.py` → `Schema("processing_purpose_finding", "2.0.0")`

**Rules:**
- Underscores separate version components
- Version must be semantic (major.minor.patch)
- Files starting with `_` are ignored (e.g., `__init__.py`)

## Runbook Updates

### Extended Execution Step

```python
@dataclass
class ExecutionStep:
    name: str
    connector: str
    analyser: str
    input_schema: str
    output_schema: str
    input_schema_version: str | None = None   # Optional version pinning
    output_schema_version: str | None = None  # Optional version pinning
```

### Example Runbook

```yaml
name: "Multi-version analysis"
description: "Demonstrates version selection"

connectors:
  - name: "mysql_connector"
    type: "mysql"

analysers:
  - name: "personal_data_analyser"
    type: "personal_data_analyser"

execution:
  - name: "Auto-select versions"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
    # Executor will select latest compatible versions

  - name: "Pin to specific versions"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    input_schema_version: "1.0.0"        # Pin to v1.0.0
    output_schema: "personal_data_finding"
    output_schema_version: "1.0.0"       # Pin to v1.0.0
```

## Practical Workflows

### Adding Support for New Schema Version

**Scenario:** `standard_input` schema v1.1.0 is released with new optional field `metadata`

**Steps:**
1. Create `schema_readers/standard_input_1_1_0.py`
2. Implement `read()` function to handle new field
3. Done - auto-discovered, no code changes to analyser class

**File content:**
```python
"""Reader for standard_input schema version 1.1.0"""

def read(content: dict) -> dict:
    """Transform standard_input v1.1.0 to internal format"""
    return {
        "source": content["source"],
        "content": content["content"],
        "metadata": content.get("metadata", {}),  # New field in v1.1.0
    }
```

### Deprecating a Schema Version

**Scenario:** Deprecate `standard_input` schema v1.0.0 (warn users, but still support it)

**Steps:**
1. Add deprecation metadata to JSON schema file:
   ```json
   {
     "name": "standard_input",
     "version": "1.0.0",
     "deprecated": true,
     "deprecation_message": "Please upgrade to version 1.1.0 or higher",
     "deprecation_date": "2025-06-01",
     "sunset_date": "2026-01-01",
     ...
   }
   ```
2. Executor/validator reads this metadata and warns users
3. Keep `schema_readers/standard_input_1_0_0.py` - still supported but deprecated

**Where warnings appear:**
- `wct validate-runbook` - warns if runbook uses deprecated versions
- `wct run` - logs warning at startup
- Component error messages - suggest non-deprecated versions

### Removing Support for Old Version

**Scenario:** Completely remove support for `standard_input` schema v1.0.0 (after sunset date)

**Steps:**
1. Delete `schema_readers/standard_input_1_0_0.py`
2. Done - automatically no longer advertised as supported
3. Users get clear error: "Component does not support standard_input v1.0.0. Supported versions: [1.1.0, 1.2.0]"

### Adding Support for New Output Schema Version

**Scenario:** Add support for producing `personal_data_finding` schema v1.2.0

**Steps:**
1. Create `schema_producers/personal_data_finding_1_2_0.py`
2. Implement `produce()` function
3. Done - auto-discovered

### Updating to Use New Schema Fields

**Scenario:** Want to start using new fields from v1.1.0

**Steps:**
1. Update internal analyser logic to populate new fields
2. Update reader to extract new fields
3. Update producer to output new fields
4. All version files remain independent

## Error Handling

### Schema Not Found

```
Error: Producer does not support schema 'standard_input'
Available schemas: ['personal_data_finding']
```

### Version Mismatch

```
Error: No compatible versions for schema 'standard_input'
Producer supports: ['1.0.0', '1.1.0']
Consumer supports: ['1.2.0', '1.3.0']
```

### Requested Version Not Supported

```
Error: Requested version '1.5.0' for schema 'standard_input' not compatible
Compatible versions: ['1.0.0', '1.1.0', '1.2.0']
```

## Implementation Phases

### Phase 1: Schema Infrastructure
- Replace all concrete schema classes with single generic `Schema` class
- Update `Schema` to accept `(name, version)` parameters only
- Implement lazy loading in `schema` property (JSON loaded on first access, not in __init__)
- Add class-level `_SEARCH_PATHS` constant with fixed conventional paths
- Ensure all JSON schema files contain `name` and `version` fields
- Ensure all JSON schema files are in conventional locations
- Fix all schema instantiations throughout codebase

### Phase 2: Base Class Auto-Discovery
- Update `BaseAnalyser.get_supported_input_schemas()` with auto-discovery
- Update `BaseAnalyser.get_supported_output_schemas()` with auto-discovery
- Update `BaseConnector.get_supported_output_schemas()` with auto-discovery
- Update `BaseConnector.extract()` signature to accept optional `output_schema` parameter
- Update `BaseAnalyser.process_data()` signature to accept optional `output_schema` parameter

### Phase 3: Component Refactoring
- Refactor `PersonalDataAnalyser` as proof of concept
- Create reader/producer files for existing versions
- Update component to use dynamic loading with module caching
- Add `_reader_cache` and `_producer_cache` class attributes

### Phase 4: Executor Version Matching
- Implement `_execute_step()` to pass schemas to components
- Implement `_resolve_step_schemas()` for version negotiation
- Implement `_find_compatible_schema()` logic with exact version matching
- Add version sorting utility (`version_sort_key()`)
- Add custom error classes (`SchemaNotFoundError`, `VersionMismatchError`, `VersionNotSupportedError`)

### Phase 5: Runbook Format Updates
- Add version fields to `ExecutionStep`
- Update runbook validation
- Document version specification

### Phase 6: Rollout
- Refactor remaining analysers
- Refactor all connectors
- Update all tests
- Write documentation

## Open Questions

1. **Schema name parsing**: How do we parse schema name from filename?
   - **Solution**: Use `rsplit("_", 3)` - splits from the right, taking last 3 parts as version (major, minor, patch)
   - Everything before the last 3 parts is the schema name
   - Examples:
     - `standard_input_1_0_0.py` → name: `standard_input`, version: `1.0.0`
     - `standard_input_extended_1_0_0.py` → name: `standard_input_extended`, version: `1.0.0`
     - `my_custom_schema_2_1_3.py` → name: `my_custom_schema`, version: `2.1.3`

2. **Dynamic import caching**: Components must cache imported reader/producer modules
   - **Implementation**: Add module cache dict at class level
   - Cache key: `f"{schema.name}_{schema.version}"`
   - Check cache before importing, store after first import

3. **Reader/producer interface**: Should we enforce a protocol/interface for reader/producer modules?
   - **Decision: No enforcement needed** - these are private implementation details within components
   - Modules are only accessed by the component that owns them
   - Components can structure their reader/producer modules however they want
   - Suggested convention: export `read()` and `produce()` functions for consistency

4. **Deprecation warnings**: Where should deprecation metadata live?
   - **Decision: In schema JSON files** (single source of truth, see Practical Workflows section)

4. **Schema loading and validation**: When are JSON schema files loaded and validated?
   - **Decision: Lazy loading on first use**
   - Schema objects are lightweight descriptors created during auto-discovery (just name + version)
   - JSON files are NOT loaded during `get_supported_*_schemas()` (performance)
   - JSON files loaded only when `Message.validate()` accesses the `schema` property
   - If JSON file doesn't exist or is invalid → error at validation time, not discovery time
   - This means components can advertise schemas that don't exist, but will fail cleanly when actually used

5. **Schema search paths**: How does `Schema` find JSON files?
   - **Decision: Fixed conventional paths only**
   - Schema class has `_SEARCH_PATHS` constant with fixed conventional locations
   - All schemas must be placed in one of these conventional locations
   - No configuration or override mechanism - keeps implementation simple
   - Additional conventional paths can be added to `_SEARCH_PATHS` as framework grows

## References

- Remote Analyser Protocol: `/docs/architecture/remote-analyser-protocol.md`
- WCF Core Components: `/docs/core-concepts/wcf-core-components.md`
- Building Custom Components: `/docs/development/building-custom-components.md`
