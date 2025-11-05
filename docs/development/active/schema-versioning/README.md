# Schema Versioning Implementation - Work Units

This directory contains atomic work units for implementing the schema versioning system in WCF.

## Overview

- **Design Document:** [../schema-versioning-design.md](../schema-versioning-design.md)
- **Execution Plan:** [../schema-versioning-execution-plan.md](../schema-versioning-execution-plan.md)

## Work Unit Structure

Each step is an atomic unit of work that can be completed independently by a developer or Claude Code session.

## Implementation Steps

### Phase 1: Schema Infrastructure

Core schema class refactoring - converts abstract schema hierarchy to single generic class.

- **[Step 1](step_1_convert_schema_base_class.md)** - Convert Schema base class to concrete implementation
- **[Step 2](step_2_update_waivern_core_instantiations.md)** - Update schema instantiations in waivern-core
- **[Step 3](step_3_update_personal_data_analyser.md)** - Update schema instantiations in waivern-personal-data-analyser
- **[Step 4](step_4_update_waivern_community.md)** - Update schema instantiations in waivern-community
- **[Step 5](step_5_update_remaining_packages.md)** - Update schema instantiations in remaining packages

**Phase 1 Completion:** All code uses `Schema(name, version)` pattern, no schema subclasses remain.

---

### Phase 2: Base Class Auto-Discovery

Add file-based version discovery to base classes.

- **[Step 6](step_6_add_connector_auto_discovery.md)** - Add auto-discovery to Connector base class
- **[Step 7](step_7_add_analyser_auto_discovery.md)** - Add auto-discovery to Analyser base class

**Phase 2 Completion:** Base classes scan `schema_readers/` and `schema_producers/` directories for version support.

---

### Phase 3: Proof of Concept Component

Establish the reader/producer pattern with PersonalDataAnalyser.

- **[Step 8](step_8_create_personal_data_analyser_structure.md)** - Create directory structure for PersonalDataAnalyser
- **[Step 9](step_9_extract_schema_logic_to_modules.md)** - Extract schema version logic to reader/producer modules
- **[Step 10](step_10_update_analyser_dynamic_loading.md)** - Update PersonalDataAnalyser to use dynamic loading

**Phase 3 Completion:** PersonalDataAnalyser demonstrates full reader/producer pattern with auto-discovery.

---

### Phase 4: Executor Version Matching

Enable version negotiation in WCT Executor.

- **[Step 11](step_11_implement_executor_version_matching.md)** - Implement executor version matching

**Phase 4 Completion:** Executor can match compatible schema versions and pass resolved schemas to components.

---

### Phase 5: Runbook Format Updates

Support version specification in runbooks.

- **[Step 12](step_12_update_runbook_format.md)** - Update runbook format and validation

**Phase 5 Completion:** Runbooks can optionally specify schema versions, with validation and documentation.

---

### Phase 6: Component Rollout

Migrate all remaining components to reader/producer pattern.

- **[Step 13](step_13_migrate_remaining_components.md)** - Migrate remaining components (7 components total)

**Phase 6 Completion:** All components use reader/producer pattern with auto-discovery.

---

## Quick Reference

### Dependencies

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5
                                    ↓
                              Step 6 + Step 7
                                    ↓
                            Step 8 → Step 9 → Step 10
                                           ↓
                                       Step 11
                                           ↓
                                       Step 12
                                           ↓
                                       Step 13
```

### Parallelisation Opportunities

- Steps 2-5 can potentially be done in parallel (different packages)
- Steps 6-7 can be done in parallel (different base classes)
- Step 13 components can be migrated in parallel (7 components)

### Testing Strategy

- Run package tests after each step
- Run full workspace tests after each phase
- Each step should leave codebase in testable state

### Rollback Strategy

- Phase 1: Revert single commit (atomic refactor)
- Phase 2+: Each step can be rolled back individually
- No breaking changes for components until they migrate

## Implementation Progress

Track completion status:

- [ ] Phase 1: Schema Infrastructure (Steps 1-5)
- [ ] Phase 2: Base Class Auto-Discovery (Steps 6-7)
- [ ] Phase 3: Proof of Concept (Steps 8-10)
- [ ] Phase 4: Executor Version Matching (Step 11)
- [ ] Phase 5: Runbook Format (Step 12)
- [ ] Phase 6: Component Rollout (Step 13)

## Success Criteria

System is complete when:
- ✅ All 13 steps completed
- ✅ All 845+ tests pass
- ✅ Zero type errors across workspace
- ✅ All components use auto-discovery
- ✅ Runbooks support version specification
- ✅ Documentation updated

## Getting Started

1. Read the [design document](../schema-versioning-design.md)
2. Review the [execution plan](../schema-versioning-execution-plan.md)
3. Start with [Step 1](step_1_convert_schema_base_class.md)
4. Follow dependencies and test after each step
