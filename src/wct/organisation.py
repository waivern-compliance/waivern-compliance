"""Organisation configuration loading for GDPR Article 30(1)(a) compliance.

This module handles loading organisation metadata from config/organisation.yaml
to include data controller information in WCT analysis exports as required
by GDPR Article 30(1)(a) for records of processing activities.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import yaml
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from wct.utils import get_project_root

logger = logging.getLogger(__name__)

# Default organisation config file location
ORGANISATION_CONFIG_PATH: Final[Path] = Path("config") / "organisation.yaml"


class DataControllerConfig(BaseModel):
    """Data controller information for GDPR compliance."""

    name: str = Field(description="Legal name of the data controller organisation")
    company_nr: str | None = Field(
        default=None, description="Company registration number"
    )
    address: str = Field(description="Registered address of the data controller")
    contact_email: str = Field(description="Contact email for data protection queries")
    trading_name: str | None = Field(
        default=None, description="Trading name if different from legal name"
    )
    jurisdictions: list[str] = Field(
        default_factory=list,
        description="List of jurisdictions where the controller operates",
    )


class JointControllerConfig(BaseModel):
    """Joint controller information if applicable."""

    name: str = Field(description="Name of the joint controller")
    processing_purposes: str = Field(
        description="Description of joint processing purposes"
    )
    contact_email: str = Field(description="Contact email for the joint controller")
    contact_address: str = Field(description="Contact address for the joint controller")


class EuUkRepresentativeConfig(BaseModel):
    """EU/UK representative information for non-EU controllers."""

    company_name: str = Field(description="Name of the EU/UK representative")
    contact_email: str = Field(description="Contact email for the representative")
    contact_address: str = Field(description="Contact address for the representative")


class DpoConfig(BaseModel):
    """Data Protection Officer information."""

    name: str = Field(description="Name of the Data Protection Officer")
    contact_email: str = Field(description="DPO contact email")
    contact_address: str = Field(description="DPO contact address")


class PrivacyContactConfig(BaseModel):
    """Privacy contact information for data subjects."""

    email: str = Field(
        description="Email for privacy-related queries from data subjects"
    )


class DataRetentionConfig(BaseModel):
    """Data retention policy information."""

    general_rule: str = Field(description="General data retention rule")
    exceptions: dict[str, str] = Field(
        default_factory=dict,
        description="Specific retention exceptions for different data categories",
    )


class OrganisationConfig(BaseModel):
    """Complete organisation configuration for GDPR compliance.

    This model represents the organisation metadata required for GDPR
    Article 30(1)(a) compliance in WCT analysis exports.
    """

    data_controller: DataControllerConfig = Field(
        description="Data controller information (required for GDPR Article 30(1)(a))"
    )
    joint_controller: JointControllerConfig | None = Field(
        default=None, description="Joint controller information if applicable"
    )
    eu_uk_representative: EuUkRepresentativeConfig | None = Field(
        default=None,
        description="EU/UK representative for controllers outside EU/UK jurisdiction",
    )
    dpo: DpoConfig | None = Field(
        default=None, description="Data Protection Officer information"
    )
    privacy_contact: PrivacyContactConfig | None = Field(
        default=None, description="Privacy contact for data subjects"
    )
    data_retention: DataRetentionConfig | None = Field(
        default=None, description="Data retention policy information"
    )

    @model_validator(mode="after")
    def validate_controller_requirements(self) -> Self:
        """Validate GDPR Article 30(1)(a) requirements."""
        # Ensure data controller has minimum required information
        if not self.data_controller.name.strip():
            raise ValueError("Data controller name is required for GDPR compliance")
        if not self.data_controller.address.strip():
            raise ValueError("Data controller address is required for GDPR compliance")
        if not self.data_controller.contact_email.strip():
            raise ValueError(
                "Data controller contact email is required for GDPR compliance"
            )

        return self

    def to_export_metadata(self) -> dict[str, Any]:
        """Convert to dictionary format suitable for analysis export metadata.

        Returns:
            Dictionary containing organisation information formatted for JSON export

        """
        export_data: dict[str, Any] = {
            "data_controller": {
                "name": self.data_controller.name,
                "address": self.data_controller.address,
                "contact_email": self.data_controller.contact_email,
            }
        }

        # Add optional data controller fields
        if self.data_controller.company_nr:
            export_data["data_controller"]["company_nr"] = (
                self.data_controller.company_nr
            )
        if self.data_controller.trading_name:
            export_data["data_controller"]["trading_name"] = (
                self.data_controller.trading_name
            )
        if self.data_controller.jurisdictions:
            export_data["data_controller"]["jurisdictions"] = (
                self.data_controller.jurisdictions
            )

        # Add joint controller if present
        if self.joint_controller:
            export_data["joint_controller"] = {
                "name": self.joint_controller.name,
                "processing_purposes": self.joint_controller.processing_purposes,
                "contact_email": self.joint_controller.contact_email,
                "contact_address": self.joint_controller.contact_address,
            }

        # Add EU/UK representative if present
        if self.eu_uk_representative:
            export_data["eu_uk_representative"] = {
                "company_name": self.eu_uk_representative.company_name,
                "contact_email": self.eu_uk_representative.contact_email,
                "contact_address": self.eu_uk_representative.contact_address,
            }

        # Add DPO if present
        if self.dpo:
            export_data["dpo"] = {
                "name": self.dpo.name,
                "contact_email": self.dpo.contact_email,
                "contact_address": self.dpo.contact_address,
            }

        # Add privacy contact if present
        if self.privacy_contact:
            export_data["privacy_contact"] = {"email": self.privacy_contact.email}

        # Add data retention if present
        if self.data_retention:
            export_data["data_retention"] = {
                "general_rule": self.data_retention.general_rule,
                "exceptions": self.data_retention.exceptions,
            }

        return export_data


class OrganisationLoader:
    """Loads organisation configuration from YAML files."""

    @classmethod
    def load(cls) -> OrganisationConfig | None:
        """Load organisation config from the project root directory.

        Searches for config/organisation.yaml relative to the project root.

        Returns:
            OrganisationConfig instance if found and valid, None otherwise

        """
        config_path = None
        try:
            project_root = get_project_root()
            config_path = project_root / ORGANISATION_CONFIG_PATH

            if not config_path.exists():
                logger.info(
                    f"Organisation config not found at {config_path}. "
                    "Analysis exports will not include organisation metadata."
                )
                return None

            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Pydantic will handle validation and provide clear error messages
            org_config = OrganisationConfig.model_validate(data)
            logger.info(
                f"Loaded organisation config for: {org_config.data_controller.name}"
            )
            return org_config

        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML in {config_path}: {e}")
            return None
        except Exception as e:
            logger.warning(
                f"Could not determine project root or load organisation config: {e}"
            )
            return None


class OrganisationConfigError(Exception):
    """Exception raised for organisation configuration errors."""

    pass
