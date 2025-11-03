# Dynamic and Agentic Workflows

**Status:** Future Vision
**Last Updated:** 2025-10-31
**Related Epics:** #189 (DAG Execution), #190 (Templates)

## Vision

Evolve WCF from supporting only static, pre-defined workflows to enabling dynamic, agent-driven compliance analysis. This would allow LLM agents to analyse organisational documents (privacy policies, system architecture), determine required compliance checks, and dynamically orchestrate analyses - potentially recursively.

## Example Use Case

An analyser receives a privacy policy document as input:

1. Uses LLM to understand the organisation's data processing activities
2. Determines what compliance analyses are required
3. Identifies which systems need to be checked
4. Dynamically generates and executes a runbook to perform the necessary checks
5. Child analysers may spawn further sub-workflows as needed

This creates an **agentic compliance analysis system** that can adapt to each organisation's unique setup.

## The Challenge

Current and near-future WCF handles **static workflows**:
- DAG is known at parse time
- All components pre-defined
- Execution path deterministic

Dynamic workflows require:
- **Runtime workflow generation** by agents/LLMs
- **Child workflow spawning** (potentially recursive)
- **Dynamic component discovery and orchestration**
- **Adaptive execution paths** based on intermediate results

## Architectural Approach

WCF will adopt **Runbooks as First-Class Data** - treating runbooks as data that analysers can produce and consume. This aligns perfectly with WCF's schema-driven architecture.

**Core Principle:** Runbooks become just another schema type that flows through the system, enabling agents to generate valid workflows that can be executed dynamically.

**Example:**
```yaml
execution:
  - name: "Generate compliance runbook"
    analyser: "policy_to_runbook_analyser"
    input_schema: "privacy_policy_document"
    output_schema: "runbook_definition"  # New schema type!
    output: "generated_runbook"

  - name: "Execute generated runbook"
    type: "execute_workflow"
    workflow: "{{ generated_runbook }}"
    limits:
      max_depth: 2
      max_duration: 3600
      max_llm_cost: 50
```

**Why this approach:**
- Fits WCF's schema-driven philosophy
- Runbooks are just another data type
- Full validation via schemas
- Clear data lineage
- Enables progressive enhancement through phases

## Evolution Path

This will be implemented through three progressive phases:

### Phase 1: Child Workflow Execution (Foundation)

**Goal:** Enable runbooks to invoke other runbooks.

**Implementation:**
- Add `execute_workflow` step type to execution schema
- Support parent-child workflow relationships
- Implement safeguards (max depth, timeouts, cost limits)
- Add workflow tracing and observability

**Enables:** Basic composition, manual workflow orchestration

**Epic:** Child Workflow Execution (to be created)

### Phase 2: Runbook Generation Schema (Enable Agents)

**Goal:** Allow analysers to generate valid runbooks as output.

**Implementation:**
- Create `RunbookDefinitionSchema`
- Analysers can declare this as output schema
- Add validation layer for generated runbooks
- Enable LLMs to produce structured runbook definitions

**Enables:** The privacy policy use case! Agents can now generate workflows.

**Epic:** Runbook Generation Schema

### Phase 3: Agent Framework Integration (Full Power)

**Goal:** Purpose-built agentic analysers with sophisticated planning.

**Implementation:**
- Agentic analyser base class
- Integration with LangGraph/CrewAI/similar frameworks
- Advanced planning capabilities
- Multi-agent collaboration support
- Full execution tracing and cost tracking

**Enables:** Complex multi-agent compliance analysis systems.

**Epic:** Agent Framework Integration

## Critical Requirements

Any implementation **must** include:

### 1. Safeguards

- **Max recursion depth** - Prevent infinite recursion
- **Execution timeouts** - Workflow and step-level timeouts
- **LLM cost limits** - Prevent runaway API costs
- **Component whitelists** - Restrict what agents can invoke
- **Resource limits** - Memory, CPU, concurrent workflows

### 2. Observability

- **Execution tree tracing** - Full parent-child relationship tracking
- **Cost tracking** - Per-workflow LLM and resource costs
- **State visibility** - Inspect workflow state at any point
- **Audit logs** - Complete history of decisions and actions
- **Debug mode** - Step-through execution for troubleshooting

### 3. Validation

- **Schema validation** - All generated runbooks must be valid
- **Component availability** - Check components exist before execution
- **Circular dependency detection** - Prevent infinite loops
- **Access control** - Validate permissions for dynamic operations
- **Input validation** - Sanitise all dynamic inputs

### 4. State Management

- **Workflow persistence** - Save state to disk/database
- **Restart capability** - Resume from last checkpoint
- **Failure recovery** - Graceful handling of partial failures
- **Rollback support** - Undo operations where possible
- **Idempotency** - Safe to retry operations

## Inspiration from Existing Systems

### Temporal.io (Workflow Orchestration)

- Durable execution with automatic retries
- Parent-child workflow spawning
- Built-in observability and replay
- Strong guarantees around state

**Lessons:** Durability and observability are critical for production workflows.

### Apache Airflow (Pipeline Orchestration)

- Static DAGs with dynamic task generation
- TaskFlow API for runtime flexibility
- Strong ecosystem and community patterns

**Lessons:** Hybrid static/dynamic models can work well.

### LangGraph / CrewAI (Agent Frameworks)

- State machines with agent nodes
- Multi-agent collaboration patterns
- LLM-native orchestration

**Lessons:** Agents need structured state management and clear boundaries.

## Open Questions

1. **LLM Determinism:** How to ensure reproducible results with non-deterministic LLMs?
2. **Cost Control:** What's an appropriate cost limit model (per workflow, per user, org-wide)?
3. **Security:** How to sandbox agent-generated workflows safely?
4. **Approval Workflows:** Should generated workflows require human approval before execution?
5. **Multi-tenancy:** How to isolate workflows in shared environments?

## Related Documents

- [WCF Core Components](../core-concepts/wcf-core-components.md)
- [Executor Design](../architecture/executor.md) (when created)
- ADR: DAG Execution Model (to be created)
- ADR: Runbook Generation Schema (to be created)

## Conclusion

Dynamic and agentic workflows represent a significant evolution for WCF. By taking a phased approach - starting with child workflows, then runbook generation, then full agent integration - we can build towards this vision whilst maintaining stability and security.

The key is to preserve WCF's core principles (schema-driven, component-based, auditable) whilst adding the flexibility needed for agent-driven compliance analysis.

With this vision, WCF could become the OSS compliance framework that combines traditional expert humans workflow orchestration with agentic exploration and analysis.
