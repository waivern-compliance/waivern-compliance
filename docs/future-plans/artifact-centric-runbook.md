# Artifact-Centric Runbook Design

- **Status:** Design Proposal
- **Last Updated:** 2025-11-26
- **Related:** [DAG Orchestration Layer](./dag-orchestration-layer.md), [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md)

## Problem

The current runbook structure separates connectors, analysers, and execution into distinct sections:

```yaml
connectors:
  - name: "mysql_reader"
    type: "mysql"
    properties: {...}

analysers:
  - name: "pda"
    type: "personal_data_analyser"
    properties: {...}

execution:
  - id: "step1"
    connector: "mysql_reader"
    analyser: "pda"
    input_schema: "..."
    output_schema: "..."
```

**Issues:**

1. **Redundant structure** - Components defined separately but typically used once
2. **Component-centric** - Focuses on "what runs" rather than "what data flows"
3. **Implicit dependencies** - `input_from` creates hidden relationships
4. **Verbose** - Three sections to express a simple pipeline

## Insight

The natural unit is the **artifact** (data), not the component. Compliance analysis is about:
- Extracting data → producing artifacts
- Transforming data → deriving new artifacts from existing ones
- The DAG emerges naturally from artifact dependencies

## Proposed Design

### Core Concept

**Artifacts are nodes. Transformations are edges.**

```yaml
name: "GDPR Compliance Analysis"
description: "Analyse MySQL database for personal data"

artifacts:
  <artifact_id>:
    source: {...}      # OR
    from: <artifact_id(s)>
    transform: {...}
```

### Artifact Types

**Source Artifact** - Produced by a connector:
```yaml
db_schema:
  source:
    type: mysql
    properties:
      host: "${MYSQL_HOST}"
      database: "${MYSQL_DATABASE}"
```

**Derived Artifact** - Produced by transforming other artifacts:
```yaml
personal_data_findings:
  from: db_schema
  transform:
    type: personal_data_analyser
    properties:
      llm_validation: true
```

**Fan-in Artifact** - Multiple inputs merged:
```yaml
combined_findings:
  from:
    - mysql_findings
    - file_findings
  merge: concatenate
  transform:
    type: findings_aggregator
```

**Output Artifact** - Designated for export (file output, API response):
```yaml
final_report:
  from: combined_findings
  transform:
    type: report_generator
  output: true  # Explicit: export this artifact
```

Artifacts with `output: true` are:
- Written to output files by the Executor
- Returned in the ExecutionResult
- Available for both human consumption and downstream analysis

### Complete Example

```yaml
name: "GDPR Compliance Analysis"
description: "Full-stack personal data discovery"

artifacts:
  # Source artifacts
  db_schema:
    source:
      type: mysql
      properties:
        host: "${MYSQL_HOST}"
        database: "${MYSQL_DATABASE}"

  log_content:
    source:
      type: filesystem
      properties:
        path: "./logs/"

  # Parallel analysis (independent, run concurrently)
  db_findings:
    from: db_schema
    transform:
      type: personal_data_analyser
      properties:
        llm_validation: true

  log_findings:
    from: log_content
    transform:
      type: personal_data_analyser
      properties:
        llm_validation: false

  # Fan-in (waits for both inputs)
  combined_findings:
    from:
      - db_findings
      - log_findings
    merge: concatenate
    transform:
      type: findings_aggregator

  # Chained analysis (terminal artifact)
  nis2_assessment:
    from: combined_findings
    transform:
      type: nis2_policy_analyser
      properties:
        service_endpoint: "${NIS2_API}"
    output: true  # Export this artifact
```

## DAG Execution Model

The DAG is implicit in the `from` relationships:

```
     db_schema          log_content
     (source)           (source)
         │                   │
         ▼                   ▼
    db_findings        log_findings
         │                   │
         └───────┬───────────┘
                 ▼
        combined_findings
                 │
                 ▼
        nis2_assessment
```

**Execution:**

1. `TopologicalSorter` builds graph from `from` fields
2. Independent artifacts execute in parallel
3. Dependent artifacts wait for inputs
4. Each artifact saved to ArtifactStore upon completion

