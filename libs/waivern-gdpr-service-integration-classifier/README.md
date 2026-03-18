# waivern-gdpr-service-integration-classifier

GDPR service integration classifier for Waivern Compliance Framework.

## Overview

This classifier enriches service integration indicator findings with GDPR-specific classification information. It takes output from `ServiceIntegrationAnalyser` and adds:

- **GDPR Purpose Category**: GDPR-specific purpose assessment (may differ from the indicator's own purpose category)
- **Article References**: Relevant GDPR article references
- **Typical Lawful Bases**: Typical Article 6 lawful bases for this service integration
- **Sensitivity Indicators**: Whether the service integration's purpose is privacy-sensitive
- **DPIA Recommendations**: Data Protection Impact Assessment recommendation level
- **Review Requirements**: Whether human review is needed to determine actual purpose

## Usage

### In a Runbook

```yaml
artifacts:
  # First, detect service integrations
  service_integration_indicators:
    inputs: source_code
    process:
      type: service_integration
      properties:
        pattern_matching:
          ruleset: "local/service_integrations/1.0.0"

  # Then, classify according to GDPR
  gdpr_service_integrations:
    inputs: service_integration_indicators
    process:
      type: gdpr_service_integration_classifier
    output: true
```

### Programmatic Usage

```python
from waivern_gdpr_service_integration_classifier import GDPRServiceIntegrationClassifier
from waivern_core import Schema

classifier = GDPRServiceIntegrationClassifier()
output_schema = Schema("gdpr_service_integration", "1.0.0")

result = classifier.process([indicator_message], output_schema)
```

## Classification Categories

| GDPR Category       | Service Integrations                                          | Sensitive | DPIA         |
| ------------------- | ------------------------------------------------------------- | --------- | ------------ |
| `ai_and_ml`         | Third-Party AI Services                                       | Yes       | Required     |
| `analytics`         | Third-Party Analytics                                         | Yes       | Recommended  |
| `healthcare`        | Healthcare Systems                                            | Yes       | Required     |
| `operational`       | Cloud Infrastructure, Identity Management, Payment Processing | No        | Not Required |
| `context_dependent` | Communication and Messaging, Social Media Integration         | No        | Recommended  |

### Context-Dependent Category

The `context_dependent` category is used for service integrations whose GDPR purpose cannot be automatically determined:

- **Communication and Messaging**: Could be transactional (operational) or marketing communications — requires contextual review for ePrivacy rules
- **Social Media Integration**: Could be authentication (operational) or marketing/advertising

Findings in this category have `require_review: true` set, indicating they need human review to determine the actual processing purpose.

### Two Purpose Category Fields

Each finding contains two purpose category fields:

- `service_integration_purpose`: The purpose category from the detection rule (e.g., `operational`, `analytics`) — a rough technical categorisation
- `gdpr_purpose_category`: The GDPR-specific assessment (e.g., `context_dependent`, `healthcare`) — may differ from the detection rule's categorisation

## Output Schema

The classifier outputs `gdpr_service_integration` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
  - Each finding includes `require_review` (only present when `true`)
- `summary`: Statistics including:
  - `total_findings`: Total classified findings
  - `gdpr_purpose_categories`: Count per GDPR category
  - `sensitive_purposes_count`: Findings with sensitive purposes
  - `dpia_required_count`: Findings requiring DPIA
  - `requires_review_count`: Findings needing human review
- `analysis_metadata`: Metadata about the classification process
