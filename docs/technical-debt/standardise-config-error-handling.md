# Technical Debt: Standardise Configuration Error Handling

- **Status:** TODO
- **Priority:** LOW (Nice to have)
- **Impact Area:** Framework (waivern-core)
- **Effort:** Medium
- **Created:** 2025-11-12

## Context

Currently, every configuration class that extends `BaseComponentConfiguration` must override `from_properties()` to implement custom error handling that converts Pydantic `ValidationError` exceptions into the appropriate framework error type (`ConnectorConfigError`, `AnalyserConfigError`, etc.).

This creates code duplication across all configuration classes in the framework.

## Problem

**Current Pattern (Duplicated Across All Configs):**

Every config class repeats this boilerplate:

```python
@classmethod
def from_properties(cls, properties: dict[str, Any]) -> Self:
    try:
        return cls.model_validate(properties)
    except ValidationError as e:
        raise SomeConfigError(f"Invalid config: {e}") from e
    except ValueError as e:
        raise SomeConfigError(f"Invalid config: {e}") from e
```

**Issues:**
- Violates DRY (Don't Repeat Yourself) principle
- Every new config class must remember to implement error handling
- Inconsistent error messages across configs
- Framework-level pattern not enforced at framework level

**Examples of Duplication:**
- `SourceCodeConnectorConfig` → raises `ConnectorConfigError`
- `SourceCodeAnalyserConfig` → raises `AnalyserConfigError`
- `MySQLConnectorConfig` → raises `ConnectorConfigError`
- `PersonalDataAnalyserConfig` → inherits default (no custom handling)

## Solution

Add a template method pattern to `BaseComponentConfiguration` that allows subclasses to specify their error type without reimplementing the entire error handling logic.

**Proposed Approach:**

Add an abstract method to `BaseComponentConfiguration` that subclasses override to specify their error class:

```
function _get_config_error_class():
    # Subclasses override to return their error type
    # Example: return AnalyserConfigError

function from_properties(properties):
    try:
        return validate(properties)
    except ValidationError or ValueError as e:
        error_class = _get_config_error_class()
        raise error_class(f"Invalid {class_name}: {e}") from e
```

**Benefits:**
- Single source of truth for error handling logic
- Subclasses only specify error type (one line)
- Consistent error messages across framework
- Reduces boilerplate from ~10 lines to ~2 lines per config

## Design Decisions

1. **Template Method Pattern** - Use abstract method that subclasses override
2. **Default Error Type** - Use `WaivernError` as fallback if not overridden
3. **Error Message Format** - Standardise: `"Invalid {ConfigClassName}: {validation_error}"`
4. **Backward Compatibility** - Existing configs continue to work (can migrate gradually)
5. **Documentation** - Update base class docstring with usage example

## Implementation

### File to Modify

`libs/waivern-core/src/waivern_core/services/configuration.py`

### Changes Required

#### 1. Add abstract error class method

Add method to `BaseComponentConfiguration` that subclasses override:

```
@classmethod
def _get_config_error_class() -> type[Exception]:
    """Override in subclasses to specify configuration error type.

    Returns error class for validation failures.
    Default: WaivernError

    Example:
        class MyAnalyserConfig(BaseComponentConfiguration):
            @classmethod
            def _get_config_error_class():
                return AnalyserConfigError
    """
    return WaivernError  # Safe default
```

#### 2. Update from_properties implementation

Modify `from_properties()` to use the error class from subclass:

```
function from_properties(properties):
    try:
        return model_validate(properties)
    except (ValidationError, ValueError) as e:
        error_cls = _get_config_error_class()
        class_name = cls.__name__
        raise error_cls(f"Invalid {class_name}: {e}") from e
```

**Key Points:**
- Catch both `ValidationError` and `ValueError`
- Use `cls.__name__` for consistent messaging
- Preserve exception chaining with `from e`

#### 3. Update docstrings

Update `BaseComponentConfiguration` docstring to explain the pattern and show example usage.

## Testing

### Testing Strategy

Test at framework level (waivern-core) and verify configs can use the pattern.

### Test Scenarios

**File:** `libs/waivern-core/tests/waivern_core/services/test_configuration.py`

#### 1. Default error type with no override

**Setup:**
- Create test config class that doesn't override `_get_config_error_class()`
- Call `from_properties()` with invalid data

**Expected behaviour:**
- Raises `WaivernError` (default)
- Error message includes class name

#### 2. Custom error type with override

**Setup:**
- Create test config that overrides `_get_config_error_class()` returning `AnalyserConfigError`
- Call `from_properties()` with invalid data

**Expected behaviour:**
- Raises `AnalyserConfigError` (not WaivernError)
- Error message formatted correctly

#### 3. Valid configuration still works

**Setup:**
- Create test config with custom error type
- Call `from_properties()` with valid data

**Expected behaviour:**
- Returns config instance successfully
- No errors raised

#### 4. Error message format

**Setup:**
- Create config with validation error
- Trigger error

**Expected behaviour:**
- Message format: "Invalid ConfigClassName: {details}"
- Consistent across all configs

#### 5. Exception chaining preserved

**Setup:**
- Trigger validation error
- Inspect exception chain

**Expected behaviour:**
- Original `ValidationError` preserved in `__cause__`
- Exception chaining intact for debugging

## Migration Strategy

**This is an enhancement, not a breaking change:**

1. **Phase 1:** Add new pattern to `BaseComponentConfiguration`
2. **Phase 2:** Gradually migrate existing configs (optional)
3. **Phase 3:** Update documentation with recommended pattern

**Existing configs continue working:**
- If they override `from_properties()`: No change needed (works as before)
- If they don't override: Get default behaviour (WaivernError)

**New configs should:**
- Override `_get_config_error_class()` instead of `from_properties()`
- One-line implementation instead of 10+ lines

## Success Criteria

**Functional:**
- [ ] BaseComponentConfiguration has `_get_config_error_class()` method
- [ ] `from_properties()` uses error class from subclass
- [ ] Default error type is WaivernError
- [ ] Custom error types work when overridden
- [ ] Error messages formatted consistently

**Quality:**
- [ ] All framework tests pass
- [ ] No breaking changes to existing configs
- [ ] Type checking passes (strict mode)
- [ ] Documentation updated with examples

**Code Quality:**
- [ ] Template method pattern properly implemented
- [ ] Exception chaining preserved
- [ ] Consistent with framework patterns
- [ ] Clear docstrings with examples

## Implementation Notes

**Why template method pattern:**
- Allows customisation without full override
- Enforces consistent error handling
- Simple for subclasses to use

**Error message format:**
- Include class name for clarity
- Include underlying error details
- Consistent across framework

**Backward compatibility:**
- Existing overrides of `from_properties()` take precedence
- No forced migration needed
- Gradual adoption possible

## Related Issues

- None (this is a new enhancement identified during refactoring)

## Future Considerations

Could extend this pattern to other base classes if similar duplication exists elsewhere in framework.
