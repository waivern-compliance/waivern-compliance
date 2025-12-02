# Task 6: Update Documentation and Clean Up Old Code

- **Phase:** 4 - Finalisation
- **Status:** DONE
- **GitHub Issue:** #247 (close via PR)
- **Prerequisites:** Task 5 (CLI and runbook migration)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Tasks 1-5 implemented and integrated the new orchestration system. This final task updates documentation to reflect the new runbook format and removes the old executor code.

## Purpose

1. Update user-facing documentation for the artifact-centric format
2. ~~Remove deprecated code (old Executor, old runbook models)~~ ✅ Done in Task 5
3. Update CLAUDE.md with new runbook format
4. Move design docs from `active/` to `completed/`

## Problem

Documentation still references the old three-section runbook format. ~~Old code remains in the codebase alongside new code.~~ This creates confusion and maintenance burden.

## Decisions Made

1. **Full removal** - No deprecation period, old code removed completely
2. **Update all docs** - Ensure consistency across all documentation
3. **Archive design docs** - Move to completed folder for reference

## Implementation

### Changes Required

#### 1. Update apps/wct/runbooks/README.md

Replace old format documentation with new artifact-centric format:

**Sections to update:**
- Runbook structure overview
- Field descriptions
- Examples
- Reference for all fields

**New structure to document:**
```yaml
name: str (required)
description: str (required)
contact: str (optional)

config:                    # Optional execution config
  timeout: int            # Total timeout in seconds
  cost_limit: float       # LLM budget
  max_concurrency: int    # Parallel artifacts (default: 10)

artifacts:
  <artifact_id>:
    # Metadata (optional)
    name: str
    description: str
    contact: str

    # Source (mutually exclusive with 'inputs')
    source:
      type: str           # Connector type
      properties: {}      # Connector config

    # Derived (mutually exclusive with 'source')
    inputs: str | list[str] # Upstream artifact(s)
    transform:
      type: str           # Analyser type
      properties: {}      # Analyser config
    merge: "concatenate"  # Merge strategy for fan-in (only concatenate supported)

    # Behaviour
    output: bool          # Export this artifact (default: false)
    optional: bool        # Continue on failure (default: false)
```

#### 2. Update CLAUDE.md

**Sections to update:**

1. **Runbook Format section:**
   - Replace example with artifact-centric format
   - Update field descriptions

2. **How the Framework Works section:**
   - Update data flow description
   - Mention Planner and DAGExecutor

3. **Sample Runbooks section:**
   - Update paths and descriptions

#### 3. Move design docs to completed

```
docs/development/active/artifact-centric-orchestration-design.md
  → docs/development/completed/artifact-centric-orchestration-design.md

docs/development/active/artifact-centric-orchestration-implementation.md
  → docs/development/completed/artifact-centric-orchestration-implementation.md

docs/development/active/artifact-centric-orchestration/
  → docs/development/completed/artifact-centric-orchestration/
```

Update status in design doc:
```markdown
- **Status:** Completed
```

#### 4. Update future-plans docs

Update status in related docs:
- `docs/future-plans/artifact-centric-runbook.md` - Mark Phase 1 complete
- `docs/future-plans/dag-orchestration-layer.md` - Mark Phase 1 complete

Add note pointing to implementation:
```markdown
> **Implementation:** See [completed design](../development/completed/artifact-centric-orchestration-design.md)
```

## Testing

### Verification Checklist

#### Documentation
- [ ] README examples run successfully
- [ ] All code snippets are valid
- [ ] No references to old format remain
- [ ] Links between docs work

#### Code Removal (✅ Done in Task 5)
- [x] No imports of removed modules
- [x] All tests pass after removal
- [x] No dead code warnings

#### Integration
- [ ] `wct run` works with documented examples
- [ ] `wct --help` shows correct commands
- [ ] Error messages reference correct format

### Validation Commands

```bash
# Run all tests
uv run pytest -v

# Run sample runbooks
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml

# Full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- ~~Search codebase thoroughly for old format references~~ ✅ Done
- ~~Check test fixtures for old format runbooks~~ ✅ Done
- ~~Update any integration tests that use old format~~ ✅ Done
- Reference ADR-0003 when documenting fan-in behaviour (only "concatenate" merge supported in Phase 1)
