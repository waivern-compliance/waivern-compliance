# Multi-Provider LLM Support - Incremental TDD Implementation

## Overview

This document outlines the plan for adding multi-provider LLM support to WCT, broken down into small, independently mergeable features that can be implemented using TDD methodology.

## Background

### Current State
- Using `langchain>=0.3.0` and `langchain-anthropic>=0.2.0` ✅
- Direct `ChatAnthropic` instantiation in `AnthropicLLMService`
- Factory pattern already in place with `LLMServiceFactory`
- Lifecycle management through `LLMServiceManager`
- Environment variables: `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`

### Goals
1. Support multiple LLM providers (OpenAI, Google, Cohere)
2. Per-analyser LLM configuration for cost/performance optimization
3. Enable parallel execution with different providers
4. Maintain backward compatibility
5. Minimal dependency bloat (optional dependency groups)

## Architecture Decisions

### Per-Analyser Configuration (Option B - Recommended)
- Each analyser can optionally specify provider/model in runbook
- Falls back to global configuration if not specified
- Enables task-specific optimization and true parallel execution

### Configuration Hierarchy (3-tier)
1. **Per-analyser config in runbook** (highest priority)
2. **Global environment variables** (fallback)
3. **Provider defaults** (final fallback)

### Dependency Management (Option D - Recommended)
- Optional dependency groups in `pyproject.toml`
- Lazy imports with helpful error messages
- Minimal default installation (core + Anthropic only)
- Users install what they need: `uv sync --group llm-openai`

## Implementation Plan

### Feature 1: Base LLM Service Abstraction
**Goal:** Extract interface, make current code inherit from it
**Testing:** All existing tests pass unchanged
**Mergeable:** ✅ Zero behaviour change, pure refactoring

**Changes:**
- Create `BaseLLMService` ABC with `analyse_data()` method
- Refactor `AnthropicLLMService` to inherit from base
- Update `LLMServiceManager` type hint to `BaseLLMService | None`
- Run existing tests to verify no regression

**Test Strategy:**
- Existing `test_llm_service.py` tests pass unchanged
- Add test verifying `AnthropicLLMService` is instance of `BaseLLMService`

**Estimated effort:** 1-2 hours

---

### Feature 2: OpenAI Provider with Lazy Import
**Goal:** Add single alternative provider, prove the pattern works
**Testing:** Unit tests for OpenAI service with mocks
**Mergeable:** ✅ Additive only, doesn't affect existing code

**Changes:**
- Add `llm-openai = ["langchain-openai>=0.2.0"]` to dependency groups
- Implement `OpenAILLMService` with lazy import + helpful error
- Add `LLMServiceFactory.create_openai_service()` method
- Document OpenAI setup in `.env.example`

**Test Strategy:**
- Test `OpenAILLMService` with mocked `ChatOpenAI`
- Test lazy import error message (without langchain-openai installed)
- Test factory creates correct service type
- All existing tests still pass (Anthropic unchanged)

**Estimated effort:** 2-3 hours

---

### Feature 3: Environment-Based Provider Selection
**Goal:** Global provider switching via `LLM_PROVIDER` env var
**Testing:** Test provider selection logic with env var mocking
**Mergeable:** ✅ Opt-in via new env var, backward compatible

**Changes:**
- Add `LLM_PROVIDER` env var support to `.env.example`
- Implement `LLMServiceFactory.create_service()` with provider detection
- Support env vars: `OPENAI_API_KEY`, `OPENAI_MODEL`
- Update `LLMServiceManager` to use new factory method

**Test Strategy:**
- Test provider selection with different `LLM_PROVIDER` values
- Test fallback to Anthropic when `LLM_PROVIDER` not set
- Test error when provider specified but API key missing
- Integration test: Run sample analyser with OpenAI config

**Estimated effort:** 2-3 hours

---

### Feature 4: Add Google & Cohere Providers
**Goal:** Expand provider options, validate pattern scales
**Testing:** Unit tests for each provider
**Mergeable:** ✅ Additive, follows established pattern

**Changes:**
- Add dependency groups: `llm-google`, `llm-cohere`, `llm-all`
- Implement `GoogleLLMService` and `CohereLLMService`
- Add factory methods for both providers
- Update factory's `create_service()` to support all providers
- Document in `.env.example`

**Test Strategy:**
- Test each service with mocked LangChain clients
- Test lazy import errors for each
- Test provider selection includes new options
- Verify existing providers still work

**Estimated effort:** 2-3 hours

---

### Feature 5: Per-Analyser LLM Configuration (Schema)
**Goal:** Add config fields without changing behaviour
**Testing:** Config validation and parsing tests
**Mergeable:** ✅ New optional fields, backward compatible

**Changes:**
- Extend `LLMValidationConfig` in analyser types with optional fields:
  - `llm_provider: str | None = None`
  - `llm_model: str | None = None`
