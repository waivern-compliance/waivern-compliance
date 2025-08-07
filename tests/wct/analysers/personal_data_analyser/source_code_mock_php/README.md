# Mock PHP Project for Personal Data Analysis Testing

This directory contains 25 PHP files designed to test the WCT personal data analyser for source code input. The files simulate a realistic web application with various personal data handling patterns.

## Test Results Summary

**Source Code Analysis:**
- ✅ Files analysed: 25
- ✅ Total lines of code: 1,389
- ✅ All files successfully parsed

**Personal Data Detection:**
- ✅ Total findings: 179
- ✅ High risk findings: 4 (financial and health data)
- ✅ Special category findings: 3 (health data - GDPR Article 9)

## Personal Data Types Detected

| Data Type | Findings | Risk Level | Examples |
|-----------|----------|------------|----------|
| basic_profile | 113 | Medium | email, first_name, last_name, phone |
| user_data | 31 | Medium | user_id, getUserData(), createUser() |
| payment_data | 10 | Medium | credit_card_number, billing_address |
| date_of_birth | 7 | Medium | birth_date, date_of_birth |
| email | 4 | Medium | email_address, sendEmail() |
| health_data | 3 | **High** ⚠️ | patient_id, diagnosis, medical_history |
| contact_data | 3 | Medium | phone_number, address |
| authentication_data | 2 | Medium | authenticateUser(), password |
| profile_data | 2 | Medium | profile_id, getProfileData() |
| User_enriched_profile_data | 2 | Medium | Enhanced profile information |
| financial_data | 1 | **High** ⚠️ | social_security_number |
| user_generated_content | 1 | Medium | User-created content |

## Pattern Detection Types

✅ **Function Names**: `getUserEmail()`, `authenticateUser()`, `processPayment()`
✅ **Parameter Names**: `$email_address`, `$first_name`, `$credit_card_number`
✅ **Class Properties**: `private $social_security_number`, `private $patient_id`
✅ **SQL Patterns**: Queries involving user tables and personal data columns

## File Structure

```
mock_php_project/
├── models/           # Data models (User, Customer, Profile, HealthRecord, Order)
├── controllers/      # Request handlers (Auth, User, Payment, Privacy)
├── services/         # Business logic (Email, SMS, Analytics)
├── src/             # Core utilities (Database, Session, Form validation, etc.)
└── config/          # Configuration classes
```

## Key Features Tested

### GDPR Compliance Patterns
- ✅ Data export functionality (`exportUserData()`)
- ✅ Data deletion (`deleteUserData()`)
- ✅ Data rectification (`rectifyUserData()`)
- ✅ Privacy request handling
- ✅ Audit logging for personal data access

### Security Patterns
- ✅ Password hashing and verification
- ✅ Authentication and authorization
- ✅ Session management
- ✅ Form validation
- ✅ Secure file upload handling

### Third-Party Integrations
- ✅ Email service providers (SendGrid, Mailgun)
- ✅ Payment processors (Stripe)
- ✅ Analytics platforms (Google Analytics)
- ✅ Social media platforms (Facebook)
- ✅ Communication services (Twilio)

### Database Interactions
- ✅ User data queries
- ✅ Payment history access
- ✅ Personal information updates
- ✅ Data deletion for GDPR compliance

## Architecture Validation

This test successfully validates the **refactored architecture** where:

1. **Analyser Delegation**: PersonalDataAnalyser properly delegates to SourceCodeSchemaInputHandler
2. **Handler Self-Containment**: Handler manages its own rulesets independently
3. **Pattern Recognition**: Successfully detects various personal data patterns in PHP code
4. **Risk Assessment**: Correctly identifies high-risk patterns (health, financial data)
5. **Special Categories**: Properly flags GDPR Article 9 special category data

## Usage for Testing

```bash
# Run source code analysis on mock files
uv run python -c "
from src.wct.connectors.source_code.connector import SourceCodeConnector
connector = SourceCodeConnector('./mock_php_project', language='php')
result = connector.extract()
print(f'Analyzed {len(result.content[\"data\"])} files')
"

# Run personal data analysis
uv run python -c "
from src.wct.analysers.personal_data_analyser.analyser import PersonalDataAnalyser
analyser = PersonalDataAnalyser(enable_llm_validation=False)
# ... (process source code analysis result)
"
```

This mock project demonstrates that the WCT personal data analyser can effectively identify personal data handling patterns in real-world PHP applications, supporting comprehensive GDPR compliance analysis.
