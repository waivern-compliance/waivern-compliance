# Step 7: Remove waivern-community Package

**Phase:** 5 - Remove waivern-community
**Complexity:** 🟢 Low
**Risk:** 🟢 Low
**Dependencies:** Step 6 must be complete (WCT no longer depends on waivern-community)
**Needed By:** None (final step)

---

## Purpose

Completely remove the waivern-community package from the workspace. After all components have been extracted and WCT has been updated to import directly from standalone packages, waivern-community is no longer needed.

---

## Context

All components have been extracted (Steps 1-5) and WCT has been updated to import directly from standalone packages (Step 6). The waivern-community package is now empty and serves no purpose. This step removes it completely and updates all documentation.

**What gets removed:**
- `libs/waivern-community/` directory (entire package)
- waivern-community entry in root `pyproject.toml` workspace sources
- All references to waivern-community in documentation

---

## Pre-Flight Checks

Before proceeding, verify Step 6 is complete:

```bash
# 1. Verify WCT doesn't depend on waivern-community
grep "waivern-community" apps/wct/pyproject.toml
# Should return: NO RESULTS

# 2. Verify no waivern_community imports in WCT
grep -r "waivern_community" apps/wct/src/wct/ apps/wct/tests/
# Should return: NO RESULTS

# 3. Verify all tests pass
./scripts/dev-checks.sh
# Should return: ALL PASSING
```

**CRITICAL:** Do NOT proceed if any of the above checks fail.

---

## Implementation Steps

### 1. Final Verification

Run full test suite to ensure everything works without modifications:

```bash
# Full workspace tests
uv run pytest

# Quality checks
./scripts/dev-checks.sh

# Component discovery
uv run wct ls-connectors
uv run wct ls-analysers

# Sample runbooks
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

**All must pass before proceeding.**

### 2. Remove waivern-community from Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "libs/*",    # waivern-community will be deleted
    "apps/*",
]

[tool.uv.sources]
waivern-core = { workspace = true }
waivern-llm = { workspace = true }
waivern-connectors-database = { workspace = true }
waivern-mysql = { workspace = true }
waivern-filesystem = { workspace = true }
waivern-sqlite = { workspace = true }
waivern-source-code = { workspace = true }
waivern-rulesets = { workspace = true }
waivern-analysers-shared = { workspace = true }
waivern-personal-data-analyser = { workspace = true }
waivern-data-subject-analyser = { workspace = true }
waivern-processing-purpose-analyser = { workspace = true }
# waivern-community = { workspace = true }  # REMOVE THIS LINE
```

### 3. Delete waivern-community Package

```bash
# Delete the entire package directory
rm -rf libs/waivern-community
```

### 4. Workspace Sync

```bash
# Sync workspace without waivern-community
uv sync

# Verify sync succeeds
echo $?  # Should be 0
```

### 5. Update CLAUDE.md

Update the package structure section in `CLAUDE.md`:

```markdown
## Monorepo Structure

\```
waivern-compliance/
├── libs/                           # Framework libraries
│   ├── waivern-core/              # Core abstractions
│   ├── waivern-llm/               # LLM abstraction
│   ├── waivern-connectors-database/  # Shared SQL utilities
│   ├── waivern-mysql/             # MySQL connector
│   ├── waivern-filesystem/        # Filesystem connector
│   ├── waivern-sqlite/            # SQLite connector
│   ├── waivern-source-code/       # Source code connector
│   ├── waivern-rulesets/          # Shared rulesets
│   ├── waivern-analysers-shared/  # Shared analyser utilities
│   ├── waivern-personal-data-analyser/  # Personal data analyser
│   ├── waivern-data-subject-analyser/   # Data subject analyser
│   └── waivern-processing-purpose-analyser/  # Processing purpose analyser
└── apps/                           # Applications
    └── wct/                        # Waivern Compliance Tool
\```
```

Update package descriptions:

```markdown
### Package Descriptions

**Framework Libraries:**
- **waivern-core**: Base abstractions (Connector, Analyser, Message, Schema)
- **waivern-llm**: Multi-provider LLM service

**Shared Utilities:**
- **waivern-connectors-database**: Shared SQL connector utilities
- **waivern-rulesets**: Shared rulesets for pattern-based analysis
- **waivern-analysers-shared**: Shared analyser utilities

**Connectors:**
- **waivern-mysql**: MySQL connector
- **waivern-filesystem**: Filesystem connector
- **waivern-sqlite**: SQLite connector
- **waivern-source-code**: Source code connector with tree-sitter parsing

**Analysers:**
- **waivern-personal-data-analyser**: Personal data detection
- **waivern-data-subject-analyser**: Data subject identification
- **waivern-processing-purpose-analyser**: Processing purpose analysis

**Applications:**
- **wct**: CLI tool for compliance analysis
```

Remove any mentions of:
- "waivern-community"
- "re-exports from waivern-community"
- "backward compatibility via waivern-community"

### 6. Update Migration Documentation

Update `docs/roadmaps/monorepo-migration/monorepo-migration-completed.md`:

Add final phase entry:

