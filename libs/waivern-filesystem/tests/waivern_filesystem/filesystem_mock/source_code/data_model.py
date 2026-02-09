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

Third-Party Service Integrations:
- OpenAI: AI-powered personal data classification and analysis
- LangChain: LLM orchestration for document processing
- Pinecone: Vector database for user data embeddings
- AWS (boto3): S3 storage and cloud infrastructure
- SimplePractice: Healthcare practice management integration
- Cliniko: Patient record management system
"""
# pyright: reportMissingImports=false, reportDeprecated=false
# pyright: reportGeneralTypeIssues=false, reportArgumentType=false
# pyright: reportAttributeAccessIssue=false, reportCallIssue=false
# pyright: reportUntypedBaseClass=false
# Test mock file - SQLAlchemy Column types have known type stub issues:
# - Column.__bool__() returns Never (can't use in conditionals)
# - Column types can't be passed to functions expecting Python types
# - Missing type stubs for .ilike() and other SQLAlchemy query methods
# Also imports third-party libs (phonenumbers, email_validator, cryptography,
# openai, langchain, pinecone, boto3, etc.) that aren't actual dependencies.
# These targeted ignores are necessary for test fixture code.

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

import boto3  # pyright: ignore[reportMissingImports]

# Third-party service integrations
import openai  # pyright: ignore[reportMissingImports]
import phonenumbers  # pyright: ignore[reportMissingImports]
import pinecone  # pyright: ignore[reportMissingImports]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingImports]
from cryptography.fernet import Fernet  # pyright: ignore[reportMissingImports]
from email_validator import (  # pyright: ignore[reportMissingImports]
    EmailNotValidError,
    validate_email,
)
from langchain.chains import LLMChain  # pyright: ignore[reportMissingImports]
from langchain.embeddings import (
    OpenAIEmbeddings,  # pyright: ignore[reportMissingImports]
)
from langchain.llms import (
    OpenAI as LangChainOpenAI,  # pyright: ignore[reportMissingImports]
)
from langchain.prompts import PromptTemplate  # pyright: ignore[reportMissingImports]
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,  # pyright: ignore[reportMissingImports]
)
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

    def encrypt_personal_data(self, data: str) -> str | None:
        """Encrypt personal data field"""
        if not data:
            return None
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_personal_data(self, encrypted_data: str) -> str | None:
        """Decrypt personal data field"""
        if not encrypted_data:
            return None
        return self.fernet.decrypt(encrypted_data.encode()).decode()


class AWSStorageService:
    """AWS S3 storage service for personal data documents and exports.

    Handles secure storage of personal data exports, identity documents,
    and healthcare records in encrypted S3 buckets.
    """

    def __init__(self, region: str = "eu-west-2"):
        self.s3_client = boto3.client("s3", region_name=region)
        self.documents_bucket = "customer-documents-eu"
        self.exports_bucket = "gdpr-data-exports-eu"
        self.healthcare_bucket = "healthcare-records-eu"

    def upload_personal_data_export(
        self, user_id: int, export_data: dict[str, Any]
    ) -> str:
        """Upload GDPR data export to S3 with encryption"""
        import json

        key = f"exports/user_{user_id}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_export.json"

        self.s3_client.put_object(
            Bucket=self.exports_bucket,
            Key=key,
            Body=json.dumps(export_data, default=str),
            ContentType="application/json",
            ServerSideEncryption="aws:kms",
            Metadata={
                "user_id": str(user_id),
                "export_type": "gdpr_data_portability",
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        return f"s3://{self.exports_bucket}/{key}"

    def upload_identity_document(
        self, user_id: int, document_bytes: bytes, document_type: str, filename: str
    ) -> str:
        """Upload identity document (passport, driving licence) to S3"""
        key = f"users/{user_id}/identity/{document_type}/{filename}"

        self.s3_client.put_object(
            Bucket=self.documents_bucket,
            Key=key,
            Body=document_bytes,
            ServerSideEncryption="aws:kms",
            Metadata={
                "user_id": str(user_id),
                "document_type": document_type,
                "uploaded_at": datetime.utcnow().isoformat(),
            },
        )
        return f"s3://{self.documents_bucket}/{key}"

    def upload_healthcare_record(
        self, patient_id: str, record_data: bytes, record_type: str
    ) -> str:
        """Upload healthcare record to dedicated encrypted S3 bucket"""
        key = f"patients/{patient_id}/records/{record_type}/{datetime.utcnow().strftime('%Y%m%d')}.json"

        self.s3_client.put_object(
            Bucket=self.healthcare_bucket,
            Key=key,
            Body=record_data,
            ServerSideEncryption="aws:kms",
            Metadata={
                "patient_id": patient_id,
                "record_type": record_type,
                "uploaded_at": datetime.utcnow().isoformat(),
            },
        )
        return f"s3://{self.healthcare_bucket}/{key}"

    def delete_user_data(self, user_id: int) -> int:
        """Delete all user data from S3 (GDPR right to erasure)"""
        deleted_count = 0
        for bucket in [self.documents_bucket, self.exports_bucket]:
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=bucket, Prefix=f"users/{user_id}/"
                )
                if "Contents" in response:
                    objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
                    self.s3_client.delete_objects(
                        Bucket=bucket, Delete={"Objects": objects}
                    )
                    deleted_count += len(objects)
            except ClientError as e:
                print(f"S3 cleanup error for bucket {bucket}: {e}")
        return deleted_count

    def generate_presigned_download_url(
        self, bucket: str, key: str, expiry_seconds: int = 86400
    ) -> str:
        """Generate pre-signed URL for secure data download"""
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )


class AIDataClassificationService:
    """AI-powered personal data classification using OpenAI and LangChain.

    Uses LLM capabilities to:
    - Classify personal data categories automatically
    - Detect sensitive data in unstructured text
    - Generate privacy impact assessments
    - Create vector embeddings for data subject access requests
    """

    def __init__(self):
        # Initialise OpenAI client for GPT-4 classification
        openai.api_key = "sk-..."  # Loaded from environment in production
        self.openai_client = openai.OpenAI()

        # Initialise LangChain with OpenAI LLM
        self.llm = LangChainOpenAI(
            model_name="gpt-4",
            temperature=0.0,
            max_tokens=2000,
        )

        # Initialise OpenAI embeddings for vector search
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
        )

        # Initialise Pinecone vector database for data search
        pinecone.init(
            api_key="pcsk_...",  # Loaded from environment in production
            environment="eu-west1-gcp",
        )
        self.pinecone_index = pinecone.Index("user-data-embeddings")

        # Text splitter for processing large documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )

    def classify_personal_data(self, text: str) -> dict[str, Any]:
        """Use OpenAI GPT-4 to classify personal data categories in text.

        Sends text content to OpenAI for analysis - text may contain
        personal data (names, emails, addresses, health information).
        """
        classification_prompt = PromptTemplate(
            input_variables=["text"],
            template="""Analyse the following text and identify any personal data present.
            Classify each piece of personal data into GDPR categories.

            Text: {text}

            Return a JSON object with:
            - personal_data_found: list of identified personal data items
            - categories: GDPR data categories (basic_identity, contact_info, etc.)
            - sensitivity_level: low, medium, high, or special_category
            - recommended_legal_basis: appropriate GDPR Article 6 legal basis
            """,
        )

        chain = LLMChain(llm=self.llm, prompt=classification_prompt)
        result = chain.run(text=text)

        return {
            "classification": result,
            "model": "gpt-4",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def generate_data_subject_embeddings(
        self, user_id: int, personal_data: dict[str, Any]
    ) -> str:
        """Generate vector embeddings of user's personal data for DSAR search.

        Creates embeddings using OpenAI and stores in Pinecone vector database.
        This enables efficient data subject access request (DSAR) processing.

        Personal data (names, emails, etc.) is sent to OpenAI for embedding
        and stored in Pinecone for vector similarity search.
        """
        import json

        # Convert personal data to text for embedding
        data_text = json.dumps(personal_data, default=str)
        chunks = self.text_splitter.split_text(data_text)

        # Generate embeddings via OpenAI
        chunk_embeddings = self.embeddings.embed_documents(chunks)

        # Store embeddings in Pinecone with user metadata
        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
            vectors.append(
                {
                    "id": f"user_{user_id}_chunk_{i}",
                    "values": embedding,
                    "metadata": {
                        "user_id": user_id,
                        "chunk_index": i,
                        "text": chunk[:500],  # Store truncated text for reference
                        "created_at": datetime.utcnow().isoformat(),
                    },
                }
            )

        self.pinecone_index.upsert(vectors=vectors)
        return f"Stored {len(vectors)} embedding vectors for user {user_id}"

    def search_user_data(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Search for user personal data using vector similarity.

        Used for data subject access requests (DSAR) - finds all personal
        data related to a specific individual across the system.
        """
        query_embedding = self.embeddings.embed_query(query)

        results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )

        return [
            {
                "user_id": match["metadata"].get("user_id"),
                "text": match["metadata"].get("text"),
                "similarity_score": match["score"],
            }
            for match in results["matches"]
        ]

    def delete_user_embeddings(self, user_id: int) -> None:
        """Delete user's vector embeddings from Pinecone (GDPR erasure)"""
        self.pinecone_index.delete(filter={"user_id": {"$eq": user_id}})

    def generate_privacy_impact_assessment(
        self, data_processing_description: str
    ) -> dict[str, Any]:
        """Use GPT-4 to generate a Data Protection Impact Assessment (DPIA).

        Analyses data processing activities and generates GDPR-compliant
        impact assessment recommendations.
        """
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a GDPR compliance expert. Analyse the data processing "
                    "activity and generate a Data Protection Impact Assessment (DPIA).",
                },
                {
                    "role": "user",
                    "content": f"Generate a DPIA for the following data processing activity:\n\n"
                    f"{data_processing_description}",
                },
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        return {
            "assessment": response.choices[0].message.content,
            "model": "gpt-4",
            "generated_at": datetime.utcnow().isoformat(),
        }


