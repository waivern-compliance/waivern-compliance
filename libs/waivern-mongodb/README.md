# waivern-mongodb

MongoDB connector for Waivern Compliance Framework.

## Overview

This package provides:
- MongoDB connector for extracting schema and sample data
- Healthcare sample data seed script for testing and client validation

## Sample Data

The package includes a seed script that creates realistic healthcare data for a patient booking system. This data can be used to:

1. **Test connector development** — Verify schema extraction works correctly
2. **Validate with clients** — Share the script so clients can confirm field names match their production schema
3. **Demonstrate GDPR patterns** — Sample data includes personal data, special category health data, and consent records

### Running the Seed Script

```bash
# Default: localhost:27017, database: healthcare_booking
uv run seed-mongodb

# Custom MongoDB instance
uv run seed-mongodb --uri mongodb://host:27017 --database mydb

# Dry run (see what would be created)
uv run seed-mongodb --dry-run
```

### Collections Created

| Collection | Description | GDPR Relevance |
|------------|-------------|----------------|
| `patients` | Patient demographics, contact info, consent records | Personal data, consent management |
| `medical_records` | Conditions, medications, allergies | Article 9 special category (health) |
| `appointments` | Booking records with provider references | Processing activity records |
| `providers` | Healthcare provider information | Data recipient identification |
| `audit_logs` | Access and modification audit trail | Accountability, data access records |

### Sample Data Fields

The seed script creates data with realistic field names that should trigger GDPR compliance detection:

**Personal Identifiers:**
- `nhs_number` — UK NHS identifier
- `national_insurance_number` — UK NI number
- `email`, `phone`, `mobile`
- `date_of_birth`
- Full address with postcode

**Health Data (Article 9):**
- `conditions` with ICD codes
- `medications` with dosage and frequency
- `allergies` with severity
- `blood_type`

**Consent Records:**
- `consent.marketing`
- `consent.data_sharing_research`
- `consent.sms_reminders`
- `consent.consent_date`

## Development

```bash
# Install dependencies
uv sync

# Run linting
./scripts/lint.sh

# Run type checking
./scripts/type-check.sh

# Run tests
uv run pytest
```
