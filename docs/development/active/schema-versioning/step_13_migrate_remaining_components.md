# Step 13: Migrate Remaining Components to Reader/Producer Pattern

**Phase:** 6 - Component Rollout
**Dependencies:** Step 12 complete (Phase 5 done)
**Estimated Scope:** Multiple component migrations
**Status:** 🔄 IN PROGRESS (1/7 complete)

## Purpose

Migrate all remaining connectors and analysers to use the reader/producer pattern with auto-discovery. Follow the pattern established with PersonalDataAnalyser.

## Migration Status

### Analysers (0/2 complete)
1. **ProcessingPurposeAnalyser** - in waivern-community ⏳ PENDING
2. **DataSubjectAnalyser** - in waivern-community ⏳ PENDING

### Connectors (1/5 complete)
3. **FilesystemConnector** - in waivern-community ✅ COMPLETE
4. **SQLiteConnector** - in waivern-community ⏳ PENDING
5. **MySQLConnector** - in waivern-mysql (standalone) ⏳ PENDING
6. **SourceCodeConnector** - in waivern-community ⏳ PENDING
7. **DatabaseConnector** (base class) - in waivern-community ⏳ PENDING

## Components to Migrate

### Analysers (2 remaining)
1. **ProcessingPurposeAnalyser** - in waivern-community
2. **DataSubjectAnalyser** - in waivern-community

### Connectors (5 total)
3. ~~**FilesystemConnector** - in waivern-community~~ ✅ COMPLETE
4. **SQLiteConnector** - in waivern-community
5. **MySQLConnector** - in waivern-mysql (standalone)
6. **SourceCodeConnector** - in waivern-community
7. **DatabaseConnector** (base class) - in waivern-community

## Migration Pattern (For Each Component)

Follow this pattern for each component:

### Step 1: Create Directory Structure

```bash
cd libs/{package}/src/{package_path}/{component_dir}
mkdir -p schema_readers   # For analysers
mkdir -p schema_producers  # For both
```

### Step 2: Create Reader/Producer Modules

For each schema version currently supported:

**Readers** (analysers only):
```python
# schema_readers/{schema_name}_{major}_{minor}_{patch}.py
def read(content: dict) -> dict:
    """Transform schema to internal format."""
    return {
        # Extract relevant fields
    }
```

**Producers** (connectors and analysers):
```python
# schema_producers/{schema_name}_{major}_{minor}_{patch}.py
def produce(internal_result: dict) -> dict:
    """Transform internal format to schema."""
    return {
        # Format according to schema
    }
```

### Step 3: Update Component Class

```python
class MyComponent(Connector):  # or Analyser
    # Remove hardcoded schema lists
    # Remove get_supported_*_schemas() overrides (use inherited auto-discovery)

    # Add module caches
    _reader_cache: dict[str, Any] = {}  # If analyser
    _producer_cache: dict[str, Any] = {}

    # Add dynamic loading methods
    def _load_reader(self, schema: Schema):
        """Dynamically import reader module."""
        cache_key = f"{schema.name}_{schema.version.replace('.', '_')}"
        if cache_key not in self._reader_cache:
            self._reader_cache[cache_key] = importlib.import_module(
                f".schema_readers.{cache_key}", package=__package__
            )
        return self._reader_cache[cache_key]

    def _load_producer(self, schema: Schema):
        """Dynamically import producer module."""
        cache_key = f"{schema.name}_{schema.version.replace('.', '_')}"
        if cache_key not in self._producer_cache:
            self._producer_cache[cache_key] = importlib.import_module(
                f".schema_producers.{cache_key}", package=__package__
            )
        return self._producer_cache[cache_key]

    # Update extract() or process() to use dynamic loading
    def extract(self, output_schema: Schema) -> Message:
        # ... extraction logic ...
        producer = self._load_producer(output_schema)
        output_content = producer.produce(internal_result)
        return Message(schema=output_schema, content=output_content)
```

### Step 4: Write Tests

Create tests for readers and producers:
```bash
tests/{component_path}/schema_readers/test_{schema_name}_{version}.py
tests/{component_path}/schema_producers/test_{schema_name}_{version}.py
```

### Step 5: Verify Auto-Discovery

Test that schemas are auto-discovered:
```python
def test_auto_discovery():
    component = MyComponent(...)
    schemas = component.get_supported_output_schemas()
    assert Schema("schema_name", "1.0.0") in schemas
```

### Step 6: Run Component Tests

```bash
cd libs/{package}
./scripts/dev-checks.sh
```

## Component-Specific Notes

### ProcessingPurposeAnalyser
- **Input schemas:** standard_input, source_code
- **Output schemas:** processing_purpose_finding
- Has multi-input handling - may need special reader logic
- Has LLM validation - keep in core analyser logic

### DataSubjectAnalyser
- **Input schemas:** standard_input
- **Output schemas:** data_subject_finding
- Simpler than ProcessingPurpose - good candidate to do early

### FilesystemConnector
- **Output schemas:** standard_input
- Simple connector - straightforward migration
- Good early candidate

### SQLiteConnector
- **Output schemas:** standard_input
- Uses DatabaseConnector base class
- May need to coordinate with DatabaseConnector migration

### MySQLConnector
- **Output schemas:** standard_input
- Standalone package
- Coordinate with waivern-connectors-database

### SourceCodeConnector
- **Output schemas:** source_code
- More complex extraction logic
- Keep complexity in core connector, simple transform in producer

### DatabaseConnector (Base Class)
- May have shared schema handling logic
- Consider extracting to shared utilities if needed
- Or keep base class override-able for now

## Migration Order Recommendation

Suggested order (easiest to hardest):

1. **FilesystemConnector** - Simple, single schema
2. **DataSubjectAnalyser** - Simple analyser, single input
3. **SQLiteConnector** - Similar to Filesystem
4. **MySQLConnector** - Similar to SQLite
5. **ProcessingPurposeAnalyser** - Multi-input, more complex
6. **SourceCodeConnector** - Complex extraction logic
7. **DatabaseConnector** - Base class, may need refactoring

## Testing Strategy

For each component:
1. Migrate one component at a time
2. Run that component's tests
3. Run full workspace tests
4. Fix any issues before moving to next component

After all migrations:
```bash
./scripts/dev-checks.sh  # Full workspace
```

## Expected Results

After all components migrated:
- ✅ All components use reader/producer pattern
- ✅ All components use auto-discovery
- ✅ No hardcoded schema version lists remain
- ✅ All 845+ tests pass
- ✅ Zero type errors across workspace

## Key Decisions

**Incremental migration:**
- One component at a time
- Test thoroughly before moving to next
- Can pause/resume migration as needed

**Shared utilities:**
- If database connectors share logic, consider shared utils
- Don't over-engineer - keep it simple
- Can refactor later if duplication becomes issue

**Base class handling:**
- Base classes can keep overrideable methods
- Concrete components use auto-discovery
- Migration doesn't require base class changes (already done in Phase 2)

## Notes

- This is the final phase!
- Take time with each component - don't rush
- After this, schema versioning system is fully deployed
- Components can now easily add version support by adding files
