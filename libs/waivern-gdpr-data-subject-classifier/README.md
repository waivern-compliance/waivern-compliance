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
