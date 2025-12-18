"""Seed script for healthcare sample data in MongoDB.

This script creates realistic sample data for a healthcare patient booking system.
It is designed to:
1. Be repeatable - can run multiple times (drops and recreates data)
2. Be shareable - share with clients to validate schema matches their production
3. Demonstrate GDPR-relevant data patterns for compliance analysis

Usage:
    uv run seed-mongodb                    # Uses default localhost:27017
    uv run seed-mongodb --uri mongodb://host:port --database mydb

Collections created:
    - patients: Patient demographic and contact information
    - appointments: Booking records with provider references
    - medical_records: Health conditions, medications, allergies
    - providers: Healthcare providers (doctors, nurses, etc.)
    - audit_logs: Access and modification audit trail
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

# =============================================================================
# SAMPLE DATA DEFINITIONS
# =============================================================================
# These represent realistic healthcare data patterns.
# Share this file with clients to validate field names match their schema.
# =============================================================================

PATIENTS: list[dict[str, Any]] = [
    {
        "patient_id": "PAT-001",
        "personal_info": {
            "first_name": "Emma",
            "last_name": "Thompson",
            "date_of_birth": datetime(1985, 3, 15),
            "gender": "female",
            "nhs_number": "943-576-2819",  # UK NHS identifier
            "national_insurance_number": "QQ123456C",
        },
        "contact": {
            "email": "emma.thompson@email.com",
            "phone": "+44 7700 900123",
            "mobile": "+44 7700 900123",
            "address": {
                "line1": "42 Oak Street",
                "line2": "Apartment 3B",
                "city": "Manchester",
                "postcode": "M1 4BT",
                "country": "United Kingdom",
            },
        },
        "emergency_contact": {
            "name": "James Thompson",
            "relationship": "Spouse",
            "phone": "+44 7700 900456",
        },
        "registration_date": datetime(2020, 6, 1),
        "status": "active",
        "preferences": {
            "communication_method": "email",
            "language": "en",
            "reminder_hours_before": 24,
        },
        "consent": {
            "marketing": False,
            "data_sharing_research": True,
            "sms_reminders": True,
            "consent_date": datetime(2020, 6, 1),
        },
    },
    {
        "patient_id": "PAT-002",
        "personal_info": {
            "first_name": "Mohammed",
            "last_name": "Ali",
            "date_of_birth": datetime(1972, 11, 8),
            "gender": "male",
            "nhs_number": "738-492-1056",
            "national_insurance_number": "AB987654D",
        },
        "contact": {
            "email": "m.ali72@gmail.com",
            "phone": "+44 7911 123456",
            "mobile": "+44 7911 123456",
            "address": {
                "line1": "15 High Street",
                "city": "Birmingham",
                "postcode": "B1 1AA",
                "country": "United Kingdom",
            },
        },
        "emergency_contact": {
            "name": "Fatima Ali",
            "relationship": "Wife",
            "phone": "+44 7911 654321",
        },
        "registration_date": datetime(2019, 2, 14),
        "status": "active",
        "preferences": {
            "communication_method": "phone",
            "language": "en",
            "reminder_hours_before": 48,
        },
        "consent": {
            "marketing": False,
            "data_sharing_research": False,
            "sms_reminders": True,
            "consent_date": datetime(2019, 2, 14),
        },
    },
    {
        "patient_id": "PAT-003",
        "personal_info": {
            "first_name": "Sarah",
            "last_name": "O'Connor",
            "date_of_birth": datetime(1990, 7, 22),
            "gender": "female",
            "nhs_number": "651-823-4097",
            "national_insurance_number": "CD456789E",
        },
        "contact": {
            "email": "sarah.oconnor@company.co.uk",
            "phone": "+44 20 7946 0958",
            "mobile": "+44 7777 888999",
            "address": {
                "line1": "8 Victoria Road",
                "city": "London",
                "postcode": "SW1A 1AA",
                "country": "United Kingdom",
            },
        },
        "registration_date": datetime(2023, 1, 10),
        "status": "active",
        "preferences": {
            "communication_method": "email",
            "language": "en",
            "reminder_hours_before": 24,
        },
        "consent": {
            "marketing": True,
            "data_sharing_research": True,
            "sms_reminders": False,
            "consent_date": datetime(2023, 1, 10),
        },
    },
]


MEDICAL_RECORDS: list[dict[str, Any]] = [
    {
        "patient_id": "PAT-001",
        "conditions": [
            {
                "icd_code": "E11.9",
                "name": "Type 2 diabetes mellitus",
                "diagnosed_date": datetime(2018, 5, 20),
                "status": "active",
                "severity": "moderate",
            },
            {
                "icd_code": "I10",
                "name": "Essential hypertension",
                "diagnosed_date": datetime(2019, 3, 12),
                "status": "active",
                "severity": "mild",
            },
        ],
        "medications": [
            {
                "name": "Metformin",
                "dosage": "500mg",
                "frequency": "twice daily",
                "prescribed_date": datetime(2018, 5, 25),
                "prescriber_id": "PROV-001",
            },
            {
                "name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily",
                "prescribed_date": datetime(2019, 3, 15),
                "prescriber_id": "PROV-001",
            },
        ],
        "allergies": [
            {
                "allergen": "Penicillin",
                "reaction": "Skin rash",
                "severity": "moderate",
                "recorded_date": datetime(2015, 8, 1),
            },
        ],
        "blood_type": "A+",
        "last_updated": datetime(2024, 11, 15),
    },
    {
        "patient_id": "PAT-002",
        "conditions": [
            {
                "icd_code": "J45.20",
                "name": "Mild intermittent asthma",
                "diagnosed_date": datetime(2005, 9, 10),
                "status": "active",
                "severity": "mild",
            },
        ],
        "medications": [
            {
                "name": "Salbutamol inhaler",
                "dosage": "100mcg",
                "frequency": "as needed",
                "prescribed_date": datetime(2005, 9, 15),
                "prescriber_id": "PROV-002",
            },
        ],
        "allergies": [],
        "blood_type": "O-",
        "last_updated": datetime(2024, 10, 3),
    },
    {
        "patient_id": "PAT-003",
        "conditions": [],
        "medications": [],
        "allergies": [
            {
                "allergen": "Latex",
                "reaction": "Contact dermatitis",
                "severity": "mild",
                "recorded_date": datetime(2020, 4, 15),
            },
        ],
        "blood_type": "B+",
        "last_updated": datetime(2024, 12, 1),
    },
]


def _generate_appointments() -> list[dict[str, Any]]:
    """Generate appointment data with dates relative to now."""
    base_date = datetime.now()
    return [
        {
            "appointment_id": "APT-001",
            "patient_id": "PAT-001",
            "provider_id": "PROV-001",
            "appointment_type": "follow_up",
            "scheduled_datetime": base_date + timedelta(days=7, hours=10),
            "duration_minutes": 30,
            "status": "confirmed",
            "reason": "Diabetes management review",
            "notes": "Check HbA1c levels, review medication efficacy",
            "created_at": base_date - timedelta(days=14),
            "reminder_sent": True,
            "location": {
                "facility": "Manchester Medical Centre",
                "room": "Consultation Room 3",
            },
        },
        {
            "appointment_id": "APT-002",
            "patient_id": "PAT-002",
            "provider_id": "PROV-002",
            "appointment_type": "routine_checkup",
            "scheduled_datetime": base_date + timedelta(days=3, hours=14, minutes=30),
            "duration_minutes": 20,
            "status": "confirmed",
            "reason": "Annual health check",
            "notes": None,
            "created_at": base_date - timedelta(days=21),
            "reminder_sent": True,
            "location": {
                "facility": "Birmingham Health Hub",
                "room": "Room 12",
            },
        },
        {
            "appointment_id": "APT-003",
            "patient_id": "PAT-003",
            "provider_id": "PROV-001",
            "appointment_type": "new_patient",
            "scheduled_datetime": base_date - timedelta(days=5, hours=9),
            "duration_minutes": 45,
            "status": "completed",
            "reason": "New patient registration and initial assessment",
            "notes": "Patient in good health, no immediate concerns",
            "created_at": base_date - timedelta(days=30),
            "reminder_sent": True,
            "completed_at": base_date - timedelta(days=5, hours=8),
            "location": {
                "facility": "London Wellness Clinic",
                "room": "GP Suite 1",
            },
        },
        {
            "appointment_id": "APT-004",
            "patient_id": "PAT-001",
            "provider_id": "PROV-003",
            "appointment_type": "specialist_referral",
            "scheduled_datetime": base_date + timedelta(days=21, hours=11),
            "duration_minutes": 60,
            "status": "pending",
            "reason": "Cardiology consultation for hypertension management",
            "notes": None,
            "created_at": base_date - timedelta(days=2),
            "reminder_sent": False,
            "location": {
                "facility": "Manchester Medical Centre",
                "room": "Cardiology Department",
            },
        },
    ]


PROVIDERS: list[dict[str, Any]] = [
    {
        "provider_id": "PROV-001",
        "personal_info": {
            "title": "Dr",
            "first_name": "Elizabeth",
            "last_name": "Chen",
            "gender": "female",
        },
        "professional_info": {
            "gmc_number": "7654321",  # UK General Medical Council number
            "specialisation": "General Practice",
            "qualifications": ["MBBS", "MRCGP"],
            "years_experience": 15,
        },
        "contact": {
            "work_email": "e.chen@healthcare.nhs.uk",
            "work_phone": "+44 161 123 4567",
        },
        "facilities": ["Manchester Medical Centre", "London Wellness Clinic"],
        "status": "active",
        "created_at": datetime(2015, 4, 1),
    },
    {
        "provider_id": "PROV-002",
        "personal_info": {
            "title": "Dr",
            "first_name": "Raj",
            "last_name": "Patel",
            "gender": "male",
        },
        "professional_info": {
            "gmc_number": "8765432",
            "specialisation": "General Practice",
            "qualifications": ["MBBS", "DRCOG", "MRCGP"],
            "years_experience": 22,
        },
        "contact": {
            "work_email": "r.patel@healthcare.nhs.uk",
            "work_phone": "+44 121 987 6543",
        },
        "facilities": ["Birmingham Health Hub"],
        "status": "active",
        "created_at": datetime(2010, 9, 15),
    },
    {
        "provider_id": "PROV-003",
        "personal_info": {
            "title": "Dr",
            "first_name": "William",
            "last_name": "Hughes",
            "gender": "male",
        },
        "professional_info": {
            "gmc_number": "9876543",
            "specialisation": "Cardiology",
            "qualifications": ["MBBS", "MRCP", "MD"],
            "years_experience": 18,
        },
        "contact": {
            "work_email": "w.hughes@healthcare.nhs.uk",
            "work_phone": "+44 161 234 5678",
        },
        "facilities": ["Manchester Medical Centre"],
        "status": "active",
        "created_at": datetime(2012, 1, 10),
    },
]


def _generate_audit_logs() -> list[dict[str, Any]]:
    """Generate audit log entries with timestamps relative to now."""
    base_date = datetime.now()
    return [
        {
            "log_id": "LOG-001",
            "timestamp": base_date - timedelta(days=1, hours=10, minutes=23),
            "action": "VIEW",
            "resource_type": "patient",
            "resource_id": "PAT-001",
            "user_id": "PROV-001",
            "user_role": "doctor",
            "ip_address": "192.168.1.105",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "details": {"fields_accessed": ["medical_records", "appointments"]},
        },
        {
            "log_id": "LOG-002",
            "timestamp": base_date - timedelta(days=1, hours=10, minutes=45),
            "action": "UPDATE",
            "resource_type": "medical_record",
            "resource_id": "PAT-001",
            "user_id": "PROV-001",
            "user_role": "doctor",
            "ip_address": "192.168.1.105",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "details": {
                "changes": {"medications": "Added new prescription for Lisinopril"}
            },
        },
        {
            "log_id": "LOG-003",
            "timestamp": base_date - timedelta(hours=5, minutes=12),
            "action": "CREATE",
            "resource_type": "appointment",
            "resource_id": "APT-004",
            "user_id": "ADMIN-001",
            "user_role": "admin",
            "ip_address": "192.168.1.50",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "details": {"patient_id": "PAT-001", "provider_id": "PROV-003"},
        },
        {
            "log_id": "LOG-004",
            "timestamp": base_date - timedelta(minutes=30),
            "action": "EXPORT",
            "resource_type": "patient_data",
            "resource_id": "PAT-002",
            "user_id": "PAT-002",
            "user_role": "patient",
            "ip_address": "86.134.22.156",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
            "details": {
                "export_format": "PDF",
                "data_types": ["personal_info", "appointments"],
            },
        },
    ]


# =============================================================================
# SEED FUNCTIONS
# =============================================================================


def seed_database(db: Database[dict[str, Any]]) -> dict[str, int]:
    """Seed the database with healthcare sample data.

    Args:
        db: MongoDB database instance

    Returns:
        Dictionary with collection names and document counts inserted

    """
    results: dict[str, int] = {}

    # Drop existing collections for clean slate
    for collection_name in [
        "patients",
        "medical_records",
        "appointments",
        "providers",
        "audit_logs",
    ]:
        db.drop_collection(collection_name)

    # Insert patients
    db.patients.insert_many(PATIENTS)
    results["patients"] = len(PATIENTS)

    # Insert medical records
    db.medical_records.insert_many(MEDICAL_RECORDS)
    results["medical_records"] = len(MEDICAL_RECORDS)

    # Insert appointments (with dynamic dates)
    appointments = _generate_appointments()
    db.appointments.insert_many(appointments)
    results["appointments"] = len(appointments)

    # Insert providers
    db.providers.insert_many(PROVIDERS)
    results["providers"] = len(PROVIDERS)

    # Insert audit logs (with dynamic timestamps)
    audit_logs = _generate_audit_logs()
    db.audit_logs.insert_many(audit_logs)
    results["audit_logs"] = len(audit_logs)

    # Create indexes (representative of production setup)
    db.patients.create_index("patient_id", unique=True)
    db.patients.create_index("personal_info.nhs_number", unique=True)
    db.patients.create_index("contact.email")
    db.medical_records.create_index("patient_id")
    db.appointments.create_index("patient_id")
    db.appointments.create_index("provider_id")
    db.appointments.create_index("scheduled_datetime")
    db.providers.create_index("provider_id", unique=True)
    db.audit_logs.create_index("timestamp")
    db.audit_logs.create_index([("resource_type", 1), ("resource_id", 1)])

    return results


def main() -> None:
    """Entry point for the seed script."""
    parser = argparse.ArgumentParser(
        description="Seed MongoDB with healthcare sample data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run seed-mongodb
    uv run seed-mongodb --uri mongodb://localhost:27017 --database healthcare_dev
    uv run seed-mongodb --uri mongodb://user:pass@host:27017 --database staging

Collections created:
    patients        - Patient demographic and contact information
    medical_records - Health conditions, medications, allergies
    appointments    - Booking records with provider references
    providers       - Healthcare providers (doctors, nurses)
    audit_logs      - Access and modification audit trail
        """,
    )
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI (default: mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--database",
        default="healthcare_booking",
        help="Database name (default: healthcare_booking)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without actually inserting data",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - No data will be inserted\n")
        print(f"Would connect to: {args.uri}")
        print(f"Would create database: {args.database}")
        print("\nCollections and document counts:")
        print(f"  patients:        {len(PATIENTS)}")
        print(f"  medical_records: {len(MEDICAL_RECORDS)}")
        print(f"  appointments:    {len(_generate_appointments())}")
        print(f"  providers:       {len(PROVIDERS)}")
        print(f"  audit_logs:      {len(_generate_audit_logs())}")
        return

    print(f"Connecting to MongoDB at {args.uri}...")

    try:
        client: MongoClient[dict[str, Any]] = MongoClient(args.uri)
        # Test connection
        client.admin.command("ping")
        print("Connected successfully!\n")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    db = client[args.database]
    print(f"Seeding database '{args.database}'...")

    results = seed_database(db)

    print("\nSeed complete! Documents inserted:")
    for collection, count in results.items():
        print(f"  {collection}: {count}")

    print(f"\nDatabase '{args.database}' is ready for testing.")
    print("\nTo verify, run:")
    print(
        f'  docker exec mangodb mongosh --eval "use {args.database}; db.patients.findOne()"'
    )


if __name__ == "__main__":
    main()
