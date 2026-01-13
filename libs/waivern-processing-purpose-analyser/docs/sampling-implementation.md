# Sampling Implementation

Simple purpose-based sampling to reduce LLM validation costs.

## Overview

Sample 3 findings per purpose instead of validating all. This reduces costs by ~98% while maintaining accuracy.

```
13,974 findings ──► Sample 3 per purpose (81 total) ──► ~$0.50 per run
```

## Flow

```
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  Pattern Matching  │────►│  Group by Purpose  │────►│  Sample 3 per group│
│  (13,974 findings) │     │  (27 purposes)     │     │  (81 samples)      │
└────────────────────┘     └────────────────────┘     └────────────────────┘
                                                               │
                                                               ▼
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  Final Output      │◄────│  Apply Results     │◄────│  LLM Validation    │
│  (validated)       │     │  to all findings   │     │  (samples only)    │
└────────────────────┘     └────────────────────┘     └────────────────────┘
```

## Decision Logic

| Scenario | Action |
|----------|--------|
| ALL samples FALSE_POSITIVE | Remove entire purpose group, flag for review |
| SOME samples FALSE_POSITIVE | Remove those samples, keep rest of group |
| NO samples FALSE_POSITIVE | Keep entire group, mark samples as validated |

## Output Schema

```yaml
summary:
  total_findings: 13927           # After validation
  purposes_identified: 26         # After validation
  purpose_categories: { ... }     # Existing

  purposes:                       # Per-purpose breakdown
    - purpose: "Payment Processing"
      findings_count: 150
    - purpose: "Customer Service"
      findings_count: 89

analysis_metadata:
  llm_validation_enabled: true

  validation_summary:
    strategy: "purpose_sampling"
    samples_per_purpose: 3
    samples_validated: 81

  purposes_removed:               # Flagged for human review
    - purpose: "Documentation Example"
      reason: "All sampled findings are false positives"
      require_review: true
```

## Finding Metadata

Sampled findings that pass validation get marked:

```json
{
  "metadata": {
    "context": {
      "processing_purpose_llm_validated": true
    }
  }
}
```

Non-sampled findings are kept by inference (no validation mark).

## Configuration

Hardcoded for now:
- `sampling_size = 3` per purpose group
- Random sampling within each group

## Related

- [LLM Validation Sampling Strategy](./llm-validation-sampling-strategy.md) - Detailed design reference
- [Generic Validation Strategies](../../waivern-analysers-shared/docs/future-plans/generic-validation-strategies.md) - Future refactoring plan
