# ADR-0003: Fan-In Handling and Transformer Pattern for Multi-Schema Inputs

## Status

Accepted (2025-11)

## Context

### Fan-In Scenarios

In artifact-centric orchestration, a derived artifact can have multiple input artifacts (fan-in):

```yaml
artifacts:
  source_a:
    source:
      type: filesystem
      properties: { path: "/data/a" }

  source_b:
    source:
      type: filesystem
      properties: { path: "/data/b" }

  combined:
    inputs: [source_a, source_b]  # Fan-in
    transform:
      type: some_analyser
```

### The Problem

When multiple artifacts feed into one downstream artifact, we need to answer:

1. **Same schema case**: What if `source_a` and `source_b` produce the same schema (e.g., both `standard_input/1.0.0`)? How are they combined?

2. **Different schema case**: What if `source_a` produces `database_schema/1.0.0` and `source_b` produces `source_code/1.0.0`? How should the downstream analyser handle different types?

3. **Merge semantics**: What merge strategies should be supported for combining multiple inputs?

### Design Requirements

- Keep analysers simple (single schema in, single schema out)
- Support legitimate use cases for combining multiple data sources
- Maintain type safety through schema validation
- Enable future extensibility without over-complicating current design

---

## Alternative Approaches Considered

### 1. Analysers Accept list[Message] (Multiple Schemas)

**How it works:** Analysers would declare they accept multiple input types and receive a list of messages with potentially different schemas.

```python
class CombinedAnalyser(Analyser):
    def get_supported_input_schemas(self) -> list[Schema]:
        return [Schema("database_schema", "1.0.0"), Schema("source_code", "1.0.0")]

    def process_data(self, messages: list[Message]) -> Message:
        # Handle different message types
        for msg in messages:
            if msg.schema.name == "database_schema":
                # Handle database data
            elif msg.schema.name == "source_code":
                # Handle source code
```

**Pros:**
- Maximum flexibility for analysers
- Can handle arbitrary input combinations
- No need for explicit transformers

**Cons:**
- **Breaks pure function model**: Analysers become complex dispatch systems
- **Coupling**: Analyser must know about all possible input types
- **Testing burden**: Must test all permutations of input types
- **Violates single responsibility**: One analyser doing too much
- **Schema validation complexity**: How do we validate "accepts any of these"?
- **Industry anti-pattern**: Leads to "god class" analysers

**Verdict:** ❌ Over-complicates analysers

---

### 2. Executor as Message Dispatcher

**How it works:** Executor routes different schema types to different analysers transparently.

```yaml
combined:
  inputs: [source_a, source_b]
  transform:
    database_schema: database_analyser
    source_code: source_code_analyser
```

**Pros:**
- Keeps analysers simple
- Declarative routing

**Cons:**
- **Configuration complexity**: Every fan-in needs routing rules
- **Hidden behaviour**: Not clear what happens to each input
- **Ordering issues**: Which analyser runs first? How are results combined?
- **Implicit coupling**: Still need to combine results somewhere

**Verdict:** ❌ Shifts complexity rather than solving it

---

### 3. Transformers + Complex Schemas (Chosen)

**How it works:** Use explicit transformer components to combine different schemas into a new complex schema. Analysers remain pure functions.

**Same schema fan-in:**
```yaml
combined:
  inputs: [source_a, source_b]  # Both produce standard_input/1.0.0
  transform:
    type: personal_data_analyser  # Receives concatenated inputs
```

**Different schema fan-in:**
```yaml
# Step 1: Transformer combines different schemas
correlation_input:
  inputs: [database_schema, source_code_findings]
  transform:
    type: correlation_transformer  # Outputs correlation_input/1.0.0
  output_schema: "correlation_input/1.0.0"

# Step 2: Analyser processes unified schema
correlation_findings:
  inputs: correlation_input
  transform:
    type: correlation_analyser  # Pure function: correlation_input → correlation_finding
```

