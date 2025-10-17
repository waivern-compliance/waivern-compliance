"""Tests for WCT organisation configuration functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from wct.organisation import (
    OrganisationConfig,
    OrganisationLoader,
)


class TestOrganisationConfig:
    """Test OrganisationConfig Pydantic model validation."""

    def test_valid_organisation_config(self):
        """Test that valid organisation config passes validation."""
        config_data = {
            "data_controller": {
                "name": "Test Company Ltd",
                "address": "123 Test Street, Test City, TC1 2AB",
                "contact_email": "privacy@testcompany.com",
                "company_nr": "12345678",
                "jurisdictions": ["EU", "UK"],
            },
            "dpo": {
                "name": "Jane Smith",
                "contact_email": "dpo@testcompany.com",
                "contact_address": "123 Test Street, Test City, TC1 2AB",
            },
        }

        config = OrganisationConfig.model_validate(config_data)

        assert config.data_controller.name == "Test Company Ltd"
        assert config.data_controller.contact_email == "privacy@testcompany.com"
        assert config.dpo is not None
        assert config.dpo.name == "Jane Smith"

    def test_minimal_valid_organisation_config(self):
        """Test organisation config with only required fields."""
        config_data = {
            "data_controller": {
                "name": "Minimal Company",
                "address": "456 Minimal Ave",
                "contact_email": "contact@minimal.com",
            }
        }

        config = OrganisationConfig.model_validate(config_data)

        assert config.data_controller.name == "Minimal Company"
        assert config.joint_controller is None
        assert config.dpo is None

    def test_missing_required_fields_raises_validation_error(self):
        """Test that missing required fields raise validation errors."""
        config_data = {
            "data_controller": {
                "name": "Incomplete Company",
                # Missing address and contact_email
            }
        }

        with pytest.raises(Exception):  # Pydantic ValidationError
            OrganisationConfig.model_validate(config_data)

    def test_empty_required_fields_raise_validation_error(self):
        """Test that empty required fields raise validation errors."""
        config_data = {
            "data_controller": {
                "name": "",  # Empty required field
                "address": "123 Test Street",
                "contact_email": "test@example.com",
            }
        }

        with pytest.raises(ValueError, match="Data controller name is required"):
            OrganisationConfig.model_validate(config_data)

    def test_to_export_metadata_includes_all_sections(self):
        """Test that to_export_metadata includes all configured sections."""
        config_data = {
            "data_controller": {
                "name": "Full Company Ltd",
                "address": "789 Full Street",
                "contact_email": "full@company.com",
                "company_nr": "987654321",
                "jurisdictions": ["EU"],
            },
            "joint_controller": {
                "name": "Joint Partner",
                "processing_purposes": "Shared analytics",
                "contact_email": "joint@partner.com",
                "contact_address": "Joint Address",
            },
            "dpo": {
                "name": "Data Officer",
                "contact_email": "dpo@company.com",
                "contact_address": "DPO Address",
            },
        }

        config = OrganisationConfig.model_validate(config_data)
        export_data = config.to_export_metadata()

        assert "data_controller" in export_data
        assert export_data["data_controller"]["name"] == "Full Company Ltd"
        assert export_data["data_controller"]["company_nr"] == "987654321"

        assert "joint_controller" in export_data
        assert export_data["joint_controller"]["name"] == "Joint Partner"

        assert "dpo" in export_data
        assert export_data["dpo"]["name"] == "Data Officer"

    def test_to_export_metadata_with_all_optional_sections(self):
        """Test that to_export_metadata handles all optional organisation sections correctly."""
        config_data = {
            "data_controller": {
                "name": "Complete Company Ltd",
                "address": "Complete Address",
                "contact_email": "complete@company.com",
                "company_nr": "12345",
                "trading_name": "Complete Corp",
                "jurisdictions": ["EU", "UK"],
            },
            "joint_controller": {
                "name": "Joint Partner",
                "processing_purposes": "Joint processing",
                "contact_email": "joint@partner.com",
                "contact_address": "Joint Address",
            },
            "representatives": [
                {
                    "company_name": "EU Rep Ltd",
                    "company_jurisdiction": "EU",
                    "contact_email": "eurep@company.com",
                    "contact_address": "EU Rep Address",
                    "representative_jurisdiction": "EU",
                }
            ],
            "dpo": {
                "name": "DPO Name",
                "contact_email": "dpo@company.com",
                "contact_address": "DPO Address",
            },
            "privacy_contact": {"email": "privacy@company.com"},
            "data_retention": {
                "general_rule": "24 months",
                "exceptions": {"financial": "7 years"},
            },
        }

        config = OrganisationConfig.model_validate(config_data)
        export_data = config.to_export_metadata()

        # Verify all sections are present
        assert "data_controller" in export_data
        assert "joint_controller" in export_data
        assert "representatives" in export_data
        assert "dpo" in export_data
        assert "privacy_contact" in export_data
        assert "data_retention" in export_data

        # Verify data controller optional fields
        assert export_data["data_controller"]["company_nr"] == "12345"
        assert export_data["data_controller"]["trading_name"] == "Complete Corp"
        assert export_data["data_controller"]["jurisdictions"] == ["EU", "UK"]

        # Verify other sections have correct data
        assert export_data["joint_controller"]["name"] == "Joint Partner"
        assert len(export_data["representatives"]) == 1
        assert export_data["representatives"][0]["company_name"] == "EU Rep Ltd"
        assert export_data["representatives"][0]["company_jurisdiction"] == "EU"
        assert export_data["representatives"][0]["representative_jurisdiction"] == "EU"
        assert export_data["dpo"]["name"] == "DPO Name"
        assert export_data["privacy_contact"]["email"] == "privacy@company.com"
        assert export_data["data_retention"]["general_rule"] == "24 months"
        assert export_data["data_retention"]["exceptions"]["financial"] == "7 years"


class TestOrganisationLoader:
    """Test OrganisationLoader functionality."""

    @patch("wct.organisation.get_project_root")
    def test_load_success(self, mock_get_root):
        """Test successful loading from project root."""
        # Create a temporary config file
        config_data = {
            "data_controller": {
                "name": "Project Company",
                "address": "Project Address",
                "contact_email": "project@company.com",
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_dir = temp_path / "apps" / "wct" / "config"
            config_dir.mkdir(parents=True)

            config_file = config_dir / "organisation.yaml"
            with config_file.open("w") as f:
                yaml.dump(config_data, f)

            # Mock project root to return our temp directory
            mock_get_root.return_value = temp_path

            config = OrganisationLoader.load()
            assert config is not None
            assert config.data_controller.name == "Project Company"

    @patch("wct.organisation.get_project_root")
    def test_load_no_config_returns_none(self, mock_get_root):
        """Test that load returns None when no config exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_get_root.return_value = Path(temp_dir)
            config = OrganisationLoader.load()
            assert config is None

    @patch("wct.organisation.get_project_root")
    def test_load_handles_project_root_error(self, mock_get_root):
        """Test that load handles project root discovery errors."""
        mock_get_root.side_effect = Exception("Cannot find project root")

        config = OrganisationLoader.load()
        assert config is None
