# waivern-gdpr-data-subject-classifier

GDPR data subject classifier for the Waivern Compliance Framework.

## Overview

This package provides the `GDPRDataSubjectClassifier` which enriches generic data subject indicators with GDPR-specific classifications. It transforms `data_subject_indicator/1.0.0` findings into `gdpr_data_subject/1.0.0` output.

## Input/Output

| Aspect            | Value                                    |
| ----------------- | ---------------------------------------- |
| **Input Schema**  | `data_subject_indicator/1.0.0`           |
| **Output Schema** | `gdpr_data_subject/1.0.0`                |
| **Ruleset**       | `gdpr_data_subject_classification/1.0.0` |
| **Framework**     | GDPR                                     |

## Features

- Maps indicator categories to GDPR data subject categories
- Enriches findings with GDPR article references
- Provides typical lawful bases for processing
- Detects risk modifiers (e.g., minors, vulnerable individuals) from evidence
- Optional LLM validation for semantic risk modifier detection

## Risk Modifier Detection

Risk modifiers indicate special GDPR considerations:

| Modifier | GDPR Reference | Meaning |
|----------|----------------|---------|
| `minor` | Article 8 | Data subject under 16 years old |
| `vulnerable_individual` | Recital 75 | Elderly, disabled, or otherwise vulnerable |

### Detection Methods

**Regex (default):** Pattern matching on evidence text. Fast but may produce false positives (e.g., "minor changes" flagged as involving a child).

**LLM validation:** Semantic analysis understands context. Correctly identifies:
- "8-year-old patient" → `minor` (age reference)
- "minor changes to the record" → No modifier (means "small")
- "elderly patient with dementia" → `vulnerable_individual`

Enable LLM validation in your runbook:

```yaml
gdpr_findings:
  inputs: indicators
  process:
    type: gdpr_data_subject_classifier
    properties:
      llm_validation:
        enable_llm_validation: true
  output: true
```

## Usage

The classifier is typically used in a pipeline after `DataSubjectAnalyser`:

```yaml
artifacts:
  indicators:
    inputs: data_content
    process:
      type: data_subject

  gdpr_findings:
    inputs: indicators
    process:
      type: gdpr_data_subject_classifier
    output: true
```

## Output Schema

The classifier outputs `gdpr_data_subject` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
  - Each finding may include `require_review` when human review is needed
- `summary`: Statistics including:
  - `total_findings`: Total classified findings
  - `categories_identified`: Unique data subject categories found
  - `high_risk_count`: Findings with risk modifiers (minors, vulnerable individuals)
  - `requires_review_count`: Findings needing human review
- `analysis_metadata`: Metadata about the classification process
