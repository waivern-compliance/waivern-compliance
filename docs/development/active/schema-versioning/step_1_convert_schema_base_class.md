# Step 1: Convert Schema Base Class to Concrete Implementation

**Phase:** 1 - Schema Infrastructure
**Dependencies:** None
**Estimated Scope:** Core abstraction change
**Status:** ✅ Completed

## Purpose

Convert the Schema abstract base class into a single concrete class that accepts `(name, version)` parameters. This is the foundation for multi-version schema support.

## Current State

`libs/waivern-core/src/waivern_core/schemas/base.py` contains:
- `Schema` as an abstract base class with abstract properties
- `BaseFindingSchema` as an abstract subclass
- Type-based equality (`type(self) == type(other)`)
- Instance-level loader per schema

## Target State

- `Schema` as a concrete class with `(name, version)` constructor
- Shared singleton `JsonSchemaLoader` for all Schema instances
- Lazy loading of JSON schema definitions
- Equality based on `(name, version)` tuple
- No abstract base class or subclasses

## Implementation Steps

1. **Update Schema class definition:**
   - Remove `@dataclass` decorator and ABC inheritance
   - Add `__init__(self, name: str, version: str)` constructor
   - Store name and version as instance attributes
   - Remove abstract property decorators

2. **Add shared singleton loader:**
   ```python
   class Schema:
       _loader: JsonSchemaLoader | None = None

       @classmethod
       def _get_loader(cls) -> JsonSchemaLoader:
           if cls._loader is None:
               cls._loader = JsonSchemaLoader(search_paths=cls._SEARCH_PATHS)
           return cls._loader
   ```

3. **Update equality and hashing:**
   - Change `__eq__` to compare `(name, version)` tuples instead of types
   - Change `__hash__` to hash `(name, version)` tuple instead of type

4. **Add lazy loading to schema property:**
   ```python
   @property
   def schema(self) -> dict[str, Any]:
       if self._schema_def is None:
           loader = self._get_loader()
           self._schema_def = loader.load(self._name, self._version)
           # Validate metadata matches parameters
       return self._schema_def
   ```

5. **Add fixed conventional search paths:**
   ```python
   _SEARCH_PATHS: list[Path] = [
       Path(__file__).parent / "json_schemas",
       # Additional paths can be added here
   ]
   ```

6. **Remove BaseFindingSchema class completely:**
   - It's no longer needed with generic Schema class
   - All finding schemas will be instantiated as `Schema("finding_name", "version")`

## Testing

Run the waivern-core test suite:
```bash
cd libs/waivern-core
uv run pytest tests/ -v
```

Expected: Tests will fail because schema instantiations need updating. This is expected and will be fixed in subsequent steps.

## Key Decisions

- **Shared singleton loader:** All Schema instances use the same loader for cache efficiency
- **Lazy loading:** JSON files only loaded when `schema` property accessed
- **Fixed search paths:** No configuration needed, schemas must be in conventional locations
- **No inheritance:** Single concrete class, no subclasses needed

## Files Modified

- `libs/waivern-core/src/waivern_core/schemas/base.py`

## Notes

- This step intentionally breaks existing code - that's expected
- Subsequent steps will fix all schema instantiations
- Keep the `JsonSchemaLoader` class unchanged (it's already working)
- The `SchemaLoader` protocol can stay for testing purposes
