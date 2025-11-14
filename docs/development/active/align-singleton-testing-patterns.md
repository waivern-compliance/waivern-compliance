# Implementation Plan: Align RulesetRegistry with SchemaRegistry Testing Pattern

## Objective
Eliminate singleton testing tech debt by aligning RulesetRegistry with SchemaRegistry's industry-standard snapshot/restore pattern.

## Approach
Follow TDD principles: Add new methods → Update fixture → Verify tests pass → Clean up boilerplate

## Implementation Steps

### Phase 1: Add Snapshot/Restore Methods (Core Change)
**File:** `libs/waivern-rulesets/src/waivern_rulesets/base.py`

**Changes:**
- Add `snapshot_state()` classmethod to capture registry state
- Add `restore_state(state)` classmethod to restore from snapshot
- Keep existing `clear()` method for backward compatibility

**Risk:** Low - purely additive, no breaking changes

---

### Phase 2: Update Package-Level Test Fixture
**File:** `libs/waivern-rulesets/tests/conftest.py`

**Changes:**
- Simplify `isolated_registry` fixture to use snapshot/restore
- Remove manual state capture (accessing `_registry`, `_type_mapping`)
- Keep fixture non-autouse initially (safer transition)

**Risk:** Low - tests still explicitly request fixture

---

### Phase 3: Verify Test Isolation (Validation)
**Action:** Run full test suite for waivern-rulesets package

**Command:**
```bash
uv run pytest libs/waivern-rulesets/tests/ -v
```

**Expected:** All tests pass with new fixture implementation

**Risk:** Low - if tests fail, revert fixture changes

---

### Phase 4: Add Workspace-Level Autouse Fixture (Optional)
**File:** `conftest.py` (workspace root)

**Changes:**
- Add autouse fixture for automatic RulesetRegistry isolation
- Similar pattern to existing `isolate_schema_registry` fixture

**Risk:** Medium - affects all tests workspace-wide
**Mitigation:** Can skip this step if desired, keep package-level only

---

### Phase 5: Clean Up Test Boilerplate (8 test files)
**Files to modify:**
- `test_base.py`
- `test_data_collection.py`
- `test_data_subject.py`
- `test_personal_data.py`
- `test_processing_purposes.py`
- `test_service_integrations.py`
- `test_types.py`

**Changes:**
- Remove manual `isolated_registry.clear()` calls
- Tests become cleaner (fixture handles isolation)

**Risk:** Low - if autouse fixture not added, keep fixture usage but remove clear()

---

### Phase 6: Full Regression Testing
**Action:** Run complete workspace test suite

**Command:**
```bash
./scripts/dev-checks.sh
```

**Expected:** All 933+ tests pass

---

## Testing Strategy

**After each phase:**
1. Run package tests: `uv run pytest libs/waivern-rulesets/tests/ -v`
2. Verify all tests pass
3. If failures occur, analyse and fix or revert

**Final validation:**
- Run full workspace tests
- Ensure no test pollution or flaky tests
- Verify parallel execution works correctly

---

## Rollback Strategy

**If issues arise:**
- Phase 1-2: Revert fixture changes, keep old implementation
- Phase 4: Remove autouse fixture, rely on package-level only
- Phase 5: Keep manual clear() calls if needed

**Changes are incremental** - can stop at any phase and still have improvement

---

## Success Criteria

✅ RulesetRegistry has snapshot_state() and restore_state() methods
✅ Test fixture uses public API (no private attribute access)
✅ All package tests pass with new implementation
✅ Consistent pattern with SchemaRegistry
✅ Less test boilerplate (fewer/no clear() calls)

---

## Dependencies
None - this is a self-contained change to waivern-rulesets package

---

## Notes
- Keep `clear()` method for backward compatibility
- Can stop after Phase 3 and still have significant improvement
- Phase 4 (autouse) is optional but recommended for full consistency
- Phase 5 cleanup can be done gradually across multiple commits
