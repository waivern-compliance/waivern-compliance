# Unified Connector Architecture - Implementation Plan

**Date:** 2025-11-13
**Status:** Planning
**Prerequisites:** ArtifactStore Service (#227) - COMPLETED

---

## High-Level Plan: Unified Connector Architecture

### Connector Format Decision

**Chosen Approach: Named References (Minimal Breaking Change)**

This implementation uses named connector references with a top-level `connectors:` section. Future work will explore DAG-style orchestration with inline configuration (Terraform-style) - placeholder Epic already exists.

**This iteration:**
- Keep top-level `connectors:` section with named connector instances
- Make `connector` field required in ExecutionStep (remove Optional)
- Remove `input_from` field entirely
- Add `artifact` connector type for pipeline steps

**Example format:**
```yaml
connectors:
  - name: "mysql_source"
    type: "mysql"
    properties: {...}
  - name: "previous_step"
    type: "artifact"
    properties:
      step_id: "extract"

execution:
  - id: "extract"
    connector: "mysql_source"
    save_output: true
  - id: "classify"
    connector: "previous_step"  # Now required, no more input_from
```

### Phase 1: Design & Core Abstraction
1. **Design ArtifactConnector** - New connector type that retrieves data from previous step outputs (stored in Executor's artifact store)
2. **Schema resolution strategy** - ArtifactConnector must peek at artifact to expose output schema before extraction
3. **Design runbook format changes** - Every step now has a connector (required field, no optional connector)

### Phase 2: Implementation
4. **Implement ArtifactConnector** - Create new connector package/class that reads from artifact storage with schema caching
5. **Refactor Executor** - Remove conditional branching (lines 359-382), unified flow: always instantiate connector → analyser
6. **Simplify helper methods** - Remove `Connector | None` optional types from `_get_step_configs()`, `_validate_step_types()`, `_instantiate_components()`
7. **Simplify schema resolution** - Single `_resolve_schemas()` method (merge `_resolve_step_schemas()` and `_resolve_pipeline_schemas()`)

### Phase 3: Update Runbooks & Tests
8. **Update 2 sample runbooks** - Convert to unified connector format (replace `input_from` with artifact connector references)
9. **Update test suite** - Adapt existing tests to new format, add ArtifactConnector tests
10. **Run full quality checks** - `./scripts/dev-checks.sh` to ensure everything passes

**Breaking Changes:** Runbook format (connector field becomes required, `input_from` removed)
**Estimated Scope:** ~450 LOC refactor + 2 sample runbooks + test updates
