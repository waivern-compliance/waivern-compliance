# Regulatory Framework Architecture - Task Breakdown

## Overview

Breaking down the regulatory framework architecture design into atomic, manageable tasks with minimal dependencies. This document focuses on **foundation tasks only**.

Reference: [Regulatory Framework Architecture Design](../../future-plans/regulatory-framework-architecture.md)

---

## Task Dependency Graph

```
Independent (Layer 0):
  [T1] [T2] [T3] [T4]
    │
    ▼
  [T5]
    │
    ▼
  [T6]
```

---

## Layer 0: Independent Tasks (No Dependencies)

### T1: Add `framework` field to Runbook model

**Scope:** Add optional `framework` field to runbook schema

**Files:**

- `libs/waivern-orchestration/src/waivern_orchestration/models.py` - Add field to Runbook class
- Update runbook validation
- Add tests

**Acceptance:**

- Runbooks can declare `framework: "GDPR"` at root level
- Field is optional (backward compatible)
- Validation accepts known frameworks (GDPR, UK_GDPR, CCPA, etc.)

**Size:** Small

---

### T2: Create Classifier base class

**Scope:** Define Classifier as a new component type in waivern-core

**Files:**

- `libs/waivern-core/src/waivern_core/base_classifier.py` - New file
- `libs/waivern-core/src/waivern_core/__init__.py` - Export
- Add tests

**Acceptance:**

- `Classifier` base class extending Processor pattern
- Declares input requirements (finding schemas)
- Declares output schema (classified findings)
- Can be registered as processor type

**Size:** Medium

---

### T3: Add `ruleset` property to analyser configuration

**Scope:** Allow analysers to receive ruleset identifier via properties

**Files:**

- `libs/waivern-analysers-shared/src/waivern_analysers_shared/utilities/ruleset_manager.py` - Support ruleset URI
- Pattern matcher configs in each analyser

**Acceptance:**

- Analyser config can specify `ruleset: "firm-a/gdpr-personal-data:2.1.0"`
- Falls back to default bundled ruleset if not specified
- URI scheme support: local path, package reference

**Size:** Medium

---

### T4: Update `export-architecture.md` documentation

**Scope:** Update design doc to reflect new architecture decisions

**Files:**

- `docs/future-plans/export-architecture.md`

**Acceptance:**

- Remove references to `get_compliance_frameworks()` discovery
- Document exporter selection via `runbook.framework`
- Mark affected sections as "superseded by regulatory-framework-architecture.md"

**Size:** Small

---

## Layer 1: Depends on Layer 0

### T5: Update exporter selection to use `runbook.framework`

**Scope:** Change CLI exporter auto-detection from component inference to runbook declaration

**Depends on:** T1

**Files:**

- `apps/wct/src/wct/cli.py` - Update `_detect_exporter()` function

**Acceptance:**

- If `runbook.framework` is set, use corresponding exporter
- If not set, fall back to JSON exporter
- Deprecation warning if using old inference (temporary)

**Size:** Small

---

### T6: Remove `get_compliance_frameworks()` from component contract

**Scope:** Remove the method from base classes and all usages

**Depends on:** T5

**Files:**

- `libs/waivern-core/src/waivern_core/base_analyser.py` - Remove method
- `libs/waivern-core/src/waivern_core/base_connector.py` - Remove method
- `libs/waivern-core/tests/waivern_core/test_base_analyser.py` - Remove tests
- `libs/waivern-core/tests/waivern_core/test_base_connector.py` - Remove tests
- `apps/wct/src/wct/cli.py` - Remove inference logic entirely

**Acceptance:**

- Method no longer exists on Analyser or Connector
- All tests pass
- CLI uses runbook.framework exclusively

**Size:** Small

---

## Execution Order

**Phase 1 (Parallel - no dependencies):**

- T1: Add `framework` to Runbook
- T2: Create Classifier base class
- T3: Add `ruleset` property support
- T4: Update export-architecture.md

**Phase 2 (Sequential - after T1):**

- T5: Update exporter selection → T6: Remove `get_compliance_frameworks()`

---

## Summary

| Task | Description                              | Dependencies | Size   |
| ---- | ---------------------------------------- | ------------ | ------ |
| T1   | Add `framework` to Runbook               | None         | Small  |
| T2   | Create Classifier base class             | None         | Medium |
| T3   | Add `ruleset` property support           | None         | Medium |
| T4   | Update export-architecture.md            | None         | Small  |
| T5   | Update exporter selection                | T1           | Small  |
| T6   | Remove `get_compliance_frameworks()`     | T5           | Small  |

**Independent tasks:** 4
**Dependent tasks:** 2

---

## Notes

- **Schemas:** New schemas will be created as needed when implementing specific classifiers, rather than designing a generic schema upfront.
- **Future work:** Classifier implementations (GDPRClassifier, etc.) and analyser refactoring are out of scope for this task list.
