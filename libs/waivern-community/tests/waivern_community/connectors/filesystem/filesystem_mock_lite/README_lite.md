# Filesystem Mock Lite - Quick E2E Testing

## Overview

This lite version of the filesystem mock provides essential test coverage for compliance analysis while being optimized for quick end-to-end testing with LLM validation enabled. It contains approximately 65-70 carefully selected cases that represent the full breadth of compliance concerns from the original comprehensive mock.

## Directory Structure

```
filesystem_mock_lite/
├── hr/                          # Human Resources documents
│   └── personal_data_sample.txt # 15 genuine personal data cases
├── compliance/                  # Compliance-specific tests
│   ├── international_formats.csv # 20 international format cases
│   └── encoded_data.xml         # 15 subtle/hidden personal data cases
├── source_code/                 # Multi-language source code
│   ├── user_model.py           # Python data models with personal data
│   └── auth_controller.php     # PHP GDPR compliance patterns
├── finance/                     # Financial data
│   └── customer_data.sql       # 15 SQL cases with personal data
├── logs/                        # System and application logs
│   ├── payment_transactions.log # 15 payment/financial personal data cases
│   ├── audit_activities.log    # 15 GDPR compliance logging cases
│   └── false_positives.log     # Technical patterns (should NOT be flagged)
├── config/                      # Configuration files
│   └── app_config.yaml         # Configuration with admin contacts
├── uploads/                     # User content
│   ├── support_tickets.json    # Mixed real/technical personal data
│   └── malformed_samples.txt   # Edge cases and error handling
├── mixed_content_lite.txt      # Quick mixed content test
└── README_lite.md             # This documentation
```

## Test Coverage

### Personal Data Categories (~70 cases total):
- **Basic Identity**: Names, emails, usernames (18 cases)
- **Contact Information**: Phone numbers, addresses (18 cases)
- **Financial Data**: Payment details, billing info (10 cases)
- **International Formats**: Various country formats (9 cases)
- **Special Categories**: Medical, biometric data (5 cases)
- **Technical Context**: Source code, configurations (10 cases)

### File Types Covered:
- **Text files**: HR documents, mixed content
- **CSV**: International formats, structured data
- **JSON**: Support tickets, mixed technical/personal data
- **XML**: Encoded and subtle personal data patterns
- **SQL**: Database dumps with personal data
- **PHP/Python**: Source code with personal data handling
- **YAML**: Configuration files with contact information
- **Log files**: Various log formats with different contexts

### Analysis Scenarios:
1. **Personal Data Detection**: Should detect ~50 genuine cases
2. **False Positive Avoidance**: Should ignore ~20 technical patterns
3. **International Support**: Covers 9 countries and formats
4. **Encoding Detection**: Tests Base64, URL encoding, embedded data
5. **Source Code Analysis**: Personal data in code, comments, queries
6. **Configuration Analysis**: Admin contacts, emergency information

## Expected Results

### High Confidence Findings:
- `hr/personal_data_sample.txt`: ~15 personal data instances
- `finance/customer_data.sql`: ~15 personal data instances
- `compliance/international_formats.csv`: ~20 personal data instances

### Medium Confidence Findings:
- `compliance/encoded_data.xml`: ~15 encoded/hidden instances
- `config/app_config.yaml`: ~10 configuration contacts
- `logs/payment_transactions.log`: ~15 payment-related instances
- `logs/audit_activities.log`: ~15 audit log instances

### Should NOT be flagged:
- `logs/false_positives.log`: Technical patterns only
- API endpoints and configuration examples
- Documentation and validation patterns

## Performance Characteristics

- **File Count**: 14 files (vs 25 in full mock)
- **Total Size**: ~60KB (vs ~288KB in full mock)
- **Personal Data Cases**: ~70 (vs ~135+ detected in previous version)
- **Processing Time**: ~80% faster than full mock
- **Coverage**: Maintains breadth across all compliance categories

## Usage

```bash
# Quick E2E test with lite mock
uv run wct run runbooks/samples/file_content_analysis.yaml --path=tests/wct/connectors/filesystem/filesystem_mock_lite -v

# Validate coverage
uv run wct run runbooks/samples/comprehensive_analysis.yaml --path=tests/wct/connectors/filesystem/filesystem_mock_lite
```

This lite version is ideal for:
- Continuous integration testing
- Quick validation of changes
- Development workflow testing
- Performance benchmarking

For comprehensive testing and validation, use the full `filesystem_mock` directory.
