"""
Data Model - User and Personal Data Management

This module handles personal data storage and processing including:
- User profiles with personal information
- Address management
- Data encryption and privacy controls
- GDPR compliance features

Contains personal data fields:
- Names, emails, phone numbers
- Addresses and location data
- Date of birth and age calculation
- National identifiers and sensitive data
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

import phonenumbers
from cryptography.fernet import Fernet
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class DataProcessingPurpose(Enum):
    """GDPR Article 6 - Legal bases for processing personal data"""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class PersonalDataCategory(Enum):
    """Categories of personal data for GDPR compliance"""

    BASIC_IDENTITY = "basic_identity"  # Name, email
    CONTACT_INFO = "contact_info"  # Phone, address
    DEMOGRAPHIC = "demographic"  # Age, gender, DOB
    FINANCIAL = "financial"  # Payment info, income
    HEALTH = "health"  # Medical records (special category)
    BIOMETRIC = "biometric"  # Fingerprints, photos (special category)


@dataclass
class PersonalDataField:
    """Metadata for personal data fields"""

    field_name: str
    category: PersonalDataCategory
    is_sensitive: bool
    retention_period_days: int
    encryption_required: bool
    legal_basis: DataProcessingPurpose


class EncryptionService:
    """Service for encrypting/decrypting personal data"""

    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())

    def encrypt_personal_data(self, data: str) -> str:
        """Encrypt personal data field"""
        if not data:
            return None
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_personal_data(self, encrypted_data: str) -> str:
        """Decrypt personal data field"""
        if not encrypted_data:
            return None
        return self.fernet.decrypt(encrypted_data.encode()).decode()


class User(Base):
    """
    User model - stores personal data

    Contains personal information subject to GDPR:
    - Identity data: first_name, last_name, email
    - Contact data: phone, addresses
    - Demographic data: date_of_birth, gender
    - Account data: password, preferences
    """

    __tablename__ = "users"

    # Primary identifier
    id = Column(Integer, primary_key=True)

    # Personal identity data (GDPR Article 4(1))
    first_name = Column(
        String(100), nullable=False, comment="First name - personal data"
    )
    last_name = Column(String(100), nullable=False, comment="Last name - personal data")
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        comment="Email address - personal data",
    )

    # Contact information (personal data)
    phone = Column(Text, comment="Encrypted phone number - personal data")
    mobile_phone = Column(Text, comment="Encrypted mobile number - personal data")

    # Demographic data (personal data)
    date_of_birth = Column(Text, comment="Encrypted date of birth - personal data")
    gender = Column(String(20), comment="Gender - personal data")
    nationality = Column(String(100), comment="Nationality - personal data")

    # Authentication data
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False)

    # GDPR compliance fields
    gdpr_consent_given_at = Column(DateTime)
    gdpr_consent_withdrawn_at = Column(DateTime)
    marketing_consent = Column(Boolean, default=False)
    analytics_consent = Column(Boolean, default=False)
    data_retention_until = Column(Date)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    deleted_at = Column(DateTime, comment="Soft delete for GDPR compliance")

    # Relationships
    addresses = relationship(
        "Address", back_populates="user", cascade="all, delete-orphan"
    )
    payment_methods = relationship("PaymentMethod", back_populates="user")
    audit_logs = relationship("PersonalDataAuditLog", back_populates="user")

    def __init__(self, **kwargs):
        """Initialize user with personal data encryption"""
        encryption_service = EncryptionService(self._get_encryption_key())

        # Encrypt sensitive personal data before storing
        if "phone" in kwargs and kwargs["phone"]:
            kwargs["phone"] = encryption_service.encrypt_personal_data(kwargs["phone"])

        if "mobile_phone" in kwargs and kwargs["mobile_phone"]:
            kwargs["mobile_phone"] = encryption_service.encrypt_personal_data(
                kwargs["mobile_phone"]
            )

        if "date_of_birth" in kwargs and kwargs["date_of_birth"]:
            # Store date of birth as encrypted string
            dob_str = (
                kwargs["date_of_birth"].isoformat()
                if isinstance(kwargs["date_of_birth"], date)
                else str(kwargs["date_of_birth"])
            )
            kwargs["date_of_birth"] = encryption_service.encrypt_personal_data(dob_str)

        super().__init__(**kwargs)

    @property
    def full_name(self) -> str:
        """Get full name - combines personal data fields"""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Get display name for UI - personal data"""
        return self.full_name

    def get_decrypted_phone(self) -> str | None:
        """Decrypt and return phone number - personal data access"""
        if not self.phone:
            return None
        encryption_service = EncryptionService(self._get_encryption_key())
        return encryption_service.decrypt_personal_data(self.phone)

    def get_decrypted_mobile_phone(self) -> str | None:
        """Decrypt and return mobile phone - personal data access"""
        if not self.mobile_phone:
            return None
        encryption_service = EncryptionService(self._get_encryption_key())
        return encryption_service.decrypt_personal_data(self.mobile_phone)

    def get_decrypted_date_of_birth(self) -> date | None:
        """Decrypt and return date of birth - personal data access"""
        if not self.date_of_birth:
            return None
        encryption_service = EncryptionService(self._get_encryption_key())
        dob_str = encryption_service.decrypt_personal_data(self.date_of_birth)
        return date.fromisoformat(dob_str)

    def calculate_age(self) -> int | None:
        """Calculate age from date of birth - derived personal data"""
        dob = self.get_decrypted_date_of_birth()
        if not dob:
            return None

        today = date.today()
        age = today.year - dob.year
        if today.month < dob.month or (
            today.month == dob.month and today.day < dob.day
        ):
            age -= 1
        return age

    def validate_email_format(self) -> bool:
        """Validate email address format - personal data validation"""
        try:
            validate_email(self.email)
            return True
        except EmailNotValidError:
            return False

    def validate_phone_format(self, phone_number: str) -> bool:
        """Validate phone number format - personal data validation"""
        try:
            parsed_number = phonenumbers.parse(phone_number, None)
            return phonenumbers.is_valid_number(parsed_number)
        except:
            return False

    def export_personal_data(self) -> dict[str, Any]:
        """Export all personal data for GDPR data portability (Article 20)"""
        return {
            "basic_information": {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "full_name": self.full_name,
                "email": self.email,
                "date_of_birth": self.get_decrypted_date_of_birth(),
                "age": self.calculate_age(),
                "gender": self.gender,
                "nationality": self.nationality,
            },
            "contact_information": {
                "phone": self.get_decrypted_phone(),
                "mobile_phone": self.get_decrypted_mobile_phone(),
                "addresses": [addr.export_data() for addr in self.addresses],
            },
            "account_information": {
                "email_verified": self.email_verified,
                "created_at": self.created_at.isoformat(),
                "last_login_at": self.last_login_at.isoformat()
                if self.last_login_at
                else None,
            },
            "consent_information": {
                "gdpr_consent_given_at": self.gdpr_consent_given_at.isoformat()
                if self.gdpr_consent_given_at
                else None,
                "marketing_consent": self.marketing_consent,
                "analytics_consent": self.analytics_consent,
            },
        }

    def anonymize_personal_data(self):
        """Anonymize personal data for GDPR right to be forgotten (Article 17)"""
        self.first_name = "ANONYMIZED"
        self.last_name = "USER"
        self.email = f"anonymized_user_{self.id}@deleted.local"
        self.phone = None
        self.mobile_phone = None
        self.date_of_birth = None
        self.gender = None
        self.nationality = None
        self.deleted_at = datetime.utcnow()

    @staticmethod
    def _get_encryption_key():
        """Get encryption key for personal data - placeholder"""
        return "your_encryption_key_here_32_bytes_long"


