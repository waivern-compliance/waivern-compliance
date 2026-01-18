# waivern-data-subject-analyser

Data subject analyser for the Waivern Compliance Framework.

## Overview

This package provides the `DataSubjectAnalyser` which identifies data subjects (individuals or groups whose personal data is being processed) in content using pattern matching. It outputs generic `data_subject_indicator` findings that can be enriched by framework-specific classifiers.

## Input/Output

| Aspect            | Value                              |
| ----------------- | ---------------------------------- |
| **Input Schema**  | `standard_input/1.0.0`             |
| **Output Schema** | `data_subject_indicator/1.0.0`     |
| **Ruleset**       | `data_subject_indicator/1.0.0`     |

## Features

- Pattern-based data subject identification using rulesets
- Confidence scoring based on pattern matches
- Evidence extraction with surrounding context

## Usage

The analyser is typically used in a pipeline, often followed by a GDPR classifier:

```yaml
artifacts:
  data_content:
    source:
      type: filesystem
      properties:
        path: "./data"

  indicators:
    inputs: data_content
    process:
      type: data_subject

  # Optional: enrich with GDPR context
  gdpr_findings:
    inputs: indicators
    process:
      type: gdpr_data_subject_classifier
    output: true
```
