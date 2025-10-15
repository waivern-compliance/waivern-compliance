"""Tests for runbook functionality.

These tests focus on:
- File loading, parsing, and error handling (RunbookLoader)
- Custom business logic validation (duplicate names, cross-references)
- Summary generation and integration scenarios

Note: Basic Pydantic field validation (required fields, patterns, etc.) is not tested
as that would be testing third-party functionality rather than our business logic.
"""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from wct.runbook import (
    Runbook,
    RunbookLoader,
    RunbookLoadError,
    RunbookSummary,
    RunbookValidationError,
)


class TestRunbookLoader:
    """Tests for RunbookLoader class."""

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file raises RunbookLoadError."""
        with pytest.raises(RunbookLoadError, match="Cannot read file"):
            RunbookLoader.load(Path("/nonexistent/file.yaml"))

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises RunbookLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content:")
            invalid_path = Path(f.name)

        try:
            with pytest.raises(RunbookLoadError, match="Invalid YAML"):
                RunbookLoader.load(invalid_path)
        finally:
            invalid_path.unlink()

    def test_load_invalid_runbook_structure(self) -> None:
        """Test loading runbook with invalid structure raises RunbookValidationError."""
        invalid_runbook = """
name: Invalid Runbook
description: Missing required fields
connectors: []
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_runbook)
            invalid_path = Path(f.name)

        try:
            with pytest.raises(
                RunbookValidationError, match="Runbook validation failed"
            ):
                RunbookLoader.load(invalid_path)
        finally:
            invalid_path.unlink()

    def test_load_valid_runbook(self) -> None:
        """Test loading a valid runbook succeeds."""
        valid_runbook = """
name: Valid Test Runbook
description: A valid runbook for testing
connectors:
  - name: test_connector
    type: filesystem
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties:
      pattern_matching:
        ruleset: personal_data
execution:
  - name: "Valid runbook test execution"
    description: "Testing valid runbook loading and parsing"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(valid_runbook)
            valid_path = Path(f.name)

        try:
            runbook = RunbookLoader.load(valid_path)
            assert runbook.name == "Valid Test Runbook"
            assert len(runbook.connectors) == 1
            assert len(runbook.analysers) == 1
            assert len(runbook.execution) == 1
        finally:
            valid_path.unlink()

    def test_load_runbook_with_duplicate_names(self) -> None:
        """Test loading runbook with duplicate connector/analyser names fails."""
        duplicate_runbook = """
name: Duplicate Names Test
description: Test duplicate validation
connectors:
  - name: duplicate_name
    type: filesystem
    properties: {}
  - name: duplicate_name
    type: mysql
    properties: {}
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - name: "Duplicate names test execution"
    description: "Testing validation of duplicate connector names"
    connector: duplicate_name
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(duplicate_runbook)
            duplicate_path = Path(f.name)

        try:
            with pytest.raises(
                RunbookValidationError, match="Duplicate connector names"
            ):
                RunbookLoader.load(duplicate_path)
        finally:
            duplicate_path.unlink()

    def test_load_runbook_with_contact_property(self) -> None:
        """Test loading runbook with optional contact property."""
        runbook_with_contact = """
name: Contact Test Runbook
description: Testing runbook with contact property
contact: "Paul Smith <paul.smith@company.com>"
connectors:
  - name: test_connector
    type: filesystem
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - name: "Contact test execution"
    description: "Testing runbook contact loading"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_with_contact)
            contact_path = Path(f.name)

        try:
            runbook = RunbookLoader.load(contact_path)
            assert runbook.contact == "Paul Smith <paul.smith@company.com>"
        finally:
            contact_path.unlink()

    def test_load_runbook_without_contact_defaults_none(self) -> None:
        """Test loading runbook without contact defaults to None."""
        runbook_without_contact = """
name: No Contact Test Runbook
description: Testing runbook without contact property
connectors:
  - name: test_connector
    type: filesystem
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - name: "No contact test execution"
    description: "Testing runbook without contact"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(runbook_without_contact)
            no_contact_path = Path(f.name)

        try:
            runbook = RunbookLoader.load(no_contact_path)
            assert runbook.contact is None
        finally:
            no_contact_path.unlink()


