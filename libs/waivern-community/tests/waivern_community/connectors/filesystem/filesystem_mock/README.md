# Enhanced Mock Filesystem Test Suite

## Overview

This enhanced mock filesystem provides comprehensive test coverage for both personal data detection and source code analysis capabilities. It serves as a precision testing environment designed to validate the accuracy, robustness, and real-world applicability of WCT's analysis engines.

## Directory Structure

```
filesystem_mock/
├── hr/                     # Human Resources documents
├── finance/               # Financial and customer data
├── logs/                  # System and application logs
├── uploads/               # User uploaded content
├── source_code/           # Multi-language source code samples
├── config/                # Configuration files
├── legacy/                # Legacy system code
├── compliance/            # Compliance-specific test files
├── mixed_content_sample.txt  # Original mixed content (legacy)
├── sample_file.txt       # Original simple test file (legacy)
└── README.md            # This documentation
```

## Test File Categories

### 1. Personal Data Detection Tests

#### Genuine Personal Data (`hr/genuine_personal_data.txt`)
**Purpose**: Test detection of clear, unambiguous personal data violations

**Contents**:
- Employee records with names, emails, phone numbers, DOB
- Multiple international formats (UK, US, EU, etc.)
- Special categories: medical records, biometric data, children's data
- Financial information: IBANs, card numbers, salary data
- Sensitive communications and emergency contacts

**Expected Outcomes**:
- ✅ Should detect ALL personal data instances
- ✅ Should identify special category data (medical, biometric)
- ✅ Should flag financial data as sensitive

#### Edge Cases International (`compliance/edge_cases_international.csv`)
**Purpose**: Test robustness against international formats and naming conventions

