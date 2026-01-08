# Processing Purpose Analyser: Source Code Analysis

## Overview

The ProcessingPurposeAnalyser implements pattern matching analysis against source code data from SourceCodeConnector. It detects business purposes and compliance-relevant patterns in raw source code content.

## Analysis Strategy

### Pattern Matching Against Raw Content

**Target**: `raw_content` field from source code files
**Purpose**: Detect processing purposes in code comments, documentation, string literals, and identifiers

**Implementation**: Pattern matching against three rulesets:

1. **Processing Purposes Ruleset** - Business intent detection
2. **Service Integrations Ruleset** - Third-party service usage
3. **Data Collection Ruleset** - Data collection mechanisms

**Example Matches**:
```php
// Marketing automation for customer engagement
function trackUserBehavior($userId) {
    // Analytics for product improvement
    sendEvent('user_action', $data);
}
```

## Current Architecture

### Core Handler: `SourceCodeSchemaInputHandler`

```python
class SourceCodeSchemaInputHandler:
    def __init__(self):
        # Load all three rulesets using URI format
        self.processing_purposes_rules = RulesetLoader.load_ruleset(
            "local/processing_purposes/1.0.0", ProcessingPurposeRule
        )
        self.service_integrations_rules = RulesetLoader.load_ruleset(
            "local/service_integrations/1.0.0", ServiceIntegrationRule
        )
        self.data_collection_rules = RulesetLoader.load_ruleset(
            "local/data_collection/1.0.0", DataCollectionRule
        )
```

### Analysis Flow

Pattern matching is performed line-by-line against raw content:

```python
def _analyse_file_data(self, file_data, file_metadata):
    findings = []

    for rule in self._processing_purposes_rules:
        for i, line in enumerate(file_data["raw_content"].splitlines()):
            for pattern in rule.patterns:
                if pattern.lower() in line.lower():
                    # Create finding with line-based evidence
                    ...

    return findings
```

### Example Finding Structure

```json
{
  "purpose": "payment_processing",
  "purpose_category": "OPERATIONAL",
  "matched_patterns": ["payment"],
  "evidence": [
    {"content": "Line 15: function processPayment($amount)"}
  ],
  "metadata": {
    "source": "source_code"
  },
  "service_category": "payment_processing"
}
```

## Benefits

### 1. Comprehensive Coverage
- **Business Intent**: Processing purposes from comments and identifiers
- **Technical Implementation**: Service integrations from library usage
- **Data Operations**: Collection patterns from code patterns

### 2. LLM-Ready Architecture
- Raw content passed directly to LLM for semantic validation
- LLMs understand code structure natively
- No pre-extracted structure needed

### 3. GDPR Compliance Support
- **Article 30**: Processing activity documentation
- **Article 28**: Service integration identification
- **Article 25**: Data collection mechanism analysis