class HealthcareIntegrationService:
    """Integration service for healthcare practice management systems.

    Syncs patient personal data between the application and healthcare
    platforms (SimplePractice, Cliniko) for GDPR-compliant health data
    processing under Article 9 (special category data).
    """

    def __init__(self):
        self.simplepractice_api_key = "sp_..."  # Loaded from environment
        self.simplepractice_base_url = "https://api.simplepractice.com/v1"
        self.cliniko_api_key = "ck_..."  # Loaded from environment
        self.cliniko_base_url = "https://api.cliniko.com/v1"
        self.aws_storage = AWSStorageService()

    def sync_patient_to_simplepractice(
        self, patient_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Sync patient personal and health data to SimplePractice.

        Shares special category data (health records) with SimplePractice
        platform. Requires explicit patient consent under GDPR Article 9.

        Personal data shared:
        - Patient name, date of birth, contact information
        - Health conditions and treatment history
        - Insurance details
        """
        import requests  # pyright: ignore[reportMissingImports]

        headers = {
            "Authorization": f"Bearer {self.simplepractice_api_key}",
            "Content-Type": "application/json",
        }

        # Create or update patient in SimplePractice
        response = requests.post(
            f"{self.simplepractice_base_url}/clients",
            headers=headers,
            json={
                "first_name": patient_data["first_name"],
                "last_name": patient_data["last_name"],
                "email": patient_data["email"],
                "phone_number": patient_data.get("phone"),
                "date_of_birth": patient_data.get("date_of_birth"),
                "gender": patient_data.get("gender"),
                "address": {
                    "street": patient_data.get("street_address"),
                    "city": patient_data.get("city"),
                    "state": patient_data.get("state"),
                    "zip": patient_data.get("postal_code"),
                    "country": patient_data.get("country"),
                },
                "emergency_contact": {
                    "name": patient_data.get("emergency_contact_name"),
                    "phone": patient_data.get("emergency_contact_phone"),
                    "relationship": patient_data.get("emergency_contact_relationship"),
                },
                "insurance": {
                    "provider": patient_data.get("insurance_provider"),
                    "member_id": patient_data.get("insurance_member_id"),
                },
            },
            timeout=30,
        )

        return response.json()

    def sync_patient_to_cliniko(self, patient_data: dict[str, Any]) -> dict[str, Any]:
        """Sync patient personal and health data to Cliniko.

        Shares special category data (health records) with Cliniko
        patient management system. Requires explicit consent.

        Personal data shared:
        - Patient demographics (name, DOB, gender)
        - Contact details (email, phone, address)
        - Medical history and treatment notes
        """
        import requests  # pyright: ignore[reportMissingImports]

        headers = {
            "Authorization": f"Bearer {self.cliniko_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CustomerPortal/2.3.1",
        }

        response = requests.post(
            f"{self.cliniko_base_url}/patients",
            headers=headers,
            json={
                "first_name": patient_data["first_name"],
                "last_name": patient_data["last_name"],
                "email": patient_data["email"],
                "date_of_birth": patient_data.get("date_of_birth"),
                "gender_identity": patient_data.get("gender"),
                "patient_phone_numbers": [
                    {"phone_type": "Mobile", "number": patient_data.get("phone")},
                ],
                "address": f"{patient_data.get('street_address', '')}, "
                f"{patient_data.get('city', '')}, "
                f"{patient_data.get('postal_code', '')}",
                "medicare_reference_number": patient_data.get("national_health_id"),
            },
            timeout=30,
        )

        return response.json()

    def fetch_patient_records_from_cliniko(
        self, cliniko_patient_id: str
    ) -> dict[str, Any]:
        """Fetch patient treatment records from Cliniko.

        Retrieves special category health data including:
        - Treatment notes and clinical observations
        - Appointment history
        - Practitioner notes containing personal health information
        """
        import requests  # pyright: ignore[reportMissingImports]

        headers = {
            "Authorization": f"Bearer {self.cliniko_api_key}",
            "Accept": "application/json",
        }

        # Fetch patient details (personal data)
        patient_response = requests.get(
            f"{self.cliniko_base_url}/patients/{cliniko_patient_id}",
            headers=headers,
            timeout=30,
        )

        # Fetch treatment notes (special category health data)
        notes_response = requests.get(
            f"{self.cliniko_base_url}/patients/{cliniko_patient_id}/treatment_notes",
            headers=headers,
            timeout=30,
        )

        patient = patient_response.json()
        notes = notes_response.json()

        # Store healthcare records in encrypted S3 bucket
        import json

        self.aws_storage.upload_healthcare_record(
            patient_id=cliniko_patient_id,
            record_data=json.dumps(
                {"patient": patient, "treatment_notes": notes}, default=str
            ).encode(),
            record_type="cliniko_sync",
        )

        return {
            "patient": patient,
            "treatment_notes": notes.get("treatment_notes", []),
            "synced_at": datetime.utcnow().isoformat(),
        }

    def delete_patient_from_platforms(
        self, patient_data: dict[str, Any]
    ) -> dict[str, bool]:
        """Delete patient data from all healthcare platforms (GDPR erasure).

        Removes personal and health data from:
        - SimplePractice patient records
        - Cliniko patient records
        - AWS S3 healthcare records bucket
        """
        results = {}

        import requests  # pyright: ignore[reportMissingImports]

        # Delete from SimplePractice
        if patient_data.get("simplepractice_id"):
            try:
                requests.delete(
                    f"{self.simplepractice_base_url}/clients/{patient_data['simplepractice_id']}",
                    headers={"Authorization": f"Bearer {self.simplepractice_api_key}"},
                    timeout=30,
                )
                results["simplepractice"] = True
            except Exception:
                results["simplepractice"] = False

        # Delete from Cliniko
        if patient_data.get("cliniko_id"):
            try:
                requests.delete(
                    f"{self.cliniko_base_url}/patients/{patient_data['cliniko_id']}",
                    headers={"Authorization": f"Bearer {self.cliniko_api_key}"},
                    timeout=30,
                )
                results["cliniko"] = True
            except Exception:
                results["cliniko"] = False

        return results


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

    # Third-party service identifiers
    simplepractice_client_id = Column(String(255), comment="SimplePractice patient ID")
    cliniko_patient_id = Column(String(255), comment="Cliniko patient ID")

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
        except Exception:
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
            "third_party_identifiers": {
                "simplepractice_client_id": self.simplepractice_client_id,
                "cliniko_patient_id": self.cliniko_patient_id,
            },
        }

    def export_and_store_to_s3(self) -> str:
        """Export personal data and upload to AWS S3 for secure delivery"""
        storage = AWSStorageService()
        export_data = self.export_personal_data()
        return storage.upload_personal_data_export(self.id, export_data)

    def classify_personal_data_with_ai(self) -> dict[str, Any]:
        """Use AI to classify personal data categories for this user"""
        classifier = AIDataClassificationService()
        import json

        user_data_text = json.dumps(self.export_personal_data(), default=str)
        return classifier.classify_personal_data(user_data_text)

    def generate_user_embeddings(self) -> str:
        """Generate vector embeddings for DSAR search using Pinecone"""
        classifier = AIDataClassificationService()
        return classifier.generate_data_subject_embeddings(
            self.id, self.export_personal_data()
        )

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
        self.simplepractice_client_id = None
        self.cliniko_patient_id = None
        self.deleted_at = datetime.utcnow()

    def delete_from_all_services(self) -> dict[str, bool]:
        """Delete user data from all third-party services (GDPR erasure).

        Removes personal data from:
        - AWS S3 (documents and exports)
        - Pinecone (vector embeddings)
        - SimplePractice (healthcare records)
        - Cliniko (patient records)
        """
        results: dict[str, bool] = {}

        # Delete from AWS S3
        try:
            storage = AWSStorageService()
            storage.delete_user_data(self.id)
            results["aws_s3"] = True
        except Exception:
            results["aws_s3"] = False

        # Delete from Pinecone vector database
        try:
            classifier = AIDataClassificationService()
            classifier.delete_user_embeddings(self.id)
            results["pinecone"] = True
        except Exception:
            results["pinecone"] = False

        # Delete from healthcare platforms
        healthcare = HealthcareIntegrationService()
        healthcare_results = healthcare.delete_patient_from_platforms(
            {
                "simplepractice_id": self.simplepractice_client_id,
                "cliniko_id": self.cliniko_patient_id,
            }
        )
        results.update(healthcare_results)

        return results

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

    # Third-party service data sharing
    data_shared_with = Column(
        String(200),
        comment="Third-party services that received personal data",
    )

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


def generate_user_report(user_id: int) -> dict[str, Any] | None:
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


def search_users_with_ai(query: str) -> list[dict[str, Any]]:
    """Search for users using AI-powered vector similarity search.

    Uses OpenAI embeddings and Pinecone to find users matching a natural
    language query. Useful for data subject access requests (DSAR).
    """
    classifier = AIDataClassificationService()
    return classifier.search_user_data(query)


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
        except Exception:
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

SAMPLE_HEALTHCARE_PATIENT = {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "email": "sarah.johnson@example.com",
    "phone": "+44 20 7946 0958",
    "date_of_birth": "1987-03-15",
    "gender": "female",
    "street_address": "42 Baker Street",
    "city": "London",
    "postal_code": "SW1A 1AA",
    "country": "United Kingdom",
    "emergency_contact_name": "Michael Johnson",
    "emergency_contact_phone": "+44 7700 900123",
    "emergency_contact_relationship": "Spouse",
    "insurance_provider": "BUPA",
    "insurance_member_id": "BUPA-12345678",
    "national_health_id": "NHS-943-215-7890",
}

# Regular expressions for personal data detection
EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
UK_PHONE_REGEX = r"(\+44\s?7\d{3}\s?\d{6}|0\d{4}\s?\d{6}|\+44\s?20\s?\d{4}\s?\d{4})"
POSTCODE_REGEX = r"\b[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][ABD-HJLNP-UW-Z]{2}\b"
