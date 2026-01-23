# waivern-gdpr-processing-purpose-classifier

GDPR processing purpose classifier for Waivern Compliance Framework.

## Overview

This classifier enriches processing purpose indicator findings with GDPR-specific classification information. It takes output from `ProcessingPurposeAnalyser` and adds:

- **Purpose Category**: Normalised GDPR purpose category (e.g., `analytics`, `operational`, `ai_and_ml`)
- **Article References**: Relevant GDPR article references
- **Typical Lawful Bases**: Typical Article 6 lawful bases for this processing
- **Sensitivity Indicators**: Whether the purpose is privacy-sensitive
- **DPIA Recommendations**: Data Protection Impact Assessment recommendation level

## Usage

### In a Runbook

```yaml
artifacts:
  # First, detect processing purposes
  processing_purposes:
    inputs: source_code
    process:
      type: processing_purpose
      properties:
        pattern_matching:
          ruleset: "local/processing_purposes/1.0.0"

  # Then, classify according to GDPR
  gdpr_processing_purposes:
    inputs: processing_purposes
    process:
      type: gdpr_processing_purpose_classifier
    output: true
```

### Programmatic Usage

```python
from waivern_gdpr_processing_purpose_classifier import GDPRProcessingPurposeClassifier
from waivern_core import Schema

classifier = GDPRProcessingPurposeClassifier()
output_schema = Schema("gdpr_processing_purpose", "1.0.0")

result = classifier.process([indicator_message], output_schema)
```

## Classification Categories

| GDPR Category               | Processing Purposes                                                           | Sensitive | DPIA         |
| --------------------------- | ----------------------------------------------------------------------------- | --------- | ------------ |
| `ai_and_ml`                 | AI and ML                                                                     | Yes       | Required     |
| `analytics`                 | Analytics, Session Recording, User Behaviour Tracking, A/B Testing, Profiling | Yes       | Recommended  |
| `marketing_and_advertising` | Advertising, Marketing, Personalisation                                       | Yes       | Recommended  |
| `operational`               | Authentication, Payment Processing, Communication, Content Delivery, etc.     | No        | Not Required |
| `security`                  | Security, Fraud Detection                                                     | No        | Not Required |

## Output Schema

The classifier outputs `gdpr_processing_purpose` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
- `summary`: Statistics including sensitive purpose counts and DPIA requirements
- `analysis_metadata`: Metadata about the classification process
