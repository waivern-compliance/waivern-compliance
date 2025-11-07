# Processing Purpose Analyser: Multi-Ruleset Source Code Analysis

## Overview

The ProcessingPurposeAnalyser now implements comprehensive multi-ruleset analysis for source code data from SourceCodeConnector. This document describes the current implementation and analysis strategy.

## Implementation Status

✅ **FULLY IMPLEMENTED** - All phases complete and tested

## Ruleset Analysis Strategy

### 1. Processing Purposes Ruleset + Raw Content Analysis

**Target**: `raw_content` field from source code files
**Purpose**: Detect business purposes in comments, documentation, and string literals

**Implementation**: `_analyse_raw_content_processing_purposes()`

**Example Matches**:
```php
// Marketing automation for customer engagement
function trackUserBehavior($userId) {
    // Analytics for product improvement
    sendEvent('user_action', $data);
}
```

**Findings**: Business purposes from natural language in code

---

### 2. Service Integrations Ruleset + Structured Analysis

**Target**: `imports`, `functions`, `classes` fields
**Purpose**: Detect third-party service usage and integration patterns

**Implementation**: `_analyse_structured_service_integrations()`

**Analysis Types**:
- **Import Analysis**: `use Stripe\StripeClient` → `payment_processing`
- **Function Analysis**: `sendViaMailchimp()` → `communication_services`
- **Class Analysis**: `GoogleAnalyticsTracker` → `user_analytics`

**Findings**: Service integrations with `service_category` metadata

---

### 3. Data Collection Patterns Ruleset + Structured Analysis

**Target**: `functions` fields + `raw_content` for SQL patterns
**Purpose**: Detect data collection mechanisms and database operations

**Implementation**: `_analyse_structured_data_collection()`

**Analysis Types**:
- **Function Analysis**: `collectUserData()` → `php_post_data`
- **SQL Pattern Analysis**: `INSERT INTO users` → `sql_database_queries`

**Findings**: Data collection patterns with empty `purpose_category` (defaults to "")

---

### 4. Processing Purposes Ruleset + Structured Analysis (Secondary)

**Target**: `functions`, `classes` fields
**Purpose**: Detect business purposes from function/class naming

**Implementation**: `_analyse_structured_processing_purposes()`

**Analysis Types**:
- **Function Analysis**: `processPayment()` → `Payment, Billing, and Invoicing`
- **Class Analysis**: `CustomerSupportBot` → `Customer Service and Support`

**Findings**: Business purposes from code structure

## Current Architecture

### Core Handler: `SourceCodeSchemaInputHandler`

```python
class SourceCodeSchemaInputHandler:
    def __init__(self):
        # Load all three rulesets
        self.processing_purposes_rules = RulesetLoader.load_ruleset("processing_purposes")
        self.service_integrations_rules = RulesetLoader.load_ruleset("service_integrations")
        self.data_collection_rules = RulesetLoader.load_ruleset("data_collection")
```

### Analysis Flow

```python
def _analyse_single_file(self, file_data: SourceCodeFileDataModel):
    findings = []

    # Raw content analysis with processing_purposes
    findings.extend(self._analyse_raw_content_processing_purposes(...))

    # Structured analysis with service_integrations
    findings.extend(self._analyse_structured_service_integrations(...))

    # Structured analysis with data_collection
    findings.extend(self._analyse_structured_data_collection(...))

    # Structured analysis with processing_purposes (secondary)
    findings.extend(self._analyse_structured_processing_purposes(...))

    return findings
```

### Finding Types by Analysis Method

| Analysis Type | Ruleset | Target Data | Purpose Category | Service Category |
|---------------|---------|-------------|------------------|------------------|
| `source_code_pattern_matching_analysis` | processing_purposes | raw_content | Set from ruleset | null |
| `function_name_analysis` | service_integrations | functions | Set from ruleset | Set from ruleset |
| `function_name_analysis` | processing_purposes | functions | Set from ruleset | null |
| `class_name_analysis` | service_integrations | classes | Set from ruleset | Set from ruleset |
| `class_name_analysis` | processing_purposes | classes | Set from ruleset | null |
| `data_collection_function_analysis` | data_collection | functions | "" (empty) | null |
| `import_analysis` | service_integrations | imports | Set from ruleset | Set from ruleset |

## Analysis Results

### Current Performance Metrics
- **526 total findings** from LAMP stack sample
- **19 unique purposes identified**
- **Multiple analysis types** providing comprehensive coverage

### Example Finding Structure

```json
{
  "purpose": "payment_processing",
  "purpose_category": "operational",
  "risk_level": "high",
  "compliance": [
    {
      "regulation": "GDPR",
      "relevance": "Payment processing requires lawful basis under Article 6(1)(b) for contract performance"
    }
  ],
  "matched_pattern": "charge",
  "evidence": [
    "Function: chargeCustomer: Payment processing service integrations - charge",
    "Matched: chargeCustomer"
  ],
  "metadata": {
    "source": "source_code",
    "file_path": "models/Order.php",
    "language": "php",
    "analysis_type": "function_name_analysis",
    "service_category": "payment_processing",
    "description": "Payment processing service integrations",
    "pattern": "charge"
  }
}
```

## Schema Flexibility

### Purpose Category
- **Type**: Free-text string (enum constraint removed)
- **Default**: "" (empty string)
- **Usage**: Each ruleset provides its own categories

### Compliance
- **Type**: Array of objects with regulation and relevance fields
- **Structure**: `[{regulation: "GDPR", relevance: "Specific regulatory context..."}]`
- **Purpose**: Provides detailed compliance information rather than just regulation names

## Benefits

### 1. Comprehensive Coverage
- **Business Intent**: Processing purposes from comments and function names
- **Technical Implementation**: Service integrations from imports and class names
- **Data Operations**: Collection patterns from function names and SQL

### 2. Precise Analysis
- Each ruleset applied to optimal data structures
- Structured analysis for technical patterns
- Raw content analysis for business descriptions

### 3. GDPR Compliance Support
- **Article 30**: Complete processing activity documentation
- **Article 28**: Service integration and processor identification
- **Article 25**: Data collection mechanism analysis

### 4. Extensible Architecture
- Independent ruleset evolution
- Flexible schema support
- Multiple analysis types per file

## Testing

**Validation**: Successfully analyzed 25 PHP files with 526 findings across all analysis types
**Quality**: All pre-commit checks passing (linting, type checking, formatting)
**Integration**: Full end-to-end testing with LAMP stack runbook
