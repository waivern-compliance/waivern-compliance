# Phase 2: Transformers - Requirements Memo

- **Status:** Planned (design after Phase 1 completion)
- **Prerequisites:** Phase 1 complete
- **Reference:** [ADR-0003](../../../adr/0003-fan-in-handling-and-transformer-pattern.md)

## Problem

Phase 1 only supports same-schema fan-in. Users needing to combine artifacts with different schemas (e.g., database schema + source code findings) have no solution.

## Solution

Introduce **Transformer** as a third component type:

| Component | Input | Output | Purpose |
|-----------|-------|--------|---------|
| Connector | External source | Single schema | Extract data |
| Analyser | Single schema | Single schema | Analyse/enrich |
| **Transformer** | **Multiple schemas** | Single schema | Combine/reshape |

## Key Requirements

1. New entry point group: `waivern.transformers`
2. Transformer declares `get_input_schemas()` returning multiple schemas
3. Planner validates all upstream outputs match transformer's declared inputs
4. Executor passes multiple messages to transformer (one per input artifact)
5. Transformer produces single output message with new schema

## Example Usage

```yaml
artifacts:
  db_schema:
    source: { type: mysql }

  code_findings:
    inputs: source_code
    transform: { type: personal_data_analyser }

  # Transformer combines different schemas
  correlation_input:
    inputs: [db_schema, code_findings]
    transform: { type: correlation_transformer }

  # Analyser processes unified schema
  correlation_findings:
    inputs: correlation_input
    transform: { type: correlation_analyser }
```

## Out of Scope

- Detailed Transformer protocol design
- Implementation details
- Testing strategy

These will be defined in full design document after Phase 1.
