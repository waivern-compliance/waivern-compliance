# Component Extraction Work Units

This directory contains atomic work units for extracting all remaining components from waivern-community into standalone packages and completing the monorepo migration.

---

## Overview

**Goal:** Extract remaining analysers from waivern-community as standalone packages, then remove waivern-community completely.

**Current State:** 10 packages (core + 9 extracted components)
**Target State:** 12 standalone packages (no waivern-community)

**Components remaining in waivern-community:**
- DataSubjectAnalyser (743 LOC + 716 test LOC)
- ProcessingPurposeAnalyser (1,231 LOC + 3,081 test LOC)
- Processing Purpose Prompts (196 LOC, used by ProcessingPurposeAnalyser)
- Database connector utilities (124 LOC - duplicates of waivern-connectors-database, to be removed)
- TCF vendor database reference data (decision needed)

**Note:** waivern-mysql and waivern-personal-data-analyser were extracted in separate efforts prior to this plan.

---

## Execution Order

### Phase 1: Independent Connectors ✅ COMPLETE

| Step | Component | Complexity | Dependencies | Status |
|------|-----------|------------|--------------|--------|
| [Step 1](./step_1_extract_waivern_filesystem.md) | waivern-filesystem | 🟢 Low | None | ✅ Complete |
| [Step 2](./step_2_extract_waivern_sqlite.md) | waivern-sqlite | 🟢 Low | waivern-connectors-database | ✅ Complete |

### Phase 2: Source Code Connector ✅ COMPLETE

| Step | Component | Complexity | Dependencies | Status |
|------|-----------|------------|--------------|--------|
| [Step 3](./step_3_extract_waivern_source_code.md) | waivern-source-code | 🟡 Medium | Step 1 (filesystem) | ✅ Complete |

### Phase 3: Independent Analyser ⏳ IN PROGRESS

| Step | Component | Complexity | Dependencies | Status |
|------|-----------|------------|--------------|--------|
| [Step 4](./step_4_extract_waivern_data_subject_analyser.md) | waivern-data-subject-analyser | 🟡 Medium | Shared packages only | ❌ Pending |

### Phase 4: Processing Purpose Analyser

| Step | Component | Complexity | Dependencies | Status |
|------|-----------|------------|--------------|--------|
| [Step 5](./step_5_extract_waivern_processing_purpose_analyser.md) | waivern-processing-purpose-analyser | 🟠 High | Step 3 (source-code) | ❌ Pending |

### Phase 5: Remove waivern-community

| Step | Action | Complexity | Dependencies | Status |
|------|--------|------------|--------------|--------|
| [Step 6](./step_6_update_wct_imports.md) | Update WCT imports | 🟡 Medium | Steps 1-5 complete | ❌ Pending |
| [Step 7](./step_7_remove_waivern_community.md) | Remove waivern-community | 🟢 Low | Step 6 complete | ❌ Pending |

---

## Work Units

### [Step 1: Extract waivern-filesystem](./step_1_extract_waivern_filesystem.md) ✅
- **Phase:** 1 - Independent Connectors
- **Status:** ✅ Complete (Commit: 7eab880)
- **Complexity:** 🟢 Low
- **Size:** ~604 LOC, 6 tests
- **Dependencies:** waivern-core only
- **Blocking:** Step 3 (source-code needs this)

### [Step 2: Extract waivern-sqlite](./step_2_extract_waivern_sqlite.md) ✅
- **Phase:** 1 - Independent Connectors
- **Status:** ✅ Complete (Commit documented in step file)
- **Complexity:** 🟢 Low
- **Size:** ~560 LOC, 6 tests
- **Dependencies:** waivern-core, waivern-connectors-database
- **Blocking:** None

### [Step 3: Extract waivern-source-code](./step_3_extract_waivern_source_code.md) ✅
- **Phase:** 2 - Source Code Connector
- **Status:** ✅ Complete (Commit: df14915)
- **Complexity:** 🟡 Medium
- **Size:** ~1,658 LOC, 7 tests
- **Dependencies:** Step 1 (filesystem)
- **Blocking:** Step 5 (processing-purpose needs this)
- **Special:** Has custom schema, optional tree-sitter dependencies

### [Step 4: Extract waivern-data-subject-analyser](./step_4_extract_waivern_data_subject_analyser.md)
- **Phase:** 3 - Independent Analyser
- **Status:** ❌ Pending
- **Complexity:** 🟡 Medium
- **Size:** 743 LOC source + 716 LOC tests (6 test files)
- **Dependencies:** Shared packages only
- **Blocking:** None
- **Special:** Has custom schema, uses data_subjects ruleset

### [Step 5: Extract waivern-processing-purpose-analyser](./step_5_extract_waivern_processing_purpose_analyser.md)
- **Phase:** 4 - Processing Purpose Analyser
- **Status:** ❌ Pending
- **Complexity:** 🟠 High
- **Size:** 1,231 LOC source + 3,081 LOC tests (14 test files) + 196 LOC prompts
- **Dependencies:** Step 3 (source-code)
- **Blocking:** None
- **Special:** Has custom schema, prompts migration, multi-schema support, integration tests

### [Step 6: Update WCT Imports](./step_6_update_wct_imports.md)
- **Phase:** 5 - Remove waivern-community
- **Complexity:** 🟡 Medium
- **Dependencies:** Steps 1-5 complete
- **Blocking:** Step 7
- **Special:** Automated sed script provided for import updates

### [Step 7: Remove waivern-community](./step_7_remove_waivern_community.md)
- **Phase:** 5 - Remove waivern-community
- **Complexity:** 🟢 Low
- **Dependencies:** Step 6 complete
- **Blocking:** None (final step)
- **Special:** Marks completion of monorepo migration