```python
async def execute(artifacts: dict[str, ArtifactDef]):
    dag = build_dag(artifacts)  # from → dependencies
    sorter = dag.get_sorter()

    while sorter.is_active():
        ready = sorter.get_ready()
        await asyncio.gather(*[produce(aid) for aid in ready])
        for aid in ready:
            sorter.done(aid)

async def produce(artifact_id: str):
    defn = artifacts[artifact_id]

    if defn.source:
        message = connector.extract()
    else:
        inputs = [store.get(fid) for fid in defn.from]
        message = analyser.process(merge(inputs))

    store.save(artifact_id, message)
```

## Design Properties

| Property | How It's Achieved |
|----------|-------------------|
| **Implicit DAG** | Derived from `from` relationships |
| **Parallel execution** | Independent artifacts run concurrently |
| **Reuse** | Same artifact ID can be referenced by multiple downstream artifacts |
| **Fan-in** | `from` accepts list of artifact IDs |
| **Fan-out** | Multiple artifacts can reference same source |
| **Extensibility** | New source/transform types added without schema changes |

## Error Handling

Per-artifact configuration:

```yaml
llm_enriched:
  from: findings
  transform:
    type: llm_enricher
  optional: true  # Skip dependents on failure, continue pipeline
```

## Extensibility

**HTTP-backed analyser:**
```yaml
legal_review:
  from: findings
  transform:
    type: legal_review_analyser
    properties:
      workflow_url: "${LEGAL_API}"
```

**Human approval (future):**
```yaml
approved_findings:
  from: legal_review
  transform:
    type: human_approval
    properties:
      approver_group: "legal-team"
```

**Conditional output (future):**
```yaml
high_risk_only:
  from: findings
  filter:
    field: "risk_level"
    equals: "high"
```

## Composable/Recursive Runbooks

A runbook can produce another runbook as output, enabling AI agents to dynamically generate compliance workflows.

### Runbook as Artifact

```yaml
artifacts:
  # AI agent analyses policy and generates a runbook
  generated_runbook:
    from: policy_document
    transform:
      type: policy_to_runbook_agent
    schema: runbook_definition  # Output is a runbook

  # Execute the generated runbook as a child
  compliance_results:
    from: generated_runbook
    execute: child  # Directive: execute input as child runbook
```

### Safeguards

```yaml
compliance_results:
  from: generated_runbook
  execute:
    mode: child
    max_depth: 3      # Prevent infinite recursion
    timeout: 3600     # Child execution timeout (seconds)
    cost_limit: 50    # LLM cost cap
```

### Scoped ArtifactStore

Child runbooks use a **scoped** artifact store - they can read parent artifacts but write to their own namespace:

```
Parent Store: { policy_document, generated_runbook }
                         ↓ (read access inherited)
Child Store:  { [parent readable], internal_step_1, internal_step_2 }
                         ↓ (output promoted to parent)
Parent Store: { policy_document, generated_runbook, compliance_results }
```

**Behaviour:**
- Child can read any parent artifact (inherited context)
- Child writes to its own namespace (no collision risk)
- Specified outputs promoted to parent on completion
- Child store disposed after execution

```python
class ScopedArtifactStore:
    def __init__(self, parent: ArtifactStore | None = None):
        self._parent = parent
        self._local: dict[str, Message] = {}

    def get(self, artifact_id: str) -> Message:
        if artifact_id in self._local:
            return self._local[artifact_id]
        if self._parent:
            return self._parent.get(artifact_id)
        raise ArtifactNotFoundError(artifact_id)

    def save(self, artifact_id: str, message: Message) -> None:
        self._local[artifact_id] = message  # Always local
```

## Benefits

1. **Simpler mental model** - Artifacts in, artifacts out
2. **Self-documenting** - DAG visible in structure
3. **Natural reuse** - Artifacts are addressable by ID
4. **Parallel by default** - Independent branches run concurrently
5. **Extensible** - New transform types slot in cleanly
6. **Less boilerplate** - No separate connector/analyser/execution sections
7. **Composable** - Runbooks can produce and execute child runbooks

## Related Documents

- [DAG Orchestration Layer](./dag-orchestration-layer.md) - Execution engine
- [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md) - Service injection
- [Dynamic and Agentic Workflows](./dynamic-and-agentic-workflows.md) - Future evolution
