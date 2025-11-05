# Schema Versioning System - Execution Plan

**Status:** DRAFT - Awaiting Approval
**Created:** 2025-11-05
**Design Document:** [schema-versioning-design.md](./schema-versioning-design.md)

## Executive Summary

This plan implements multi-version schema support in WCF through file-based auto-discovery. The implementation converts the current abstract Schema class hierarchy into a single generic Schema class, adds auto-discovery capabilities to base classes, and introduces a reader/producer pattern for version-specific logic.

## Goals

1. **Eliminate manual version maintenance** - Components declare version support through file presence
2. **Enable multi-version support** - Components can handle multiple schema versions simultaneously
3. **Simplify schema evolution** - Add version = add file, remove version = delete file
4. **Maintain backward compatibility** - Existing runbooks continue to work
5. **Clear deprecation path** - JSON-based deprecation metadata with tooling support

## Current State Assessment

### Current Architecture

```
Schema (ABC)
├── StandardInputSchema (concrete, v1.0.0 only)
├── PersonalDataFindingSchema (concrete, v1.0.0 only)
└── BaseFindingSchema (abstract) → other finding schemas

Components:
- Hardcode version support in class attributes
- Single version per schema type
- Type-based schema equality (type(self) == type(other))
```

### Current Pain Points

1. **No multi-version support** - Can only work with one version at a time
2. **Manual maintenance** - Adding version requires code changes
3. **No version negotiation** - Executor can't match compatible versions
4. **Unclear deprecation** - No mechanism to phase out old versions

## Target Architecture

### New Architecture

```
Schema (concrete class)
- Instantiated with (name, version)
- Lazy loads JSON schema definitions
- Equality based on (name, version) tuple
- Shared singleton loader for caching

Components:
schema_readers/          # Auto-discovered input versions (analysers)
  standard_input_1_0_0.py
  standard_input_1_1_0.py
schema_producers/        # Auto-discovered output versions (connectors + analysers)
  personal_data_finding_1_0_0.py
  personal_data_finding_1_1_0.py
```

### Key Changes

1. **Schema class** - Abstract base → Single concrete class
2. **Version declaration** - Code → File presence
3. **Schema discovery** - Manual lists → Auto-discovery from directories
4. **Version logic** - Inline → Separate reader/producer modules
5. **Schema equality** - Type-based → (name, version) tuple-based

## Implementation Phases

### Phase 1: Schema Infrastructure
**Goal:** Replace schema class hierarchy with single generic Schema class

**Key Changes:**
- Convert Schema from ABC to concrete class
- Remove all concrete schema subclasses (StandardInputSchema, PersonalDataFindingSchema, etc.)
- Update Schema equality from type-based to (name, version) tuple-based
- Add shared singleton loader for efficient caching
- Fix all schema instantiations: `StandardInputSchema()` → `Schema("standard_input", "1.0.0")`

**Dependencies:** None
**Risk:** High (touches all code using schemas)
**Testing:** All existing tests must pass with new Schema class

**Files to Update:**
- `libs/waivern-core/src/waivern_core/schemas/base.py` - Convert Schema to concrete
- `libs/waivern-core/src/waivern_core/schemas/standard_input.py` - Remove class
- All schema files in waivern-community, waivern-personal-data-analyser
- All code instantiating schema objects (hundreds of locations)

**Success Criteria:**
- ✅ Single Schema class with (name, version) constructor
- ✅ Lazy loading of JSON schemas
- ✅ Shared singleton loader with caching
- ✅ All tests pass (845+ tests)
- ✅ No schema subclasses remain

---

### Phase 2: Base Class Auto-Discovery
**Goal:** Add file-based version discovery to Connector and Analyser base classes

**Key Changes:**
- Add auto-discovery to `Connector.get_supported_output_schemas()`
- Add auto-discovery to `Analyser.get_supported_input_schemas()`
- Add auto-discovery to `Analyser.get_supported_output_schemas()`
- Implement filename parsing: `standard_input_1_0_0.py` → `Schema("standard_input", "1.0.0")`
- Document directory conventions: `schema_readers/` and `schema_producers/`

