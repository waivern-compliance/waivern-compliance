# Unified Connector Architecture - Implementation Plan

**Date:** 2025-11-13
**Status:** Planning

---

## High-Level Plan: Unified Connector Architecture

### Phase 1: Design & Core Abstraction
1. **Design ArtifactConnector** - New connector type that retrieves data from previous step outputs (stored in executor's artifact store)
2. **Update Connector interface (if needed)** - Ensure base abstraction supports artifact retrieval semantics
3. **Design runbook format changes** - Every step now has a connector (explicit, no optional connector field)

### Phase 2: Implementation
4. **Implement ArtifactConnector** - Create new connector package/class that reads from artifact storage
5. **Refactor Executor** - Remove conditional branching (lines 330-371), unified flow: always instantiate connector → analyser
6. **Simplify helper methods** - Remove `Connector | None` optional types from `_get_step_configs()`, `_validate_step_types()`, `_instantiate_components()`
7. **Simplify schema resolution** - Single `_resolve_schemas()` method (merge `_resolve_step_schemas()` and `_resolve_pipeline_schemas()`)

### Phase 3: Update Runbooks & Tests
8. **Update 3 sample runbooks** - Convert to unified connector format (replace `input_from` with artifact connector)
9. **Update test suite** - Adapt existing tests to new format, add ArtifactConnector tests
10. **Run full quality checks** - `./scripts/dev-checks.sh` to ensure everything passes

**Breaking Changes:** Runbook format (connector field becomes required, `input_from` removed)
**Estimated Scope:** ~400 LOC refactor + 3 sample runbooks