**Pros:**
- **Pure functions**: Analysers remain simple (one schema in, one schema out)
- **Explicit composition**: Transformers clearly declare input/output schemas
- **Type safety**: Schema validation at every step
- **Testable**: Each component has clear contract
- **Extensible**: Add new complex schemas without changing analysers
- **Industry pattern**: Follows ETL/data pipeline best practices

**Cons:**
- Requires explicit transformer for multi-schema combination
- One extra artifact definition for complex fan-in cases
- Learning curve: users must understand transformer pattern

**Verdict:** ✅ Best balance of simplicity and extensibility

---

## Decision

We will implement the **Transformers + Complex Schemas** pattern in two phases:

- **Phase 1 (Current)**: Same-schema fan-in only. Different-schema fan-in raises `SchemaCompatibilityError`.
- **Phase 2 (Future)**: Introduce Transformers as a new component type to enable different-schema fan-in.

### 1. Fan-In Schema Validation Rules

**Same schema requirement**: All inputs to a fan-in must have the same schema (name AND version):

```python
# Planner validates at plan time
def _validate_fan_in_schemas(self, inputs: list[str], resolved: dict) -> Schema:
    schemas = [resolved[ref][1] for ref in inputs]  # Output schemas
    first = schemas[0]

    for schema in schemas[1:]:
        if schema.name != first.name or schema.version != first.version:
            raise SchemaCompatibilityError(
                f"Fan-in requires same schema. Got {first.name}/{first.version} "
                f"and {schema.name}/{schema.version}"
            )

    return first
```

**Rationale**: Requiring same version ensures downstream components can safely process all inputs with a single code path.

### 2. Merge Strategy (Phase 2)

Only `"concatenate"` merge strategy is currently supported:

```python
class ArtifactDefinition(BaseModel):
    merge: Literal["concatenate"] = "concatenate"
```

**Concatenate semantics**:
- Executor combines all input messages into a single message
- Combined message contains list of all input data
- Downstream analyser processes the combined data

**Future extensibility**: Additional merge strategies may be added if concrete use cases arise. The `Literal` type can be expanded (e.g., `Literal["concatenate", "zip"]`) without breaking existing runbooks.

### 3. Transformer Pattern for Different Schemas (Phase 2)

**Note**: This section describes the planned Phase 2 implementation. In Phase 1, different-schema fan-in is not supported and will raise `SchemaCompatibilityError`.

When combining artifacts with different schemas, use explicit transformer:

```yaml
artifacts:
  # Different sources
  database_schema:
    source: { type: mysql }

  source_code_findings:
    inputs: source_code
    transform: { type: personal_data_analyser }

  # Transformer combines into complex schema
  correlation_input:
    inputs: [database_schema, source_code_findings]
    transform:
      type: correlation_transformer  # Phase 2: Transformer component
    output_schema: "correlation_input/1.0.0"

  # Analyser processes unified schema
  correlation_findings:
    inputs: correlation_input
    transform:
      type: correlation_analyser
```

### 4. Schema as Contract

The schema is the contract. Complex inputs are encapsulated in complex schemas:

```json
{
  "name": "correlation_input",
  "version": "1.0.0",
  "properties": {
    "database_schemas": { "type": "array", "items": { "$ref": "database_schema" } },
    "code_findings": { "type": "array", "items": { "$ref": "personal_data_finding" } }
  }
}
```

Analysers only see the unified schema - they don't know or care how it was composed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Fan-In Cases                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Case 1: Same Schema (Phase 1 - Supported)                           │
│  ┌──────────┐                                                        │
│  │ source_a │──┐                                                     │
│  └──────────┘  │    ┌────────────┐    ┌────────────┐                │
│                ├───→│  Executor  │───→│  Analyser  │                │
│  ┌──────────┐  │    │ (combine)  │    │ (process)  │                │
│  │ source_b │──┘    └────────────┘    └────────────┘                │
│  └──────────┘                                                        │
│  Both: standard_input/1.0.0                                          │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Case 2: Different Schemas (Phase 2 - Transformer Required)          │
│  ┌──────────┐                                                        │
│  │ db_data  │──┐    ┌─────────────┐    ┌────────────────────┐       │
│  └──────────┘  │    │ Transformer │    │ complex_input/1.0.0│       │
│                ├───→│  (combine)  │───→│   (new schema)     │──→... │
│  ┌──────────┐  │    └─────────────┘    └────────────────────┘       │
│  │ findings │──┘                                                     │
│  └──────────┘                                                        │
│  Different: database_schema vs personal_data_finding                 │
│                                                                      │
│  Note: In Phase 1, this raises SchemaCompatibilityError              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Consequences

