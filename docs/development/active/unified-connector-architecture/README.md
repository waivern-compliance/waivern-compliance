# Development Task Plans

This directory contains detailed task plans for implementing features and refactoring in the Waivern Compliance Framework.

## Active Task Plans

### ArtifactStore Service Implementation (#227)

Foundation for unified connector architecture - implements service-based artifact management.

1. **[Core Service Implementation](../../completed/artifect-store/artifact-store-task-1-core-service.md)** ✅
   - Abstract ArtifactStore interface
   - InMemoryArtifactStore implementation
   - Exception hierarchy and factory pattern
   - **Prerequisites:** None
   - **Status:** COMPLETED

2. **[ServiceContainer Integration](../../completed/artifect-store/artifact-store-task-2-service-container.md)** ✅
   - Integrate ArtifactStore with dependency injection system
   - Lazy initialisation and singleton behaviour
   - Configuration via environment variables
   - **Prerequisites:** Task 1
   - **Status:** COMPLETED

3. **[Executor Integration](../../completed/artifect-store/artifact-store-task-3-executor-integration.md)** ✅
   - Replace dict-based artifact storage with service
   - Maintain backward compatibility
   - Lifecycle management and cleanup
   - **Prerequisites:** Tasks 1-2
   - **Status:** COMPLETED

### Unified Connector Architecture (#226)

Simplifies Executor by ensuring every step has a connector, eliminating dual-mode execution logic.

4. **[ArtifactConnector Implementation](unified-connector-task-1-artifact-connector.md)**
   - Create connector for artifact retrieval
   - ComponentFactory and configuration
   - Entry point registration
   - **Prerequisites:** ArtifactStore tasks (1-3)
   - **Status:** TODO

5. **[Executor Refactoring](unified-connector-task-2-executor-refactor.md)**
   - Remove dual-mode branching logic
   - Merge schema resolution methods
   - Simplify helper method signatures
   - **Prerequisites:** Task 4
   - **Status:** TODO

6. **[Runbook Migration](unified-connector-task-3-runbook-migration.md)**
   - Update sample runbooks to new format
   - Replace `input_from` with ArtifactConnector
   - Update documentation
   - **Prerequisites:** Task 5
   - **Status:** TODO

## Task Execution Order

**Sequential execution required:**

```
ArtifactStore Service (Foundation)
├── Task 1: Core Service ──────────┐
├── Task 2: ServiceContainer ──────┤
└── Task 3: Executor Integration ──┤
                                    ↓
Unified Connector Architecture (Builds on foundation)
├── Task 4: ArtifactConnector ─────┐
├── Task 5: Executor Refactor ─────┤
└── Task 6: Runbook Migration ─────┘
```

**Dependencies:**
- Tasks 1-3 must complete before Task 4
- Tasks 4-6 build on ArtifactStore foundation
- Each task within a group depends on previous tasks

## Related Documentation

- **Planning Docs:**
  - [ArtifactStore Service Plan](../active/artifact-store-service-plan.md)
  - [Unified Connector Architecture Plan](../active/unified-connector-architecture-plan.md)

- **GitHub Issues:**
  - [#227 - Implement ArtifactStore Service](https://github.com/waivern-compliance/waivern-compliance/issues/227)
  - [#226 - Unified Connector Architecture](https://github.com/waivern-compliance/waivern-compliance/issues/226)

- **Architecture Docs:**
  - [WCF Core Components](../../core-concepts/wcf-core-components.md)
  - [CLAUDE.md](../../../CLAUDE.md) - Development guidelines

## Task Plan Format

Each task plan includes:

- **Context** - Background and positioning within larger effort
- **Purpose** - What this task achieves
- **Problem** - What issue it solves
- **Proposed Solution** - High-level approach
- **Decisions Made** - Key architectural choices
- **Implementation** - What needs to change (pseudo-code, not full implementations)
- **Testing** - Test scenarios and validation approaches
- **Implementation Notes** - Design principles and considerations

Task plans are **descriptive, not prescriptive** - they explain the problem and approach whilst allowing implementers to make detailed decisions.

## Validation

After completing each task:

```bash
# Run quality checks
./scripts/dev-checks.sh

# Run relevant tests
uv run pytest <package-path>/tests/ -v

# Validate overall system
uv run wct ls-connectors
uv run wct ls-analysers
```

## Notes

- Tasks follow British English spelling conventions
- Each task should pass quality checks before proceeding
- Breaking changes documented in task plans
- Integration tests verify cross-task compatibility
