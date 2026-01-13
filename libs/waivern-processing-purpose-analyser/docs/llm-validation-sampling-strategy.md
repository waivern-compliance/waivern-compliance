# LLM Validation Sampling Strategy Architecture

This document explains the purpose-based sampling strategy for LLM validation in the Processing Purpose Analyser.

## Overview

The sampling strategy **reduces LLM validation costs by 97-99%** by validating representative samples from each purpose group rather than every individual finding. When a codebase produces thousands of findings, this approach makes LLM validation economically viable while maintaining compliance accuracy.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WITHOUT SAMPLING                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│   13,974 findings ──────► LLM validates ALL ──────► ~$30+ per run           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          WITH SAMPLING                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│   13,974 findings ──► Sample 3 per purpose (81 total) ──► ~$0.50 per run    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Design Philosophy

**Purpose-level validation is sufficient for compliance analysis.**

For GDPR and similar regulations, what matters is whether a processing purpose exists in the codebase - not how many times a pattern matched. If "Payment Processing" appears 150 times, validating 3 representative samples tells us whether the purpose is legitimate.

This enables a two-layer architecture:

| Layer                | Cost Model               | Responsibility                           |
| -------------------- | ------------------------ | ---------------------------------------- |
| **Technical Layer**  | Fixed (sampling)         | Detect purposes, filter false positives  |
| **Compliance Layer** | Variable (per framework) | Map purposes to legal bases, assess risk |

## Information Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PATTERN MATCHING PHASE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Source Code ──────► Pattern Matcher ──────► All Findings (13,974)         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GROUPING PHASE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   All Findings ──────► Group by Purpose ──────► Purpose Groups              │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Purpose Groups:                                                  │      │
│   │   "Payment Processing"     → 150 findings                        │      │
│   │   "Customer Service"       → 89 findings                         │      │
│   │   "Documentation Example"  → 45 findings                         │      │
│   │   "Analytics Tracking"     → 234 findings                        │      │
│   │   ... (27 purposes total)                                        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SAMPLING PHASE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   For each Purpose Group:                                                   │
│     - If findings >= samples_per_purpose: randomly pick N samples.          │
│     - If findings < samples_per_purpose: use all findings as samples        │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Sampled Findings:                                                │      │
│   │   "Payment Processing"     → 3 samples (from 150)                │      │
│   │   "Customer Service"       → 3 samples (from 89)                 │      │
│   │   "Documentation Example"  → 3 samples (from 45)                 │      │
│   │   "Analytics Tracking"     → 3 samples (from 234)                │      │
│   │   ... (81 total samples from 27 purposes)                        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LLM VALIDATION PHASE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Prompt to LLM:                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ "Validate these 81 findings. Return ONLY the finding IDs that    │      │
│   │  are FALSE_POSITIVE. If a finding is TRUE_POSITIVE, do not       │      │
│   │  include it in your response."                                   │      │
│   │                                                                  │      │
│   │  Finding [abc-123]: Purpose="Payment Processing", Evidence=...   │      │
│   │  Finding [def-456]: Purpose="Documentation Example", Evidence=...│      │
│   │  ...                                                             │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   LLM Response (only FALSE_POSITIVEs returned to save output tokens):       │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ {                                                                │      │
│   │   "false_positives": [                                           │      │
│   │     {"finding_id": "doc-001", "reasoning": "Just an example"},   │      │
│   │     {"finding_id": "doc-002", "reasoning": "Tutorial code"},     │      │
│   │     {"finding_id": "doc-003", "reasoning": "Comment only"},      │      │
│   │     {"finding_id": "test-001", "reasoning": "Test fixture"},     │      │
│   │     {"finding_id": "test-002", "reasoning": "Mock data"}         │      │
│   │   ]                                                              │      │
│   │ }                                                                │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DECISION PHASE                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   For each Purpose Group, evaluate sampled findings:                        │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE A: ALL samples are FALSE_POSITIVE                              │   │
│   │ ─────────────────────────────────────────                           │   │
│   │   "Documentation Example" (3 samples):                              │   │
│   │     - doc-001: FALSE_POSITIVE ✗                                     │   │
│   │     - doc-002: FALSE_POSITIVE ✗                                     │   │
│   │     - doc-003: FALSE_POSITIVE ✗                                     │   │
│   │                                                                     │   │
│   │   ACTION: Remove ENTIRE purpose group (all 45 findings)             │   │
│   │           Flag for human review                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE B: SOME samples are FALSE_POSITIVE                             │   │
│   │ ─────────────────────────────────────────                           │   │
│   │   "Test Data Processing" (3 samples):                               │   │
│   │     - test-001: FALSE_POSITIVE ✗  → Remove this finding             │   │
│   │     - test-002: FALSE_POSITIVE ✗  → Remove this finding             │   │
│   │     - test-003: TRUE_POSITIVE ✓   → Keep, mark validated            │   │
│   │                                                                     │   │
│   │   ACTION: Keep purpose group (at least one TRUE_POSITIVE exists)    │   │
│   │           Remove only the FALSE_POSITIVE samples                    │   │
│   │           Keep non-sampled findings (by inference)                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE C: NO samples are FALSE_POSITIVE (not in LLM response)         │   │
│   │ ─────────────────────────────────────────                           │   │
│   │   "Payment Processing" (3 samples):                                 │   │
│   │     - pay-001: TRUE_POSITIVE ✓  → Keep, mark validated              │   │
│   │     - pay-002: TRUE_POSITIVE ✓  → Keep, mark validated              │   │
│   │     - pay-003: TRUE_POSITIVE ✓  → Keep, mark validated              │   │
│   │                                                                     │   │
│   │   ACTION: Keep entire purpose group                                 │   │
│   │           Mark sampled findings as validated                        │   │
│   │           Keep non-sampled findings (by inference, NOT validated)   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT PHASE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Final Findings List:                                                      │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ [                                                                │      │
│   │   {                                                              │      │
│   │     "id": "pay-001",                                             │      │
│   │     "purpose": "Payment Processing",                             │      │
│   │     "metadata": {                                                │      │
│   │       "context": { "processing_purpose_llm_validated": true }    │      │
│   │     }                              ← Sampled & validated         │      │
│   │   },                                                             │      │
│   │   {                                                              │      │
│   │     "id": "pay-004",                                             │      │
│   │     "purpose": "Payment Processing",                             │      │
│   │     "metadata": { }                ← Kept by inference           │      │
│   │   },                                                             │      │
│   │   ...                                                            │      │
│   │ ]                                                                │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Decision Logic

