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
from waivern_analysers_shared.utilities import RulesetManager

class SourceCodeSchemaInputHandler:
    def __init__(self):
        # Load all three rulesets using RulesetManager (provides caching)
        self._processing_purposes_rules = RulesetManager.get_rules(
            "local/processing_purposes/1.0.0", ProcessingPurposeRule
        )
        self._service_integrations_rules = RulesetManager.get_rules(
            "local/service_integrations/1.0.0", ServiceIntegrationRule
        )
        self._data_collection_rules = RulesetManager.get_rules(
            "local/data_collection/1.0.0", DataCollectionRule
        )
```

### Analysis Flow

Pattern matching is performed line-by-line against raw content. Matches are then
**grouped by purpose** (rule name), aggregating pattern counts and using the first
match location for evidence:

```python
def _analyse_file_data(self, file_data):
    # 1. Collect all matches across all rules
    purpose_matches: dict[str, list[MatchInfo]] = {}

    for rule in self._processing_purposes_rules:
        for line_idx, pattern in self._find_pattern_matches(lines, rule.patterns):
            purpose = rule.name  # Group key
            if purpose not in purpose_matches:
                purpose_matches[purpose] = []
            purpose_matches[purpose].append(MatchInfo(pattern=pattern, ...))

    # 2. Create ONE finding per purpose with aggregated pattern counts
    for purpose, matches in purpose_matches.items():
        pattern_counts = Counter(m.pattern for m in matches)
        matched_patterns = [
            PatternMatchDetail(pattern=p, match_count=c)
            for p, c in pattern_counts.items()
        ]
        # Evidence from first match location with context window
        ...
```

This grouping behaviour ensures that multiple occurrences of the same processing
purpose in a file produce a single finding with accurate match counts, rather than
one finding per pattern match.

### Example Indicator Structure

Indicators are grouped by purpose (rule name), with pattern match counts aggregated:

```json
{
  "purpose": "Payment, Billing, and Invoicing",
  "matched_patterns": [
    {"pattern": "payment", "match_count": 3},
    {"pattern": "checkout", "match_count": 2}
  ],
  "evidence": [
    {"content": "  15  function processPayment($amount) {\n  16      // Process checkout\n  17  }"}
  ],
  "metadata": {
    "source": "src/payments/checkout.php",
    "line_number": 15
  }
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

### 3. Compliance Framework Support
- Processing activity documentation for regulatory compliance
- Service integration identification for vendor management
- Data collection mechanism analysis for privacy audits
