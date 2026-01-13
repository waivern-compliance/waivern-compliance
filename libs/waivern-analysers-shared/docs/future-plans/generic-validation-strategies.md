# Generic Validation Strategies

Future design for making LLM validation strategies reusable across all analysers.

## Motivation

Current validation strategies are tightly coupled to specific analysers (e.g., `batch_by_files` assumes file-based sources, `sample_by_purpose` assumes processing purpose findings). This document outlines a generic design that allows any analyser to use any validation strategy.

## Layered Configuration

```python
LLMValidationConfig(
    grouping="by_concern",    # "none" | "by_source" | "by_concern"
    sampling_size=3,          # None = validate all, int = sample N per group
)
```

### Grouping Strategies

| Strategy | Description |
|----------|-------------|
| `none` | No grouping - batch findings by token limits only |
| `by_source` | Group findings by their origin (file, table, API endpoint, etc.) |
| `by_concern` | Group findings by compliance-relevant attribute (purpose, data type, etc.) |

### Sampling

| `sampling_size` | Behaviour |
|-----------------|-----------|
| `None` | Validate all findings in each group |
| `int` | Sample N findings per group, apply result to group |

### Layering Matrix

| Grouping | `sampling_size` | Behaviour |
|----------|-----------------|-----------|
| `none` | `None` | Plain batching (current default) |
| `none` | `3` | Ignored - sampling without grouping doesn't make sense |
| `by_source` | `None` | Group by source, validate all with source context |
| `by_source` | `3` | Group by source, sample 3 per source |
| `by_concern` | `None` | Group by concern, validate all |
| `by_concern` | `3` | Group by concern, sample 3 per group |

## Analyser-Provided Protocols

Each analyser implements these protocols to define what "source" and "concern" mean:

```python
class SourceProvider(Protocol):
    """Provides source content for validation context."""

    def get_source_content(self, source_id: str) -> str:
        """Return the content of the source (file content, table schema, etc.)."""
        ...

    def get_source_id(self, finding: Finding) -> str:
        """Extract source identifier from a finding."""
        ...


class ConcernProvider(Protocol):
    """Defines what the 'compliance concern' is for this analyser."""

    def get_concern(self, finding: Finding) -> str:
        """Extract the compliance concern from a finding."""
        ...
```

### Analyser Implementations

| Analyser | Source | Concern |
|----------|--------|---------|
| Processing Purpose | File path | `finding.purpose` |
| Personal Data | File path | `finding.data_category` |
| Data Subject | File path | `finding.subject_type` |
| Database (future) | Table name | `finding.purpose` |

## Benefits

1. **Generic strategies in `analyser-shared`** - No hardcoded assumptions about finding structure
2. **Analyser defines semantics** - Each analyser knows what its source and concern attributes are
3. **Composable** - Grouping and sampling are independent, layered when it makes sense
4. **Extensible** - New grouping strategies can be added without changing analysers

## Implementation Notes

- Strategy logic lives in `waivern-analysers-shared`
- Protocol implementations live in each analyser
- Strategies should gracefully handle missing providers (e.g., if analyser doesn't implement `ConcernProvider`, `by_concern` grouping falls back to `none`)

## Related Documentation

- [LLM Validation Sampling Strategy](../../../waivern-processing-purpose-analyser/docs/llm-validation-sampling-strategy.md) - Initial implementation for processing purpose analyser