### Purpose Validity Rule

A purpose is considered **valid** if ANY of its samples is TRUE_POSITIVE:

```
Purpose "Payment Processing" with 3 samples:
  - Sample 1: TRUE_POSITIVE  → Purpose is VALID
  - Sample 2: FALSE_POSITIVE → This specific finding removed
  - Sample 3: TRUE_POSITIVE  → Purpose is VALID

Result: Keep ALL non-sampled findings in this purpose
        Remove only Sample 2 (the FALSE_POSITIVE)
        Mark Samples 1 and 3 as processing_purpose_llm_validated
```

Only remove the **entire purpose group** when ALL samples are FALSE_POSITIVE. This is conservative — if even one instance is legitimate, the purpose exists in the codebase.

### Validation Marking Rule

Only sampled findings that are TRUE_POSITIVE get marked as `processing_purpose_llm_validated: true`:

```
Purpose "Payment Processing" (150 findings, 3 sampled):
  - 3 sampled findings → processing_purpose_llm_validated: true (if TRUE_POSITIVE)
  - 147 other findings → no validation mark (kept by inference)
```

- We're truthful about what was actually checked
- Auditors can see "3 directly validated, 147 inferred"
- No false claims of validation coverage

## Detailed Logic Specification

### Step 1: Pattern Matching (Existing)

```
INPUT:  Source code files
OUTPUT: All findings (list of ProcessingPurposeFindingModel)
        Each finding has: id, purpose, evidence, matched_patterns, metadata
```

### Step 2: Group by Purpose

```
INPUT:  All findings
OUTPUT: Dictionary[purpose_name -> list[finding]]

LOGIC:
  for each finding in all_findings:
    purpose = finding.purpose
    groups[purpose].append(finding)
```

### Step 3: Sample Selection

```
INPUT:  Purpose groups, samples_per_purpose (default: 3)
OUTPUT: sampled_findings (list)

LOGIC:
  sampled_findings = []

  for purpose, findings in groups.items():
    n = min(len(findings), samples_per_purpose)
    samples = random.sample(findings, n)
    sampled_findings.extend(samples)
```

### Step 4: LLM Validation

```
INPUT:  sampled_findings (81 findings)
OUTPUT: false_positive_ids with reasoning

PROMPT STRUCTURE:
  "Validate these findings. Return ONLY FALSE_POSITIVE finding IDs.
   If TRUE_POSITIVE, do not include in response.

   Finding [id-1]: Purpose=X, Evidence=Y, Patterns=Z
   Finding [id-2]: Purpose=X, Evidence=Y, Patterns=Z
   ..."

RESPONSE SCHEMA:
  {
    "false_positives": [
      {"finding_id": "...", "reasoning": "..."},
      ...
    ]
  }
```