### Cleanup Tasks (Part of Step 7)

**Files to remove (duplicates/leftovers):**
- `connectors/database/` - 124 LOC duplicates of waivern-connectors-database (3 files + 4 test files)
- `tests/connectors/filesystem/` - empty directory
- `tests/connectors/sqlite/` - empty directory
- `tests/rulesets/` - empty directory

**TCF Vendor Database (decision needed):**
- `analysers/data_export_analyser/vendor-database/` - 1.1MB SQLite DB + 789KB JSON + scripts
- Options: Keep as reference data, move to docs, move to separate package, or remove

---

## Parallel Execution Strategy

### Option A: Sequential (Safest)
Execute steps 1-7 in strict order. Recommended for first-time execution.

### Option B: Parallel Phase 1 (Faster)
1. Run Steps 1 & 2 in parallel (independent)
2. Run Step 3 after Step 1 completes
3. Run Step 4 in parallel with Step 3
4. Run Step 5 after Step 3 completes
5. Run Step 6 after all extractions complete
6. Run Step 7 after Step 6 completes

### Option C: Maximum Parallelism (Fastest, Requires Coordination)
- **Session A:** Steps 1 → 3 → 5
- **Session B:** Steps 2 → 4
- **Session C:** Step 6 (waits for A & B) → Step 7

---

## Each Step File Contains

✅ **Purpose** - What this step achieves
✅ **Context** - Background and dependencies
✅ **Component Variables** - Specific values for template substitution
✅ **Implementation Steps** - Detailed instructions
✅ **Testing Procedures** - How to verify success
✅ **Success Criteria** - Checklist for completion
✅ **Decisions Made** - Key choices and rationale
✅ **Notes** - Important considerations

---

## Common Patterns

### All Extraction Steps (1-5)
1. Create package structure
2. Copy scripts from waivern-core
3. Create pyproject.toml
4. Create README.md
5. Copy component code
6. Update imports
7. Create package exports (with schema registration if needed)
8. Move tests
9. Add to workspace
10. Install and test
11. Run quality checks
12. Update waivern-community
13. Delete extracted code
14. Run full workspace checks

### All Steps Must
- Run `./scripts/dev-checks.sh` and ensure all checks pass
- Commit changes with conventional commit message
- Verify integration tests pass

---

## Prerequisites

Before starting:
- [x] All shared packages already extracted:
  - ✅ waivern-core
  - ✅ waivern-llm
  - ✅ waivern-connectors-database
  - ✅ waivern-rulesets
  - ✅ waivern-analysers-shared
  - ✅ waivern-mysql
  - ✅ waivern-personal-data-analyser
- [x] Connectors extracted (Steps 1-3):
  - ✅ waivern-filesystem (Step 1)
  - ✅ waivern-sqlite (Step 2)
  - ✅ waivern-source-code (Step 3)
- [x] Familiar with [Component Extraction Template](../../guides/component-extraction-template.md)
- [x] Feature branch created (e.g., `feature/extract-all-components`)

---

## Success Indicators

After completing all steps:
- ✅ **12 standalone packages** in libs/ directory
- ✅ **No waivern-community** package
- ✅ **All tests passing** (`uv run pytest`)
- ✅ **All quality checks passing** (`./scripts/dev-checks.sh`)
- ✅ **4 connectors** discoverable (`uv run wct ls-connectors`)
- ✅ **3 analysers** discoverable (`uv run wct ls-analysers`)
- ✅ **Sample runbooks working** (file_content_analysis.yaml, LAMP_stack.yaml)
- ✅ **No waivern_community imports** in active code
- ✅ **Documentation updated** (CLAUDE.md, migration docs)

---

## Troubleshooting

### Common Issues

**Issue:** Package not found after extraction
**Solution:** Check `[tool.uv.sources]` in root pyproject.toml - must be manually added

**Issue:** Schema not found
**Solution:** Verify `SchemaRegistry.register_search_path()` in package __init__.py

**Issue:** Import errors after extraction
**Solution:** Check that all waivern_community imports were updated to new packages

**Issue:** Tests failing after extraction
**Solution:** Run `uv sync` and verify all dependencies are installed

### Getting Help

- Review the [Component Extraction Template](../../guides/component-extraction-template.md)
- Check the [Troubleshooting Section](../extract-remaining-components.md#troubleshooting) in main plan
- Review completed extractions (waivern-mysql, waivern-personal-data-analyser)

---

## Estimated Timeline

| Phase | Steps | Sequential Time | Parallel Time |
|-------|-------|----------------|---------------|
| Phase 1 | 1-2 | 2 sessions | 1 session |
| Phase 2 | 3 | 1 session | 1 session |
| Phase 3 | 4 | 1 session | 0 sessions (parallel with Phase 2) |
| Phase 4 | 5 | 1 session | 1 session |
| Phase 5 | 6-7 | 2 sessions | 2 sessions |
| **Total** | **7** | **7 sessions** | **5 sessions** |

*Session = focused work period, exact duration varies by experience*

---

## Notes

- Each step is designed to be completed in a single Claude Code session
- Steps can be assigned to different developers where noted
- All steps must pass `./scripts/dev-checks.sh` before committing
- Rollback instructions included in each step file
- Final step (7) marks completion of monorepo migration

---

## References

- [Main Extraction Plan](../extract-remaining-components.md)
- [Component Extraction Template](../../guides/component-extraction-template.md)
- [Monorepo Migration Completed](../../../roadmaps/monorepo-migration/monorepo-migration-completed.md)
