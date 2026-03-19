# waivern-gdpr-data-collection-classifier

GDPR data collection classifier for Waivern Compliance Framework.

## Overview

This classifier enriches data collection indicator findings with GDPR-specific classification information. It takes output from `DataCollectionAnalyser` and adds:

- **GDPR Purpose Category**: GDPR-specific purpose assessment
- **Article References**: Relevant GDPR article references
- **Typical Lawful Bases**: Typical Article 6 lawful bases for this data collection mechanism
- **Sensitivity Indicators**: Whether the data collection's purpose is privacy-sensitive
- **DPIA Recommendations**: Data Protection Impact Assessment recommendation level
- **Review Requirements**: Whether human review is needed to determine actual purpose

## Usage

### In a Runbook

```yaml
artifacts:
  # First, detect data collection mechanisms
  data_collection_indicators:
    inputs: source_code
    process:
      type: data_collection
      properties:
        pattern_matching:
          ruleset: "local/data_collection/1.0.0"

  # Then, classify according to GDPR
  gdpr_data_collection:
    inputs: data_collection_indicators
    process:
      type: gdpr_data_collection_classifier
    output: true
```

### Programmatic Usage

```python
from waivern_gdpr_data_collection_classifier import GDPRDataCollectionClassifier
from waivern_core import Schema

classifier = GDPRDataCollectionClassifier()
output_schema = Schema("gdpr_data_collection", "1.0.0")

result = classifier.process([indicator_message], output_schema)
```

## Classification Categories

| GDPR Category       | Data Collection Mechanisms                          | Sensitive | DPIA        |
| ------------------- | --------------------------------------------------- | --------- | ----------- |
| `context_dependent` | Web Form Data, Session/Cookies, Database Operations | No        | Recommended |

All data collection mechanisms are classified as `context_dependent` because they are technical mechanisms whose actual GDPR purpose depends on the business context — what data is collected and why.

### Context-Dependent Category

- **Web Form Data Collection**: Forms and HTTP requests could collect any type of data, including special category data (Art. 9)
- **Session and Cookie Management**: Could be strictly necessary (no consent) or for tracking/analytics (requires consent under ePrivacy Directive Art. 5(3))
- **Database Operations**: Databases store data for all purposes — the GDPR purpose depends on business context

All findings have `require_review: true` set, indicating they need human review to determine the actual processing purpose.

## Output Schema

The classifier outputs `gdpr_data_collection` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
  - Each finding includes `collection_type` and `data_source` propagated from the indicator
  - Each finding includes `require_review` (only present when `true`)
- `summary`: Statistics including:
  - `total_findings`: Total classified findings
  - `gdpr_purpose_categories`: Count per GDPR category
  - `sensitive_purposes_count`: Findings with sensitive purposes
  - `dpia_required_count`: Findings requiring DPIA
  - `requires_review_count`: Findings needing human review
- `analysis_metadata`: Metadata about the classification process