class TestRunbookValidation:
    """Tests for custom runbook validation logic (not basic Pydantic validation)."""

    def test_execution_step_missing_name_field(self) -> None:
        """Test that execution steps without name field are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "description": "Test execution step without name",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("execution", 0, "name") and error["type"] == "missing"
            for error in errors
        )

    def test_execution_step_missing_description_field(self) -> None:
        """Test that execution steps without description field are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Test execution step without description",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("execution", 0, "description")
            and error["type"] == "missing"
            for error in errors
        )

    def test_execution_step_empty_name_field(self) -> None:
        """Test that execution steps with empty name field are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "",
                    "description": "Test execution step with empty name",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any(
            error["loc"] == ("execution", 0, "name")
            and "at least 1 character" in error["msg"]
            for error in errors
        )

    def test_execution_step_empty_description_field_allowed(self) -> None:
        """Test that execution steps with empty description field are allowed."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Test execution step with empty description",
                    "description": "",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)
        assert runbook.execution[0].name == "Test execution step with empty description"
        assert runbook.execution[0].description == ""

    def test_execution_step_valid_name_and_description(self) -> None:
        """Test that execution steps with valid name and description fields work correctly."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Personal Data Analysis",
                    "description": "Analyse filesystem for personal data using pattern matching",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)
        assert runbook.execution[0].name == "Personal Data Analysis"
        assert (
            runbook.execution[0].description
            == "Analyse filesystem for personal data using pattern matching"
        )

    def test_runbook_duplicate_connector_names(self) -> None:
        """Test that duplicate connector names are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "duplicate_name", "type": "filesystem", "properties": {}},
                {"name": "duplicate_name", "type": "mysql", "properties": {}},
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Duplicate connector validation test",
                    "description": "Testing duplicate connector name validation logic",
                    "connector": "duplicate_name",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any("Duplicate connector names" in error["msg"] for error in errors)

    def test_runbook_duplicate_analyser_names(self) -> None:
        """Test that duplicate analyser names are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "duplicate_name",
                    "type": "personal_data_analyser",
                    "properties": {},
                },
                {
                    "name": "duplicate_name",
                    "type": "processing_purpose_analyser",
                    "properties": {},
                },
            ],
            "execution": [
                {
                    "name": "Duplicate analyser validation test",
                    "description": "Testing duplicate analyser name validation logic",
                    "connector": "test_connector",
                    "analyser": "duplicate_name",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any("Duplicate analyser names" in error["msg"] for error in errors)

    def test_runbook_invalid_connector_reference(self) -> None:
        """Test that invalid connector references in execution are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "existing_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Invalid connector reference test",
                    "description": "Testing validation of nonexistent connector references",
                    "connector": "nonexistent_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any("unknown connector" in error["msg"] for error in errors)

    def test_runbook_invalid_analyser_reference(self) -> None:
        """Test that invalid analyser references in execution are rejected."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "existing_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Invalid analyser reference test",
                    "description": "Testing validation of nonexistent analyser references",
                    "connector": "test_connector",
                    "analyser": "nonexistent_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        with pytest.raises(ValidationError) as exc_info:
            Runbook.model_validate(runbook_data)

        errors = exc_info.value.errors()
        assert any("unknown analyser" in error["msg"] for error in errors)

    def test_execution_step_with_contact_property(self) -> None:
        """Test that execution steps can have optional contact property."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Step with contact",
                    "description": "Testing execution step with contact",
                    "contact": "Jane Austin <jane.austin@company.com>",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)
        assert runbook.execution[0].contact == "Jane Austin <jane.austin@company.com>"

    def test_execution_step_without_contact_defaults_none(self) -> None:
        """Test that execution steps without contact default to None."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Step without contact",
                    "description": "Testing execution step without contact",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)
        assert runbook.execution[0].contact is None

    def test_execution_steps_mixed_contact_scenarios(self) -> None:
        """Test runbook with mix of execution steps with and without contact."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "connectors": [
                {"name": "test_connector", "type": "filesystem", "properties": {}}
            ],
            "analysers": [
                {
                    "name": "test_analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                }
            ],
            "execution": [
                {
                    "name": "Step with contact",
                    "description": "Step that has contact information",
                    "contact": "Alice Smith <alice@company.com>",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                },
                {
                    "name": "Step without contact",
                    "description": "Step that has no contact information",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                },
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)
        assert len(runbook.execution) == 2
        assert runbook.execution[0].contact == "Alice Smith <alice@company.com>"
        assert runbook.execution[1].contact is None


class TestRunbookSummary:
    """Tests for RunbookSummary business logic."""

    def test_runbook_summary_creation(self) -> None:
        """Test creating runbook summary from runbook model."""
        runbook_data = {
            "name": "Test Runbook",
            "description": "A comprehensive test runbook",
            "connectors": [
                {"name": "conn1", "type": "filesystem", "properties": {}},
                {"name": "conn2", "type": "mysql", "properties": {}},
            ],
            "analysers": [
                {"name": "anal1", "type": "personal_data_analyser", "properties": {}},
                {
                    "name": "anal2",
                    "type": "processing_purpose_analyser",
                    "properties": {},
                },
                {"name": "anal3", "type": "personal_data_analyser", "properties": {}},
            ],
            "execution": [
                {
                    "name": "First summary test execution",
                    "description": "First step in runbook summary test",
                    "connector": "conn1",
                    "analyser": "anal1",
                    "input_schema": "input",
                    "output_schema": "output1",
                },
                {
                    "name": "Second summary test execution",
                    "description": "Second step in runbook summary test",
                    "connector": "conn2",
                    "analyser": "anal2",
                    "input_schema": "input",
                    "output_schema": "output2",
                },
            ],
        }

        runbook = Runbook.model_validate(runbook_data)
        summary = RunbookSummary.from_runbook(runbook)

        assert summary.name == "Test Runbook"
        assert summary.description == "A comprehensive test runbook"
        assert summary.connector_count == 2
        assert summary.analyser_count == 3
        assert summary.execution_steps == 2
        assert set(summary.connector_types) == {"filesystem", "mysql"}
        assert set(summary.analyser_types) == {
            "personal_data_analyser",
            "processing_purpose_analyser",
        }


class TestRunbookIntegration:
    """Integration tests with realistic runbook structures."""

    def test_validation_with_sample_runbook_structure(self) -> None:
        """Test validation with structure similar to actual sample runbooks."""
        runbook_data = {
            "name": "Sample Integration Test",
            "description": "Testing Pydantic validation with realistic data",
            "contact": "Integration Test Manager <integration@company.com>",
            "connectors": [
                {
                    "name": "filesystem_connector",
                    "type": "filesystem",
                    "properties": {
                        "path": "./data",
                        "exclude_patterns": ["*.pyc", "__pycache__"],
                        "max_files": 100,
                    },
                },
                {
                    "name": "database_connector",
                    "type": "mysql",
                    "properties": {
                        "max_rows_per_table": 50,
                    },
                },
            ],
            "analysers": [
                {
                    "name": "personal_data_detector",
                    "type": "personal_data_analyser",
                    "properties": {
                        "pattern_matching": {
                            "ruleset": "personal_data",
                            "evidence_context_size": "medium",
                            "maximum_evidence_count": 3,
                        },
                        "llm_validation": {
                            "enable_llm_validation": False,
                            "llm_batch_size": 50,
                            "llm_validation_mode": "standard",
                        },
                    },
                    "metadata": {
                        "description": "Detects personal data patterns",
                    },
                },
                {
                    "name": "purpose_detector",
                    "type": "processing_purpose_analyser",
                    "properties": {
                        "ruleset": "processing_purposes",
                        "enable_llm_validation": True,
                        "confidence_threshold": 0.7,
                    },
                    "metadata": {},
                },
            ],
            "execution": [
                {
                    "name": "Filesystem personal data analysis",
                    "description": "Comprehensive analysis of filesystem for personal data patterns",
                    "contact": "Data Analysis Team <data-analysis@company.com>",
                    "connector": "filesystem_connector",
                    "analyser": "personal_data_detector",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                },
                {
                    "name": "Database processing purpose analysis",
                    "description": "Identification of data processing purposes in database",
                    "connector": "database_connector",
                    "analyser": "purpose_detector",
                    "input_schema": "standard_input",
                    "output_schema": "processing_purpose_finding",
                },
            ],
        }

        # Should validate successfully
        runbook = Runbook.model_validate(runbook_data)

        # Verify the structure is preserved
        assert runbook.name == "Sample Integration Test"
        assert len(runbook.connectors) == 2
        assert len(runbook.analysers) == 2
        assert len(runbook.execution) == 2

        # Verify contact properties are preserved
        assert runbook.contact == "Integration Test Manager <integration@company.com>"
        assert (
            runbook.execution[0].contact
            == "Data Analysis Team <data-analysis@company.com>"
        )
        assert runbook.execution[1].contact is None  # Second step has no contact

        # Verify nested properties are preserved
        fs_connector = runbook.connectors[0]
        assert fs_connector.properties["exclude_patterns"] == ["*.pyc", "__pycache__"]

        personal_data_analyser = runbook.analysers[0]
        assert (
            personal_data_analyser.properties["pattern_matching"]["ruleset"]
            == "personal_data"
        )