class Address(Base):
    """
    Address model - stores location personal data

    Contains personal data:
    - Home/work addresses
    - Geographic location information
    - Postal codes and delivery details
    """

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Address type
    address_type = Column(String(20), nullable=False)  # home, work, billing, shipping

    # Address components (personal data)
    street_address = Column(
        Text, nullable=False, comment="Street address - personal data"
    )
    apartment_unit = Column(String(50), comment="Apartment/unit - personal data")
    city = Column(String(100), nullable=False, comment="City - personal data")
    state_province = Column(String(100), comment="State/province - personal data")
    postal_code = Column(
        String(20), nullable=False, comment="Postal code - personal data"
    )
    country = Column(String(100), nullable=False, comment="Country - personal data")

    # Geographic coordinates (derived personal data)
    latitude = Column(String(50), comment="Encrypted latitude coordinate")
    longitude = Column(String(50), comment="Encrypted longitude coordinate")

    # Metadata
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="addresses")

    @property
    def full_address(self) -> str:
        """Get formatted full address - combines personal data"""
        parts = [self.street_address]

        if self.apartment_unit:
            parts.append(f"Unit {self.apartment_unit}")

        parts.extend([self.city, self.state_province, self.postal_code, self.country])

        return ", ".join(filter(None, parts))

    def geocode_address(self) -> tuple[float, float]:
        """Geocode address to coordinates - generates derived personal data"""
        # Placeholder for geocoding service
        # In real implementation, this would call a geocoding API
        return (51.5074, -0.1278)  # London coordinates as example

    def export_data(self) -> dict[str, Any]:
        """Export address data for GDPR compliance"""
        return {
            "address_type": self.address_type,
            "street_address": self.street_address,
            "apartment_unit": self.apartment_unit,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "country": self.country,
            "full_address": self.full_address,
            "is_primary": self.is_primary,
        }