**Dependencies:** Phase 1 complete
**Risk:** Low (base classes only, components override if needed)
**Testing:** Unit tests for auto-discovery logic

**Files to Update:**
- `libs/waivern-core/src/waivern_core/base_connector.py` - Add auto-discovery
- `libs/waivern-core/src/waivern_core/base_analyser.py` - Add auto-discovery

**Success Criteria:**
- ✅ Auto-discovery scans `schema_readers/` and `schema_producers/`
- ✅ Filename parsing works for various schema names
- ✅ Components can override methods for custom logic
- ✅ Zero file I/O during discovery (Schema objects are lightweight)

---

### Phase 3: Proof of Concept Component
**Goal:** Refactor PersonalDataAnalyser to use reader/producer pattern

**Key Changes:**
- Create `schema_readers/standard_input_1_0_0.py` with `read()` function
- Create `schema_producers/personal_data_finding_1_0_0.py` with `produce()` function
- Add module caching (`_reader_cache`, `_producer_cache`)
- Update `process()` to dynamically load readers/producers
- Remove hardcoded version support lists

**Dependencies:** Phase 2 complete
**Risk:** Medium (first component migration, establishes pattern)
**Testing:** All PersonalDataAnalyser tests must pass

**Files to Create:**
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_readers/`
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/schema_producers/`

**Files to Update:**
- `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/analyser.py`

**Success Criteria:**
- ✅ PersonalDataAnalyser uses reader/producer pattern
- ✅ Auto-discovery works (schemas advertised without code changes)
- ✅ All existing tests pass
- ✅ Pattern documented for other components

---

### Phase 4: Executor Version Matching
**Goal:** Implement version negotiation in WCT Executor

**Key Changes:**
- Update `ExecutionStep` dataclass with `input_schema_version` and `output_schema_version` fields
- Implement `_resolve_step_schemas()` for version matching
- Implement `_find_compatible_schema()` with exact version matching
- Add version sorting utility
- Pass resolved schemas to components during execution
- Add custom error classes for version mismatches

**Dependencies:** Phase 3 complete (need working example)
**Risk:** Medium (changes execution flow)
**Testing:** Integration tests with multiple schema versions

**Files to Update:**
- `apps/wct/src/wct/executor.py` - Add version resolution
- `apps/wct/src/wct/schemas/runbook.py` - Add version fields

**Success Criteria:**
- ✅ Executor selects latest compatible version by default
- ✅ Executor respects explicit version pins in runbook
- ✅ Clear error messages for version mismatches
- ✅ Integration tests cover version scenarios

---

### Phase 5: Runbook Format Updates
**Goal:** Support version specification in runbooks

**Key Changes:**
- Add optional `input_schema_version` and `output_schema_version` fields to execution steps
- Update runbook JSON schema
- Update runbook validation
- Update `wct validate-runbook` to check version compatibility
- Document version specification in runbook README

**Dependencies:** Phase 4 complete
**Risk:** Low (optional fields, backward compatible)
**Testing:** Runbook validation tests

**Files to Update:**
- `apps/wct/src/wct/schemas/runbook.py` - Add version fields
- `apps/wct/runbooks/README.md` - Document version fields
- Runbook JSON schema files

**Success Criteria:**
- ✅ Runbooks can specify versions (optional)
- ✅ Runbooks without versions still work (auto-select latest)
- ✅ Validation checks version compatibility
- ✅ Documentation updated with examples

---

### Phase 6: Component Rollout
**Goal:** Migrate all remaining components to reader/producer pattern

**Components to Migrate:**
- ✅ PersonalDataAnalyser (Phase 3 - done)
- ProcessingPurposeAnalyser
- DataSubjectAnalyser
- FilesystemConnector
- SQLiteConnector
- MySQLConnector
- SourceCodeConnector

