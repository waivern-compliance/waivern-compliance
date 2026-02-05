# waivern-gdpr-processing-purpose-classifier

GDPR processing purpose classifier for Waivern Compliance Framework.

## Overview

This classifier enriches processing purpose indicator findings with GDPR-specific classification information. It takes output from `ProcessingPurposeAnalyser` and adds:

- **Purpose Category**: Normalised GDPR purpose category (e.g., `analytics`, `operational`, `ai_and_ml`)
- **Article References**: Relevant GDPR article references
- **Typical Lawful Bases**: Typical Article 6 lawful bases for this processing
- **Sensitivity Indicators**: Whether the purpose is privacy-sensitive
- **DPIA Recommendations**: Data Protection Impact Assessment recommendation level
- **Review Requirements**: Whether human review is needed to determine actual purpose

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

| GDPR Category               | Processing Purposes                                                            | Sensitive | DPIA         |
| --------------------------- | ------------------------------------------------------------------------------ | --------- | ------------ |
| `ai_and_ml`                 | AI Model Training, AI Services, ML Processing                                  | Yes       | Required     |
| `analytics`                 | Behavioural Analysis, Personalisation, Third-Party Analytics                   | Yes       | Recommended  |
| `healthcare`                | Healthcare Practice Management, Medical Systems                                | Yes       | Required     |
| `marketing_and_advertising` | Consumer Marketing, Targeted Marketing, Third-Party Marketing                  | Yes       | Recommended  |
| `operational`               | Service Delivery, Payment Processing, Identity Management, Cloud Infrastructure | No        | Not Required |
| `security`                  | Security, Fraud Prevention, Abuse Detection                                    | No        | Not Required |
| `context_dependent`         | Technical mechanisms requiring human review (see below)                        | No        | Recommended  |

### Context-Dependent Category

The `context_dependent` category is used for technical mechanisms that cannot be automatically classified to a specific GDPR purpose. These are the "how" of data collection, not the "why":

- **Communication and Messaging**: Could be transactional (operational) or marketing
- **Social Media Integration**: Could be authentication (operational) or marketing/advertising
- **Web Form Data Collection**: Purpose depends on what data is collected and why
- **Session and Cookie Management**: Could be strictly necessary or for tracking/analytics
- **Database Operations**: Purpose depends on business context

Findings in this category have `require_review: true` set, indicating they need human review to determine the actual processing purpose.

## Output Schema

The classifier outputs `gdpr_processing_purpose` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
  - Each finding includes `require_review` (only present when `true`)
- `summary`: Statistics including:
  - `total_findings`: Total classified findings
  - `purpose_categories`: Count per category
  - `sensitive_purposes_count`: Findings with sensitive purposes
  - `dpia_required_count`: Findings requiring DPIA
  - `requires_review_count`: Findings needing human review
- `analysis_metadata`: Metadata about the classification process
