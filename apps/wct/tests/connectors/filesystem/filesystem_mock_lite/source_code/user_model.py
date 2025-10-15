"""
Data Model - User and Personal Data Management

This module handles personal data storage and processing including:
- User profiles with personal information
- Address management
- GDPR compliance features

Contains personal data fields:
- Names, emails, phone numbers
- Addresses and location data
- Date of birth and age calculation
"""

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PersonalDataCategory(Enum):
    """Categories of personal data for GDPR compliance"""

    BASIC_IDENTITY = "basic_identity"  # Name, email
    CONTACT_INFO = "contact_info"  # Phone, address
    DEMOGRAPHIC = "demographic"  # Age, gender, DOB
    FINANCIAL = "financial"  # Payment info, income


class User(Base):
    """
    User model - stores personal data

    Contains personal information subject to GDPR:
    - Identity data: first_name, last_name, email
    - Contact data: phone, addresses
    - Demographic data: date_of_birth, gender
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

    # Demographic data (personal data)
    date_of_birth = Column(Text, comment="Encrypted date of birth - personal data")
    gender = Column(String(20), comment="Gender - personal data")
    nationality = Column(String(100), comment="Nationality - personal data")

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def full_name(self) -> str:
        """Get full name - combines personal data fields"""
        return f"{self.first_name} {self.last_name}"

    def export_personal_data(self) -> dict[str, Any]:
        """Export all personal data for GDPR data portability (Article 20)"""
        return {
            "basic_information": {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "email": self.email,
                "date_of_birth": self.date_of_birth,
                "gender": self.gender,
                "nationality": self.nationality,
            },
            "contact_information": {
                "phone": self.phone,
            },
        }


def search_users_by_email(email_pattern: str) -> list[User]:
    """Search for users by email - processes personal data"""
    return User.query.filter(User.email.ilike(f"%{email_pattern}%")).all()


def generate_user_report(user_id: int) -> dict[str, Any]:
    """Generate comprehensive user report - accesses all personal data"""
    user = User.query.get(user_id)
    if not user:
        return None

    return {
        "personal_info": {
            "name": user.full_name,  # Personal data
            "email": user.email,  # Personal data
            "phone": user.phone,  # Personal data
        },
    }


# Test data and examples for personal data detection
SAMPLE_USER_DATA = {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@example.com",
    "phone": "+44 20 7946 0958",
    "date_of_birth": "1987-03-15",
}

SAMPLE_CONTACT_INFO = {
    "emergency_contact": {
        "name": "Michael Johnson",
        "phone": "+44 7700 900123",
        "email": "michael.johnson@email.com",
    },
}
