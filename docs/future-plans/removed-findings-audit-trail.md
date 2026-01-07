# Removed Findings Audit Trail

- **Status:** Design Proposal
- **Last Updated:** 2025-01-07
- **Related:** [Execution Persistence](./execution-persistence.md), [Export Architecture](./export-architecture.md)

## Problem

When LLM validation removes false positives (e.g., 48 → 2 findings), the removed findings are logged but then discarded. This information is valuable for:

- **Auditing** - Understanding what was filtered and why
- **Performance review** - Evaluating LLM validation effectiveness
- **Debugging** - Investigating why legitimate findings were removed
- **Compliance** - Demonstrating due diligence in data classification

Currently:
- Removed findings are logged at INFO level with identifier, confidence, and reasoning
- Only aggregate statistics appear in output (`false_positives_removed: 46`)
- Full details are lost after the validation process completes

## Solution

**Capture always, store separately** - validation layer captures all removal details, orchestration persists to artifact store, main output stays lean with just a reference.

```
┌─────────────────────────────────────────────────────────────────┐
│                     LLM Validation                              │
│                                                                 │
│  Findings → Validate → (Kept Findings, Removed Finding Records) │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Analyser                                    │
│                                                                 │
│  - Main output: validated findings + summary                    │
│  - Side output: removed findings for storage                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestration/DAGExecutor                   │
│                                                                 │
│  - Store removed findings to ArtifactStore                      │
│  - Add artifact reference to main output                        │
└─────────────────────────────────────────────────────────────────┘
```

## Design

### Removed Finding Record Model

```python
class RemovedFindingRecord(BaseModel):
    """Record of a finding removed during LLM validation."""

    finding_identifier: str  # Human-readable identifier
    original_finding: dict[str, Any]  # Complete finding data
    validation_result: str  # "FALSE_POSITIVE", etc.
    confidence: float  # LLM confidence (0-1)
    reasoning: str  # LLM explanation
    recommended_action: str  # "discard", etc.
    removal_timestamp: datetime
```

### Output Structure

**Main output (lean):**
```json
{
  "findings": [...],
  "validation_summary": {
    "original_findings_count": 48,
    "validated_findings_count": 2,
    "false_positives_removed": 46,
    "removed_findings_artifact_id": "run_abc123_removed_findings"
  }
}
```

**Separate artifact (full audit trail):**
```json
{
  "artifact_id": "run_abc123_removed_findings",
  "analyser": "personal_data_analyser",
  "removed_findings": [
    {
      "finding_identifier": "biometric - voice",
      "original_finding": {
        "category": "biometric",
        "evidence": [...],
        "matched_patterns": ["voice"]
      },
      "validation_result": "FALSE_POSITIVE",
      "confidence": 0.99,
      "reasoning": "Event method field with value 'voice', not biometric data"
    }
  ]
}
```

### Artifact Store Integration

| Artifact | Location | Content |
|----------|----------|---------|
| Main output | `{run_id}/personal_data_indicators.json` | Validated findings |
| Audit artifact | `{run_id}/personal_data_removed_findings.json` | Removed finding records |

## Implementation Layers

### Layer 1: Validation Strategy (waivern-analysers-shared)

```python
# llm_validation/strategy.py

def _filter_findings_by_validation_results(
    self, findings_batch, validation_results
) -> tuple[list[T], list[RemovedFindingRecord]]:
    """Returns (kept_findings, removed_records)"""

# New abstract method
@abstractmethod
def convert_finding_to_dict(self, finding: T) -> dict[str, Any]:
    """Convert finding to dict for audit record."""
```

### Layer 2: Analyser Output

```python
# Analyser returns both validated findings and removed records
class AnalyserOutput:
    message: Message  # Main output with findings
    removed_findings: list[RemovedFindingRecord]  # For separate storage
```

### Layer 3: Orchestration

```python
# DAGExecutor handles storage
def _execute_analyser(self, analyser, inputs, output_schema):
    result = analyser.process(inputs, output_schema)

    if result.removed_findings:
        artifact_id = self._store_removed_findings(
            run_id, analyser.get_name(), result.removed_findings
        )
        # Add reference to main output
        result.message.content["validation_summary"]["removed_findings_artifact_id"] = artifact_id
```

## Benefits

- **Single run** - No need to run twice with different configs
- **Clean output** - Main results stay lean and focused
- **Full audit trail** - All removal details persisted
- **On-demand access** - Query artifact store when needed
- **Backward compatible** - Optional enhancement, existing pipelines unaffected

## Dependencies

- Requires [Execution Persistence](./execution-persistence.md) for artifact store with run IDs
- Integrates with [Export Architecture](./export-architecture.md) for audit report generation

## Implementation Path

1. Add `RemovedFindingRecord` model to `waivern-analysers-shared/llm_validation/models.py`
2. Update `LLMValidationStrategy` to capture and return removed findings
3. Update analyser-specific strategies to implement `convert_finding_to_dict()`
4. Define analyser output structure that includes removed findings
5. Update DAGExecutor to store removed findings as separate artifact
6. Add `removed_findings_artifact_id` field to validation summary schemas
7. Implement `wct inspect --removed-findings {run_id}` command for querying

## Future Enhancements

- **Removed findings report** - Dedicated exporter for audit reports
- **Validation effectiveness dashboard** - Aggregate statistics across runs
- **Re-validation** - Ability to re-run validation on stored removed findings with different settings
