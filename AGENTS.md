# Agent Guidelines for Waivern Compliance Framework

## Essential Commands

**Full quality check (run before completing tasks):**
```bash
./scripts/dev-checks.sh
```

**Individual checks:**
```bash
./scripts/lint.sh && ./scripts/format.sh && ./scripts/type-check.sh
```

**Testing:**
```bash
# All tests
uv run pytest

# Single test
uv run pytest path/to/test_file.py::test_function

# With verbose output
uv run pytest -v

# Integration tests (requires API keys)
uv run pytest -m integration

# Batch API tests (requires API keys, may take several minutes)
uv run pytest -m batch
```

## Code Style

**Type system:**
- Type annotations required (basedpyright strict mode)
- Use `@override` decorator for abstract method overrides
- Python 3.12+: Use PEP 695 generics `def func[T](...)` syntax

**Formatting & linting:**
- Ruff formatter (py312 target)
- British English spelling
- Import order: stdlib → third-party → local `waivern_*` packages

**Component architecture:**
- ComponentFactory pattern for instantiation with dependency injection
- Configuration via Pydantic models
- Schema files: `schemas/json_schemas/{name}/{version}/{name}.json`
- Tests: Contract testing pattern for base classes (inherit from `AnalyserContractTests`, `ComponentFactoryContractTests`)

**Error handling:**
- Use custom error types from `waivern_core.errors`
- Specific exception types for different failure modes (ConfigError, ExtractionError, ProcessingError, etc.)

**Docstrings:** Required for public methods/classes; Google-style or similar

**Testing:** Tests use `--import-mode=importlib`; integration tests marked with `@pytest.mark.integration`, batch API tests with `@pytest.mark.batch` (both excluded by default)

**Monorepo:** UV workspace with libs/ and apps/; each package owns its configuration