### Step 5: Apply Validation Results

```
INPUT:  All findings, sampled_findings, LLM response (false_positives)
OUTPUT: Final findings list, validation_summary

LOGIC:
  false_positive_ids = {fp.finding_id for fp in response.false_positives}
  sampled_ids = {f.id for f in sampled_findings}

  for purpose, findings in groups.items():
    purpose_sample_ids = {f.id for f in findings if f.id in sampled_ids}
    purpose_fp_ids = purpose_sample_ids & false_positive_ids

    if purpose_fp_ids == purpose_sample_ids:
      # CASE A: ALL samples FALSE_POSITIVE
      # Remove entire purpose group, flag for review
      removed_purposes.append({
        "purpose": purpose,
        "findings_removed": len(findings),
        "reasons": [get_reasoning(id) for id in purpose_fp_ids]
      })

    else:
      # CASE B or C: At least one TRUE_POSITIVE
      for finding in findings:
        if finding.id in false_positive_ids:
          # Remove this specific FALSE_POSITIVE sample
          continue
        elif finding.id in sampled_ids:
          # TRUE_POSITIVE sample - mark as validated
          finding.metadata.context["processing_purpose_llm_validated"] = True
          final_findings.append(finding)
        else:
          # Non-sampled finding - keep by inference (no validation mark)
          final_findings.append(finding)
```

### Step 6: Generate Summary

Include in validation_summary:

- Original findings breakdown by purpose (from Step 2)
- Sampling statistics
- Per-purpose validation results
- Removed purposes with reasons (for human review)
- Honest counts: directly_validated vs kept_by_inference

## Output Schema

Extends the existing output with validation verdicts:

```yaml
summary:
  total_findings: 13927 # After validation
  purposes_identified: 26 # After validation
  purpose_categories: { ... } # Existing

  # NEW: per-purpose breakdown (only validated purposes)
  purposes:
    - purpose: "Payment Processing"
      findings_count: 150
    - purpose: "Customer Service"
      findings_count: 89
    # ... (validated purposes only)

analysis_metadata:
  llm_validation_enabled: true
  # ... existing fields

  validation_summary:
    strategy: "purpose_sampling"
    samples_per_purpose: 3
    samples_validated: 81

  purposes_removed: # NEW: flagged for human review
    - purpose: "Documentation Example"
      reason: "All sampled findings are false positives"
      require_review: true
```

## Configuration

```python
LLMValidationConfig(
    enable_llm_validation=True,
    validation_strategy="auto",         # "auto" | "by_purpose" | "by_source"
    sample_size=3,                      # Number of samples per group
)
```

| Parameter             | Default  | Description                                                              |
| --------------------- | -------- | ------------------------------------------------------------------------ |
| `validation_strategy` | `"auto"` | How to group findings: `"auto"`, `"by_purpose"`, or `"by_source"`        |
| `sample_size`         | `3`      | Number of samples per group                                              |

## Error Handling

| Scenario                       | Behaviour                                                                |
| ------------------------------ | ------------------------------------------------------------------------ |
| LLM call fails                 | Keep all findings in affected batch, mark `all_batches_succeeded: false` |
| LLM returns unknown finding ID | Log warning, ignore the unknown ID                                       |
| Purpose group has < N findings | Use all findings as samples (no random selection)                        |
| Empty response from LLM        | All samples treated as TRUE_POSITIVE                                     |

## Cost Analysis

| Metric                  | Without Sampling | With Sampling (3 per purpose) |
| ----------------------- | ---------------- | ----------------------------- |
| Findings validated      | 13,974           | 81                            |
| Estimated output tokens | ~2.8M            | ~16K                          |
| Estimated cost per run  | ~$30             | ~$0.50                        |
| **Savings**             | -                | **98.3%**                     |

## Future Extensions

| Current               | Future Possibilities                                    |
| --------------------- | ------------------------------------------------------- |
| Random sampling       | Stratified sampling (by file, by pattern)               |
| Fixed sample size     | Adaptive sampling (more samples for uncertain purposes) |
| Purpose-only grouping | Purpose + pattern grouping for finer granularity        |
| Single LLM call       | Parallel batch validation for large sample sets         |

## Related Documentation

- [LLM Validation Strategy](../../waivern-analysers-shared/src/waivern_analysers_shared/llm_validation/strategy.py) - Base validation infrastructure
- [Batched Files Strategy](../../waivern-analysers-shared/src/waivern_analysers_shared/llm_validation/batched_files_strategy.py) - Token-aware batching