### Positive ✅

**Simple Analysers:**
- Analysers remain pure functions (one schema in, one schema out)
- Easy to test, reason about, and compose
- No complex dispatch logic inside analysers

**Type Safety:**
- Schema validation at plan time catches incompatibilities early
- Each step has clear input/output contract
- No runtime surprises from mismatched schemas

**Explicit Composition:**
- Transformers make data combination explicit and visible
- Clear audit trail of how data flows
- Easy to understand runbook intent

**Extensibility:**
- Add new complex schemas without changing existing analysers
- Transformers can be reused across runbooks
- Third parties can create domain-specific transformers

**Industry Alignment:**
- Follows ETL/data pipeline best practices
- Similar to Apache Beam, Spark pipeline patterns
- Data engineers will find pattern familiar

### Trade-offs ⚠️

**Phase 1 Limitation:**
- Different-schema fan-in not supported until Phase 2
- Users needing multi-schema combination must wait or use workarounds

**Phase 2 Trade-offs (when Transformers are implemented):**
- Need explicit transformer artifact when combining different schemas
- More verbose runbook for complex scenarios
- Learning curve for transformer pattern
- Third component type adds some framework complexity

**No Ad-Hoc Schema Mixing:**
- Cannot throw arbitrary schemas at an analyser
- Must think about data composition upfront
- Requires schema design discipline

### Neutral ➡️

**Pattern Follows Data Pipeline Standards:**
- ETL tools use similar transform-then-process pattern
- Well-documented approach with known trade-offs
- Clear migration path for data engineers

---

## Implementation Notes

### Planner Changes

1. Add schema compatibility validation for fan-in:
   ```python
   def _validate_fan_in_compatible(self, schemas: list[Schema]) -> None:
       """Validate all fan-in inputs have same schema name and version."""
   ```

2. Raise `SchemaCompatibilityError` for incompatible fan-in

### Model Changes

1. Update `ArtifactDefinition.merge` to only allow `"concatenate"`:
   ```python
   merge: Literal["concatenate"] = "concatenate"
   ```

### Phase 2: Transformer Components

Transformers will be introduced as a **new component type** alongside Connectors and Analysers:

| Component | Input | Output | Purpose |
|-----------|-------|--------|---------|
| Connector | External source | Single schema | Extract data |
| Analyser | Single schema | Single schema | Analyse/enrich (pure function) |
| Transformer | Multiple schemas | Single schema | Combine/reshape data |

**Implementation plan:**
- New entry point group: `waivern.transformers`
- New `Transformer` protocol/ABC with `get_input_schemas()` returning multiple schemas
- Planner validates transformer input schemas match upstream outputs
- Executor handles transformer invocation similar to analysers

**Why a separate component type (not specialized analyser):**
- Keeps analysers as pure functions (single schema in, single schema out)
- Clear mental model: each component type has one job
- Independent evolution: transformers can have different capabilities without polluting analyser interface
- Discoverable: AI agents can query "what transformers can combine these schemas?"

---

## Related Documents

- **Architecture:** [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md) - Execution model
- **ADR-0002:** [Dependency Injection](0002-dependency-injection-for-service-management.md) - Component factory pattern

---

## References

- **Apache Beam Transforms:** https://beam.apache.org/documentation/programming-guide/#transforms
- **Schema Evolution Best Practices:** https://docs.confluent.io/platform/current/schema-registry/avro.html
- **ETL Pipeline Patterns:** Standard data engineering practices