```markdown
## Phase 7: Complete waivern-community Removal (2025-11-07)

**Objective:** Remove waivern-community package entirely after extracting all components.

**Actions:**
- Extracted remaining 5 components as standalone packages:
  - waivern-filesystem (filesystem connector)
  - waivern-sqlite (SQLite connector)
  - waivern-source-code (source code connector with tree-sitter)
  - waivern-data-subject-analyser (data subject identification)
  - waivern-processing-purpose-analyser (processing purpose analysis)
- Updated WCT to import directly from standalone packages
- Removed waivern-community package completely

**Outcome:**
- Clean architecture with 12 standalone packages
- No intermediary re-export layer
- WCT has explicit dependencies on packages it uses
- Monorepo migration completed

**Final Package Count:** 12 standalone packages
```

### 7. Update README.md (if needed)

If the project README mentions waivern-community, update it to reflect the new structure.

### 8. Search for Remaining References

```bash
# Search for any remaining references to waivern-community
grep -r "waivern-community" . \
  --exclude-dir=.git \
  --exclude-dir=.pytest_cache \
  --exclude-dir=__pycache__ \
  --exclude-dir=.ruff_cache \
  --exclude-dir=.venv \
  --exclude-dir=node_modules \
  --exclude="*.pyc"

# Should only find references in:
# - This step file
# - Migration documentation (historical references)
# - Git history

# Check Python imports
grep -r "from waivern_community" . \
  --include="*.py" \
  --exclude-dir=.git
# Should return: NO RESULTS (except in docs)

grep -r "import waivern_community" . \
  --include="*.py" \
  --exclude-dir=.git
# Should return: NO RESULTS (except in docs)
```

---

## Testing

### Workspace Tests

```bash
# Full test suite
uv run pytest
# Expected: All tests passing

# Quality checks
./scripts/dev-checks.sh
# Expected: All checks passing
```

### Component Discovery

```bash
# List all connectors
uv run wct ls-connectors
# Expected: filesystem, mysql, source_code, sqlite (4 connectors)

# List all analysers
uv run wct ls-analysers
# Expected: data_subject, personal_data, processing_purpose (3 analysers)
```

### Integration Tests

```bash
# Validate runbooks
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
# Expected: Both validate successfully

# Run runbooks
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
# Expected: Both run successfully
```

### Package Count Verification

```bash
# Count standalone packages
ls -1 libs/ | wc -l
# Expected: 12

# List all packages
ls -1 libs/
# Expected output:
# waivern-analysers-shared
# waivern-connectors-database
# waivern-core
# waivern-data-subject-analyser
# waivern-filesystem
# waivern-llm
# waivern-mysql
# waivern-personal-data-analyser
# waivern-processing-purpose-analyser
# waivern-rulesets
# waivern-source-code
# waivern-sqlite
```

---

## Verification Checklist

- [ ] libs/waivern-community/ directory deleted
- [ ] waivern-community removed from root pyproject.toml [tool.uv.sources]
- [ ] uv sync succeeds without waivern-community
- [ ] All workspace tests passing
- [ ] All quality checks passing
- [ ] Component discovery working (4 connectors, 3 analysers)
- [ ] Sample runbooks validating and running
- [ ] CLAUDE.md updated (no waivern-community references)
- [ ] Migration documentation updated
- [ ] No waivern-community imports in codebase (except docs)
- [ ] Workspace contains exactly 12 standalone packages
- [ ] Changes committed with message: `refactor: remove waivern-community package`

---

## Success Criteria

- [ ] waivern-community package completely removed from workspace
- [ ] All tests passing without waivern-community
- [ ] No references to waivern-community in active code
- [ ] Documentation updated to reflect new structure
- [ ] 12 standalone packages in libs/ directory
- [ ] Component extraction and migration complete

---

## Rollback Plan

If critical issues are discovered after removal:

```bash
# 1. Restore waivern-community from git
git checkout HEAD~1 -- libs/waivern-community

# 2. Restore workspace sources entry
# Edit pyproject.toml to add: waivern-community = { workspace = true }

# 3. Revert WCT dependencies
# Edit apps/wct/pyproject.toml to add waivern-community dependency

# 4. Sync and test
uv sync
./scripts/dev-checks.sh
```

---

## Decisions Made

1. **Complete removal:** No backward compatibility layer kept
2. **Clean break:** All components now standalone
3. **Documentation updates:** Reflects new 12-package structure
4. **Migration complete:** This marks the end of the monorepo migration

---

## Notes

- This is the FINAL step in the component extraction plan
- Completes the monorepo migration to fully independent packages
- waivern-community served its purpose during transition but is no longer needed
- Final architecture is cleaner with explicit dependencies
- Future components will be created as standalone packages from the start

---

## Celebration 🎉

After completing this step:
- ✅ All 5 remaining components extracted as standalone packages
- ✅ WCT updated to use standalone packages directly
- ✅ waivern-community removed completely
- ✅ 12 standalone packages total
- ✅ Monorepo migration COMPLETE

The Waivern Compliance Framework now has a clean, modular architecture with fully independent packages!
