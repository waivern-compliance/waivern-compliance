# waivern-gdpr-personal-data-classifier

GDPR personal data classifier for Waivern Compliance Framework.

## Overview

Classifies generic personal data indicators according to GDPR requirements:
- Maps detection categories to GDPR data types
- Determines Article 9 special category status
- Adds GDPR Article references

## Installation

```bash
pip install waivern-gdpr-personal-data-classifier
```

## Usage

```python
from waivern_gdpr_personal_data_classifier import GDPRPersonalDataClassifier

# Used via WCT runbooks or programmatically
```

### In a Runbook

```yaml
artifacts:
  personal_data_indicators:
    inputs: data_content
    process:
      type: personal_data

  gdpr_personal_data:
    inputs: personal_data_indicators
    process:
      type: gdpr_personal_data_classifier
    output: true
```

## Output Schema

The classifier outputs `gdpr_personal_data` version `1.0.0` with:

- `findings`: List of classified findings with GDPR enrichment
  - Each finding may include `require_review` when human review is needed
- `summary`: Statistics including:
  - `total_findings`: Total classified findings
  - `special_category_count`: GDPR Article 9 special category findings
  - `requires_review_count`: Findings needing human review
- `analysis_metadata`: Metadata about the classification process

## Development

See [docs](../../docs/) for development guidelines.