- Update JSON schemas for analysers
- Update sample runbook with commented examples

**Test Strategy:**
- Test config parsing with new fields present
- Test config parsing without new fields (backward compat)
- Test validation rejects invalid provider names
- Existing analyser tests pass unchanged

**Estimated effort:** 1-2 hours

---

### Feature 6: Configuration Hierarchy Resolution
**Goal:** Implement 3-tier config resolution logic
**Testing:** Test all resolution paths
**Mergeable:** ✅ Wired up but doesn't change behaviour unless new fields used

**Changes:**
- Update `LLMServiceManager.__init__()` to accept config parameters
- Implement resolution: analyser config → env vars → defaults
- Update analysers to pass config to manager
- Add logging for selected provider/model

**Test Strategy:**
- Test resolution with only analyser config
- Test resolution with only env vars
- Test resolution with both (analyser wins)
- Test resolution with neither (defaults)
- Integration test with each resolution path

**Estimated effort:** 2-3 hours

---

### Feature 7: Test-LLM CLI Command
**Goal:** Provide diagnostic tool for users
**Testing:** CLI command tests with mocked services
**Mergeable:** ✅ New command, doesn't affect existing

**Changes:**
- Add `test-llm` command to `src/wct/__main__.py`
- Implement `test_llm_command()` in `src/wct/cli.py`
- Test provider detection and connectivity
- Show helpful diagnostics and configuration info

**Test Strategy:**
- Test command with valid configuration
- Test command with missing API key
- Test command with invalid provider
- Test command shows detected provider/model
- Manual verification: `uv run wct test-llm`

**Estimated effort:** 2-3 hours

---

### Feature 8: Multi-Provider Example Runbook
**Goal:** Document real-world usage pattern
**Testing:** Run example end-to-end
**Mergeable:** ✅ Documentation/example only

**Changes:**
- Create `runbooks/samples/multi_provider_example.yaml`
- Demonstrate mixed providers (e.g., Claude + OpenAI)
- Add comprehensive comments explaining optimization
- Update `runbooks/README.md` with explanation

**Test Strategy:**
- Manually run with Anthropic only (fallback works)
- Manually run with per-analyser config (resolution works)
- Add integration test running multi-provider runbook
- Verify parallel execution benefits

**Estimated effort:** 1-2 hours

---

### Feature 9: Documentation & Migration Guide
**Goal:** Complete user-facing documentation
**Testing:** Documentation review
**Mergeable:** ✅ Docs only

**Changes:**
- Update `CLAUDE.md` with multi-provider setup
- Add provider comparison table (use cases, costs)
- Document configuration hierarchy
- Add troubleshooting section
- Update `.env.example` with all providers

**Test Strategy:**
- Review docs for accuracy
- Test all example commands
- Verify installation instructions

**Estimated effort:** 1-2 hours

---

## Merge Strategy for Each Feature

1. **Write failing tests** (TDD red phase)
2. **Implement minimum code** to pass tests (green phase)
3. **Refactor** for clarity (refactor phase)
4. **Run full test suite**: `uv run pytest`
5. **Run dev checks**: `./scripts/dev-checks.sh`
6. **Commit with conventional commit message**
7. **Merge to main** (or PR if required)

## Key Benefits of This Approach

- ✅ Each feature ~1-3 hours of work
- ✅ Always shippable after each merge
- ✅ Tests written before implementation (true TDD)
- ✅ Can pause between features without broken state
- ✅ Easy to review (small, focused changes)
- ✅ Immediate value (can use OpenAI after Feature 3)
- ✅ Low risk (backward compatible at every step)

## Example Configurations

### Global Provider Selection
```bash
# .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
```

### Per-Analyser Configuration
```yaml
analysers:
  - name: "personal_data_analyser"
    type: "personal_data_analyser"
    properties:
      llm_validation:
        enable_llm_validation: true
        llm_provider: "anthropic"  # High accuracy for PII
        llm_model: "claude-opus-4-20250514"

  - name: "processing_purpose_analyser"
    type: "processing_purpose_analyser"
    properties:
      llm_validation:
        enable_llm_validation: true
        llm_provider: "openai"  # Cheaper for categorization
        llm_model: "gpt-3.5-turbo"
```

### Dependency Installation
```bash
# Minimal (Anthropic only)
uv sync

# Add OpenAI support
uv sync --group llm-openai

# Add all LLM providers
uv sync --group llm-all

# Future connector dependencies
uv sync --group connector-postgres
```

## Backward Compatibility Guarantees

- Existing `ANTHROPIC_API_KEY` configs continue working unchanged
- Analysers without per-analyser config use global settings
- Default provider remains Anthropic
- All existing tests pass
- No breaking changes to runbook format

## Future Extensibility

- Pattern scales to connectors (postgres, mongodb, etc.)
- Easy to add new LLM providers
- Per-analyser config enables advanced optimizations
- Foundation for provider-specific features (streaming, function calling)