**Contents**:
- 25+ countries with different date, phone, and ID formats
- Unicode characters, diacritics, and special alphabets
- Hyphenated names, prefixes, suffixes
- Cultural naming patterns (van der, O', José María)
- Multiple writing systems (Latin, Cyrillic, Arabic, etc.)

**Expected Outcomes**:
- ✅ Should handle international phone formats correctly
- ✅ Should detect names with special characters
- ✅ Should identify emails from various country domains
- ⚠️ May have challenges with non-Latin scripts

#### False Positives Technical (`logs/false_positives_technical.log`)
**Purpose**: Test precision by avoiding false alarms on technical patterns

**Contents**:
- API endpoints with email-like patterns
- Configuration values with domain names
- Code examples and documentation
- System messages and error patterns
- Database connection strings

**Expected Outcomes**:
- ❌ Should NOT flag technical email patterns (admin@localhost)
- ❌ Should NOT flag documentation examples
- ❌ Should NOT flag API endpoint patterns
- ✅ Should distinguish between real and example data

#### Mixed Context Realistic (`uploads/mixed_context_realistic.json`)
**Purpose**: Test real-world scenarios with mixed personal and technical data

**Contents**:
- Customer support tickets with genuine issues
- System logs with both real and test data
- Marketing analytics with anonymized metrics
- Configuration mixed with personal contact info

**Expected Outcomes**:
- ✅ Should detect real personal data in context
- ❌ Should ignore test/example data
- ✅ Should handle JSON/structured data correctly

#### Subtle Personal Data (`compliance/subtle_personal_data.xml`)
**Purpose**: Test detection of hidden or encoded personal data

**Contents**:
- Base64 encoded email addresses
- URL-encoded phone numbers
- Personal data in file paths and database queries
- Hashed data with revealing comments
- Personal data in error messages and templates

**Expected Outcomes**:
- ✅ Should detect Base64 encoded personal data
- ✅ Should identify personal data in unusual locations
- ⚠️ May miss highly obfuscated patterns (acceptable trade-off)

#### Malformed Data (`uploads/malformed_data.txt`)
**Purpose**: Test robustness against corrupted, incomplete, or invalid data

**Contents**:
- Incomplete email addresses and phone numbers
- Corrupted character encodings
- Truncated personal data across lines
- Mixed data types and injection attempts
- Boundary conditions and edge cases

**Expected Outcomes**:
- ✅ Should handle malformed data gracefully
- ✅ Should detect partial matches where appropriate
- ❌ Should not crash on invalid input
- ⚠️ May have reduced accuracy on severely corrupted data

### 2. Source Code Analysis Tests

#### Multi-Language Source Code
**Purpose**: Test source code analysis across different programming languages

**Files**:
- `source_code/user_controller.php` - PHP with GDPR compliance patterns
- `source_code/auth_service.js` - JavaScript authentication service
- `source_code/data_model.py` - Python data models with personal data
- `legacy/customer_system.c` - Legacy C code with privacy violations

**Expected Outcomes**:
- ✅ Should detect personal data handling in function parameters
- ✅ Should identify database queries with personal data
- ✅ Should recognize personal data fields in classes/structs
- ✅ Should detect hardcoded personal data in code

#### Configuration Analysis (`config/application_config.yaml`)
**Purpose**: Test analysis of configuration files for personal data

**Contents**:
- Database connection strings
- Email service configuration with personal contacts
- System administrator contact information
- GDPR compliance settings and DPO contacts

**Expected Outcomes**:
- ✅ Should detect personal contact information
- ❌ Should ignore system configuration values
- ✅ Should identify admin/emergency contacts

### 3. Database Analysis (`finance/database_dump.sql`)
**Purpose**: Test analysis of database exports and SQL files

**Contents**:
- Customer table with personal data
- Address and payment information
- Support tickets with customer communications
- Audit logs with personal data access records

**Expected Outcomes**:
- ✅ Should detect personal data in INSERT statements
- ✅ Should identify table schemas containing personal data
- ✅ Should recognize personal data in SQL comments

## Testing Scenarios and Expected Results

### Scenario 1: Comprehensive Personal Data Audit
**Files**: All files in the mock filesystem
**Purpose**: Full-scale personal data discovery audit

**Expected Results**:
```
High Confidence Findings:
- hr/genuine_personal_data.txt: ~50 personal data instances
- finance/database_dump.sql: ~30 personal data instances
- compliance/edge_cases_international.csv: ~100 personal data instances

Medium Confidence Findings:
- compliance/subtle_personal_data.xml: ~20 encoded/hidden instances
- config/application_config.yaml: ~15 configuration contacts

Low Confidence (Review Required):
- uploads/malformed_data.txt: ~10 partial/corrupted instances
- logs/false_positives_technical.log: ~0 (should be filtered out)
```

### Scenario 2: Source Code Security Analysis
**Files**: `source_code/`, `legacy/`
**Purpose**: Identify personal data handling in code

**Expected Results**:
- PHP Controller: Personal data processing functions identified
- JavaScript Service: Authentication and session management flagged
- Python Models: Database schema with personal data fields
- Legacy C Code: Multiple privacy violations and hardcoded data

### Scenario 3: False Positive Minimization
**Files**: `logs/false_positives_technical.log`
**Purpose**: Ensure technical patterns don't trigger false alarms

**Expected Results**:
- API endpoints: Not flagged as personal data
- Configuration examples: Not flagged as personal data
- Documentation patterns: Not flagged as personal data
- System messages: Not flagged as personal data

### Scenario 4: International Compliance Testing
**Files**: `compliance/edge_cases_international.csv`
**Purpose**: Validate international data format recognition

**Expected Results**:
- European formats: GDPR-relevant data detected
- US formats: CCPA-relevant data detected
- Asian formats: Local privacy law compliance
- Special characters: Properly handled

## Validation and Quality Assurance

### Automated Testing Integration
This mock filesystem is designed to integrate with WCT's automated testing suite:

```bash
# Run comprehensive analysis
uv run wct run runbooks/test/filesystem_comprehensive.yaml -v

# Test specific scenarios
uv run wct run runbooks/test/personal_data_only.yaml
uv run wct run runbooks/test/source_code_only.yaml
uv run wct run runbooks/test/false_positives.yaml
```

### Performance Testing
The filesystem contains sufficient data volume to test:
- Processing time for large datasets
- Memory usage with complex file structures
- Scalability with multiple file types

### Accuracy Metrics
Expected accuracy targets:
- **Personal Data Detection**: >95% true positive rate, <5% false positive rate
- **Source Code Analysis**: >90% identification of personal data handling
- **Format Recognition**: >90% accuracy across international formats
- **Edge Case Handling**: Graceful degradation without system failure

## Maintenance and Updates

### Regular Review Schedule
- **Monthly**: Add new edge cases based on real-world findings
- **Quarterly**: Review international format coverage
- **Annually**: Major structural updates to reflect evolving regulations

### Contributing Test Cases
When adding new test files:

1. **Document the purpose** - What specific scenario does it test?
2. **Define expected outcomes** - What should the analyser detect/ignore?
3. **Include metadata** - File format, data categories, complexity level
4. **Validate accuracy** - Test against known good results

### File Naming Conventions
- Descriptive names indicating purpose
- Data category prefixes where appropriate
- Version numbers for evolving test cases
- Clear documentation of contents and expectations

## Advanced Testing Features

### Encoded Data Testing
The filesystem includes various encoding scenarios:
- Base64 encoded personal data
- URL encoded parameters
- Encrypted fields with metadata
- Hashed values with context clues

### Cross-Reference Testing
Files are designed to test cross-reference capabilities:
- Same person's data across multiple files
- Related records in different formats
- Linked data requiring contextual analysis

### Regulatory Compliance Testing
Coverage for major privacy regulations:
- **GDPR**: EU personal data patterns and special categories
- **CCPA**: California consumer data patterns
- **PIPEDA**: Canadian privacy format requirements
- **LGPD**: Brazilian data protection scenarios

## Troubleshooting Common Issues

### Low Detection Rates
If personal data detection is lower than expected:
1. Check file encoding (UTF-8 recommended)
2. Verify analyser configuration for file types
3. Review pattern matching rules for international formats

### High False Positive Rates
If technical patterns are being flagged incorrectly:
1. Review false positive test file for similar patterns
2. Update exclusion rules in analyser configuration
3. Consider context-aware analysis improvements

### Performance Issues
If analysis is slower than expected:
1. Check file sizes (some files are intentionally large)
2. Monitor memory usage during processing
3. Consider parallel processing for large datasets

## Future Enhancements

### Planned Additions
- **Audio/Video Files**: Test multimedia content analysis
- **Compressed Archives**: Test handling of ZIP/TAR files
- **Encrypted Files**: Test encrypted content detection
- **Real-Time Logs**: Test streaming/live data analysis

### Integration Opportunities
- **CI/CD Pipeline**: Automated testing on code commits
- **Compliance Dashboards**: Real-time test result monitoring
- **Benchmark Comparisons**: Performance against industry standards

---

*This mock filesystem represents a comprehensive testing environment designed to validate and improve WCT's personal data detection capabilities. Regular updates and community contributions help maintain its effectiveness as privacy regulations and technology evolve.*
