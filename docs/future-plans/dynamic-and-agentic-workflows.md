# Dynamic and Agentic Workflows

- **Status:** Future Vision
- **Last Updated:** 2025-11-26
- **Related:** [Artifact-Centric Runbook](./artifact-centric-runbook.md), [DAG Orchestration Layer](./dag-orchestration-layer.md), [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md)

## Vision

Evolve WCF from supporting only static, pre-defined workflows to enabling dynamic, agent-driven compliance analysis. LLM agents analyse organisational documents (privacy policies, system architecture), determine required compliance checks, and dynamically orchestrate analyses - potentially recursively.

## Example Use Case

An analyser receives a privacy policy document:

1. Uses LLM to understand the organisation's data processing activities
2. Determines what compliance analyses are required
3. Identifies which systems need to be checked
4. Dynamically generates and executes a runbook
5. Child analysers may spawn further sub-workflows

## Evolution Path

### Phase 1 & 2: Foundation (Designed)

**Now covered by:**
- [Artifact-Centric Runbook](./artifact-centric-runbook.md) - Composable/recursive runbooks, `execute: child` directive
- [DAG Orchestration Layer](./dag-orchestration-layer.md) - Planner/Executor separation, parallel execution
- [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md) - Service injection pattern

The core infrastructure for child workflow execution and runbook generation is designed in these documents.

### Phase 3: Agent Framework Integration (Future)

**Goal:** Purpose-built agentic analysers with sophisticated planning.

**Scope:**
- Agentic analyser base class
- Integration with LangGraph/CrewAI/similar frameworks
- Advanced planning capabilities
- Multi-agent collaboration support
- Full execution tracing and cost tracking

## Critical Requirements

### Safeguards

- Max recursion depth
- Execution timeouts (workflow and step-level)
- LLM cost limits
- Component whitelists
- Resource limits (memory, CPU, concurrent workflows)

### Observability

- Execution tree tracing (parent-child relationships)
- Cost tracking (per-workflow LLM and resource costs)
- State visibility
- Audit logs
- Debug mode (step-through execution)

### Validation

- Schema validation for generated runbooks
- Component availability checks
- Circular dependency detection
- Access control for dynamic operations
- Input sanitisation

### State Management (Future)

- Workflow persistence (disk/database)
- Restart capability (resume from checkpoint)
- Failure recovery
- Rollback support
- Idempotency

## Open Questions

1. **LLM Determinism:** How to ensure reproducible results with non-deterministic LLMs?
2. **Cost Control:** What's an appropriate cost limit model (per workflow, per user, org-wide)?
3. **Security:** How to sandbox agent-generated workflows safely?
4. **Approval Workflows:** Should generated workflows require human approval before execution?
5. **Multi-tenancy:** How to isolate workflows in shared environments?

## Related Documents

- [Artifact-Centric Runbook](./artifact-centric-runbook.md) - Runbook format with composable execution
- [DAG Orchestration Layer](./dag-orchestration-layer.md) - Execution engine
- [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md) - Service injection pattern
- [WCF Core Components](../core-concepts/wcf-core-components.md) - Framework architecture