class PaymentMethod(Base):
    """
    Payment method model - stores financial personal data

    Contains sensitive personal/financial data:
    - Credit card information (partial)
    - Billing names and addresses
    - Payment preferences
    """

    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Payment information (sensitive personal data)
    card_type = Column(String(20), nullable=False)  # visa, mastercard, amex
    card_last_four = Column(
        String(4), nullable=False, comment="Last 4 digits - financial data"
    )
    expiry_month = Column(Integer, nullable=False)
    expiry_year = Column(Integer, nullable=False)

    # Cardholder information (personal data)
    cardholder_name = Column(
        String(200), nullable=False, comment="Cardholder name - personal data"
    )
    billing_address_id = Column(Integer, ForeignKey("addresses.id"))

    # Metadata
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="payment_methods")
    billing_address = relationship("Address")

    def get_masked_card_number(self) -> str:
        """Get masked card number for display - protects financial data"""
        return f"**** **** **** {self.card_last_four}"

    def is_expired(self) -> bool:
        """Check if payment method is expired"""
        current_date = datetime.now()
        expiry_date = datetime(self.expiry_year, self.expiry_month, 1)
        return current_date > expiry_date


class PersonalDataAuditLog(Base):
    """
    Audit log for personal data access and modifications

    Tracks:
    - Who accessed personal data
    - When personal data was modified
    - What data was accessed/changed
    - Legal basis for processing
    """

    __tablename__ = "personal_data_audit_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Audit details
    action = Column(String(50), nullable=False)  # access, modify, delete, export
    accessed_fields = Column(
        Text, comment="JSON array of accessed personal data fields"
    )
    legal_basis = Column(String(50), comment="GDPR legal basis for processing")
    processing_purpose = Column(String(200), comment="Purpose of data processing")

    # Session information
    accessed_by_user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(45), comment="IP address - potentially identifying")
    user_agent = Column(Text, comment="Browser user agent")
    session_id = Column(String(255))

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="audit_logs")
    accessed_by = relationship("User", foreign_keys=[accessed_by_user_id])


