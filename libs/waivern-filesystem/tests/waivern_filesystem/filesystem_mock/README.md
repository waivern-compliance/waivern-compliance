# Filesystem Mock — Test Fixtures for Compliance Analysis

## Overview

This mock filesystem provides test coverage for both personal data detection and source code analysis. It serves as a testing environment for validating WCT's analysis engines across multiple file types, formats, and compliance scenarios.

## Directory Structure

```
filesystem_mock/
├── hr/                          # Human Resources documents
│   └── personal_data_sample.txt # Genuine personal data cases
├── compliance/                  # Compliance-specific tests
│   ├── international_formats.csv # International format cases
│   └── encoded_data.xml         # Subtle/hidden personal data
├── source_code/                 # Multi-language source code samples
│   ├── auth_controller.php      # PHP GDPR compliance patterns
│   ├── auth_service.js          # JavaScript authentication service
│   ├── data_model.py            # Python data models with personal data
│   ├── user_controller.php      # PHP with GDPR compliance patterns
│   └── user_model.py            # Python data models with personal data
├── finance/                     # Financial data
│   └── customer_data.sql        # SQL cases with personal data
├── logs/                        # System and application logs
│   ├── payment_transactions.log # Payment/financial personal data
│   ├── audit_activities.log     # GDPR compliance logging
│   └── false_positives.log      # Technical patterns (should NOT be flagged)
├── config/                      # Configuration files
│   └── app_config.yaml          # Configuration with admin contacts
├── uploads/                     # User content
│   ├── support_tickets.json     # Mixed real/technical personal data
│   └── malformed_samples.txt    # Edge cases and error handling
├── mixed_content.txt            # Quick mixed content test
└── README.md                    # This documentation
```

## Test Coverage

### Personal Data Categories

- **Basic Identity**: Names, emails, usernames
- **Contact Information**: Phone numbers, addresses
- **Financial Data**: Payment details, billing info
- **International Formats**: Various country formats
- **Special Categories**: Medical, biometric data
- **Technical Context**: Source code, configurations

### File Types Covered

Text, CSV, JSON, XML, SQL, PHP, Python, JavaScript, YAML, log files.

### Source Code Analysis

The `source_code/` directory contains multi-language samples for testing:

- Personal data handling in function parameters
- Database queries with personal data
- Personal data fields in classes/structs
- Hardcoded personal data in code
- Authentication and session management patterns
- GDPR compliance patterns

## Usage

```bash
# File content analysis
uv run wct run runbooks/samples/file_content_analysis.yaml -v

# Full LAMP stack analysis (includes source code pipeline)
uv run wct run runbooks/samples/LAMP_stack_lite.yaml -v
```
