# Task: Create SourceCodeAnalyserFactory

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** TODO
- **Prerequisites:** Step 8 (SourceCodeAnalyser created)
- **GitHub Issue:** #214

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser. The previous steps created the config and analyser class.

**See:** the parent implementation plan for full context.

## Purpose

Create factory for SourceCodeAnalyser following the ComponentFactory pattern used throughout WCF, enabling automatic registration and discovery by the executor.

## Problem

WCF uses a component factory pattern for dependency injection:
- Executor discovers components via entry points
- Factories instantiate components with validated configuration
- Metaclass handles automatic registration

Without a factory, the analyser cannot be discovered or used by WCT.

## Solution

Create `SourceCodeAnalyserFactory` implementing `ComponentFactory[Analyser]`:
- Validate configuration via SourceCodeAnalyserConfig
- Instantiate SourceCodeAnalyser
- Register automatically via metaclass
- Follow existing factory patterns

## Decisions Made

1. **ComponentFactory pattern** - Use existing framework infrastructure
2. **Config validation** - Use SourceCodeAnalyserConfig.from_properties()
3. **Automatic registration** - Metaclass handles registry
4. **Type safety** - Generic type hint ComponentFactory[Analyser]
5. **Entry point** - Register in pyproject.toml under waivern.analysers

## Implementation

### File to Create

`libs/waivern-source-code/src/waivern_source_code/analyser_factory.py`

### Factory Structure

**Pattern to follow:**
```
Look at PersonalDataAnalyserFactory or DataSubjectAnalyserFactory
for reference implementation
```

**Key methods:**

#### 1. get_component_type()

Return the type name for lookup ("source_code_analyser").

#### 2. create()

Create SourceCodeAnalyser instance from properties dict.

**Algorithm (pseudo-code):**
```
function create(properties):
    # Validate configuration
    config = SourceCodeAnalyserConfig.from_properties(properties)

    # Create analyser instance
    analyser = SourceCodeAnalyser(config)

    log("Created SourceCodeAnalyser")

    return analyser
```

**Error handling:**
- Configuration errors propagate as ConnectorConfigError
- Let validation errors bubble up to executor

## Testing

### Testing Strategy

Test through **public API** via executor integration. Factory is tested indirectly through analyser usage.

Unit tests for factory focus on configuration handling only.

### Test Scenarios

**File:** `libs/waivern-source-code/tests/test_analyser_factory.py`

#### 1. Valid configuration

**Setup:**
- Call factory.create({"language": "php", "max_file_size": 5242880})

**Expected behaviour:**
- Returns SourceCodeAnalyser instance
- Config fields correctly set

#### 2. Empty configuration (all defaults)

**Setup:**
- Call factory.create({})

**Expected behaviour:**
- Returns SourceCodeAnalyser instance
- Config uses defaults (language=None, max_file_size=10MB)

#### 3. Invalid configuration

**Setup:**
- Call factory.create({"max_file_size": -1})

**Expected behaviour:**
- Raises ConnectorConfigError
- Error message mentions validation issue

#### 4. get_component_type returns correct name

**Setup:**
- Call factory.get_component_type()

**Expected behaviour:**
- Returns "source_code_analyser"

#### 5. Factory registered in component registry

**Setup:**
- Import factory module
- Query component registry

**Expected behaviour:**
- Factory discoverable by type name
- Automatic metaclass registration worked

## Success Criteria

**Functional:**
- [ ] SourceCodeAnalyserFactory implements ComponentFactory[Analyser]
- [ ] get_component_type() returns "source_code_analyser"
- [ ] create() validates configuration via SourceCodeAnalyserConfig
- [ ] create() returns SourceCodeAnalyser instance
- [ ] Invalid configuration raises ConnectorConfigError

**Quality:**
- [ ] All tests pass
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] Factory follows existing patterns

**Code Quality:**
- [ ] Tests verify factory behaviour, not internal implementation
- [ ] Error handling consistent with other factories
- [ ] Logging follows project standards
- [ ] Minimal code (factory should be simple)

## Implementation Notes

**Design considerations:**
- Factory is simple glue code
- Configuration validation handled by config class
- Component creation is straightforward
- Registry handles discovery automatically

**Pattern consistency:**
- Match PersonalDataAnalyserFactory structure
- Same error handling approach
- Same logging approach
- Same type annotations

**Integration points:**
- Entry point in pyproject.toml: `[project.entry-points."waivern.analysers"]`
- Registry via metaclass (automatic)
- Executor discovery via entry points