**Per Component Steps:**
1. Create `schema_readers/` or `schema_producers/` directories
2. Extract version-specific logic to reader/producer modules
3. Add module caching
4. Remove hardcoded version lists
5. Test auto-discovery
6. Verify all tests pass

**Dependencies:** Phases 1-5 complete
**Risk:** Low (following established pattern)
**Testing:** Each component's test suite

**Success Criteria:**
- ✅ All components use reader/producer pattern
- ✅ All components advertise versions via auto-discovery
- ✅ All tests pass (845+ tests)
- ✅ No hardcoded version lists remain

## Testing Strategy

### Unit Tests
- Schema class equality and hashing
- Auto-discovery filename parsing
- Module caching in components
- Version sorting and comparison

### Integration Tests
- Executor version resolution with multiple versions
- Schema compatibility checking
- Version pinning in runbooks
- Default version selection

### Regression Tests
- All existing tests continue to pass
- Existing runbooks work without modification
- Component behavior unchanged (just implementation)

### Performance Tests
- Schema loading with caching
- Auto-discovery performance (should be negligible)
- Module caching effectiveness

## Risk Mitigation

### High Risk: Phase 1 Schema Refactoring

**Risk:** Breaking changes to core abstraction used everywhere
**Mitigation:**
- Comprehensive test coverage before starting
- Make changes in single atomic commit
- Run full test suite after each change
- Have rollback plan ready

### Medium Risk: Executor Changes

**Risk:** Version resolution bugs could break execution
**Mitigation:**
- Start with simple version matching (exact match only)
- Extensive integration tests
- Clear error messages for debugging
- Gradual rollout with monitoring

### Low Risk: Component Migration

**Risk:** Component-specific bugs during migration
**Mitigation:**
- Follow established pattern from Phase 3
- Migrate one component at a time
- Each component has own test suite
- Can rollback individual components

## Rollback Strategy

### Phase 1 Rollback
- Revert single commit with schema changes
- Restore original schema class hierarchy
- All tests should pass immediately

### Phase 2-6 Rollback
- Components can be rolled back individually
- Base class auto-discovery has defaults (empty lists)
- Executor changes are backward compatible

## Success Metrics

### Functional Metrics
- ✅ Components auto-discover schema versions
- ✅ Adding version support requires no code changes
- ✅ Executor successfully negotiates versions
- ✅ All 845+ tests pass

### Quality Metrics
- ✅ Zero type errors (basedpyright strict)
- ✅ Zero linting errors
- ✅ No performance degradation
- ✅ Clear error messages for version issues

### Documentation Metrics
- ✅ Developer guide for adding schema versions
- ✅ Runbook documentation updated
- ✅ Migration guide for existing components
- ✅ Examples of multi-version support

## Parallelisation Opportunities

Some phases can run in parallel:
- Phase 2 can start before Phase 1 is fully tested
- Phase 5 can run alongside Phase 4
- Phase 6 components can be migrated in parallel

## Open Questions for Review

1. **Performance:** Is lazy loading + caching sufficient? Should we benchmark?
2. **Deprecation:** Should Phase 1 include deprecation metadata support?
3. **Semver:** Should we support any semver compatibility (e.g., minor versions) or stay with exact matching?
4. **Testing:** Do we need additional integration tests beyond existing coverage?
5. **Documentation:** Should we create a video walkthrough for component migration?

## Approval Checklist

Before proceeding to detailed work unit breakdown:

- [ ] Architecture approach approved
- [ ] Phase sequence makes sense
- [ ] Risk mitigation adequate
- [ ] Testing strategy sufficient
- [ ] Any open questions resolved

## Next Steps

Once approved:
1. Break down each phase into atomic work units
2. Create step-by-step files in `docs/development/active/schema-versioning/`
3. Assign priority and dependencies to each unit
4. Begin Phase 1 implementation
