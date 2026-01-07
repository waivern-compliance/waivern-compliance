# Mock PHP Project for Processing Purpose Analysis Testing

This directory contains 25 PHP files designed to test the WCT processing purpose analyser for source code input. The files simulate a realistic web application with various data processing purposes and service integrations. Note: This was moved from personal_data_analyser tests as part of the architectural refactor.

## Test Results Summary

**Source Code Analysis:**
- ✅ Files analysed: 25
- ✅ Total lines of code: 1,389
- ✅ All files successfully parsed

**Processing Purpose Detection:**
- ✅ Service integrations identified: Payment processors, analytics, email services
- ✅ Business logic patterns: Authentication, data processing, GDPR compliance functions
- ✅ Third-party platform integrations: Social media, cloud services, communication tools

## Processing Purpose Categories Detected

| Purpose Category | Examples Found | Integration Types |
|------------------|----------------|-------------------|
| Payment, Billing, and Invoicing | stripe, paypal, charge, billing | Payment processors |
| User Identity and Login Management | auth0, oauth, authenticate, login | Authentication services |
| Behavioral Data Analysis | analytics, tracking, google-analytics | Analytics platforms |
| Customer Service and Support | sendgrid, mailchimp, email, support | Communication services |
| Targeted Marketing via Third-Party Platforms | facebook, twitter, social, advertising | Social media integrations |
| General Product and Service Delivery | aws, storage, service, delivery | Cloud infrastructure |

## Pattern Detection Types

✅ **Service Integration Patterns**: Stripe API calls, Google Analytics tracking, social media integrations
✅ **Business Logic Patterns**: Authentication flows, payment processing, user management
✅ **Third-Party API Usage**: Email services, SMS providers, analytics platforms
✅ **Processing Purpose Keywords**: "payment", "analytics", "authentication", "marketing"

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

1. **Processing Purpose Analysis**: ProcessingPurposeAnalyser now handles source code analysis for business logic
2. **Service Integration Detection**: Successfully identifies third-party service patterns and integrations
3. **Business Purpose Recognition**: Detects processing purposes like payment, analytics, authentication
4. **Compliance Mapping**: Maps detected patterns to compliance frameworks (GDPR, PCI DSS, etc.)
5. **Clear Separation**: Processing purposes (WHY data is used) vs personal data (WHAT data exists)

## Usage for Testing

```bash
# Run source code analysis on mock files
uv run python -c "
from src.wct.connectors.source_code.connector import SourceCodeConnector
connector = SourceCodeConnector('./mock_php_project', language='php')
result = connector.extract()
print(f'Analyzed {len(result.content[\"data\"])} files')
"

# Run processing purpose analysis
uv run python -c "
from src.wct.analysers.processing_purpose_analyser.analyser import ProcessingPurposeAnalyser
analyser = ProcessingPurposeAnalyser(enable_llm_validation=False)
# ... (process source code analysis result)
"
```

This mock project demonstrates that the WCT processing purpose analyser can effectively identify business processing purposes and service integrations in real-world PHP applications, supporting comprehensive GDPR compliance analysis.