class DataRetentionPolicy:
    """Data retention and deletion policies for personal data"""

    # Retention periods by data category (in days)
    RETENTION_PERIODS = {
        PersonalDataCategory.BASIC_IDENTITY: 2555,  # 7 years
        PersonalDataCategory.CONTACT_INFO: 1095,  # 3 years
        PersonalDataCategory.FINANCIAL: 2555,  # 7 years (legal requirement)
        PersonalDataCategory.DEMOGRAPHIC: 1095,  # 3 years
        PersonalDataCategory.HEALTH: 3650,  # 10 years (special category)
        PersonalDataCategory.BIOMETRIC: 1095,  # 3 years (special category)
    }

    @classmethod
    def should_delete_user_data(cls, user: User) -> bool:
        """Determine if user's personal data should be deleted"""
        if user.deleted_at:
            # Already marked for deletion
            return True

        if user.gdpr_consent_withdrawn_at:
            # User withdrew consent - delete immediately unless other legal basis exists
            return True

        if user.data_retention_until and user.data_retention_until < date.today():
            # Retention period expired
            return True

        # Check for inactivity-based deletion
        if user.last_login_at:
            inactive_days = (datetime.utcnow() - user.last_login_at).days
            if inactive_days > 730:  # 2 years of inactivity
                return True

        return False


# Example functions that process personal data


def search_users_by_email(email_pattern: str) -> list[User]:
    """Search for users by email - processes personal data"""
    # This function processes personal data (email addresses)
    # Legal basis: legitimate interests (system administration)
    return User.query.filter(User.email.ilike(f"%{email_pattern}%")).all()


def find_users_by_phone(phone_number: str) -> list[User]:
    """Find users by phone number - processes personal data"""
    # This would need to encrypt the search term and compare
    encryption_service = EncryptionService("encryption_key_here")
    encrypted_phone = encryption_service.encrypt_personal_data(phone_number)
    return User.query.filter(User.phone == encrypted_phone).all()


def generate_user_report(user_id: int) -> dict[str, Any]:
    """Generate comprehensive user report - accesses all personal data"""
    user = User.query.get(user_id)
    if not user:
        return None

    return {
        "personal_info": {
            "name": user.full_name,  # Personal data
            "email": user.email,  # Personal data
            "phone": user.get_decrypted_phone(),  # Personal data
            "age": user.calculate_age(),  # Derived personal data
            "addresses": [
                addr.full_address for addr in user.addresses
            ],  # Personal data
        },
        "account_metrics": {
            "member_since": user.created_at,
            "last_active": user.last_login_at,
            "total_orders": len(user.orders) if hasattr(user, "orders") else 0,
        },
    }


def validate_personal_data_formats(user_data: dict[str, Any]) -> dict[str, bool]:
    """Validate personal data formats before processing"""
    validations = {}

    # Email validation
    if "email" in user_data:
        try:
            validate_email(user_data["email"])
            validations["email"] = True
        except EmailNotValidError:
            validations["email"] = False

    # Phone validation
    if "phone" in user_data:
        try:
            parsed = phonenumbers.parse(user_data["phone"], None)
            validations["phone"] = phonenumbers.is_valid_number(parsed)
        except:
            validations["phone"] = False

    # Date of birth validation
    if "date_of_birth" in user_data:
        try:
            dob = datetime.strptime(user_data["date_of_birth"], "%Y-%m-%d").date()
            validations["date_of_birth"] = dob < date.today()
        except ValueError:
            validations["date_of_birth"] = False

    return validations


# Test data and examples for personal data detection

SAMPLE_USER_DATA = {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@example.com",
    "phone": "+44 20 7946 0958",
    "date_of_birth": "1987-03-15",
    "addresses": [
        {
            "street_address": "42 Baker Street",
            "city": "London",
            "postal_code": "SW1A 1AA",
            "country": "United Kingdom",
        }
    ],
}

SAMPLE_CONTACT_INFO = {
    "emergency_contact": {
        "name": "Michael Johnson",
        "relationship": "Spouse",
        "phone": "+44 7700 900123",
        "email": "michael.johnson@email.com",
    },
    "next_of_kin": {
        "name": "Emma Johnson",
        "relationship": "Daughter",
        "phone": "07700 900456",
        "address": "42 Baker Street, London SW1A 1AA",
    },
}

# Regular expressions for personal data detection
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
UK_PHONE_REGEX = r"(\+44\s?7\d{3}\s?\d{6}|0\d{4}\s?\d{6}|\+44\s?20\s?\d{4}\s?\d{4})"
POSTCODE_REGEX = r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][ABD-HJLNP-UW-Z]{2}\b"
