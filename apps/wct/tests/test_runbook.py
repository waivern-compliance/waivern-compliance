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
    ExecutionStep,
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
    type: filesystem_connector
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties:
      pattern_matching:
        ruleset: personal_data
execution:
  - id: "step1"
    name: "Valid runbook test execution"
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
    type: filesystem_connector
    properties: {}
  - name: duplicate_name
    type: mysql
    properties: {}
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - id: "step1"
    name: "Duplicate names test execution"
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
    type: filesystem_connector
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - id: "step1"
    name: "Contact test execution"
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
    type: filesystem_connector
    properties:
      path: ./test
analysers:
  - name: test_analyser
    type: personal_data_analyser
    properties: {}
execution:
  - id: "step1"
    name: "No contact test execution"
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "duplicate_name",
                    "type": "filesystem_connector",
                    "properties": {},
                },
                {"name": "duplicate_name", "type": "mysql_connector", "properties": {}},
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "existing_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
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
                {
                    "name": "test_connector",
                    "type": "filesystem_connector",
                    "properties": {},
                }
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
                    "id": "step1",
                    "name": "Step with contact",
                    "description": "Step that has contact information",
                    "contact": "Alice Smith <alice@company.com>",
                    "connector": "test_connector",
                    "analyser": "test_analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                },
                {
                    "id": "step2",
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
                {"name": "conn1", "type": "filesystem_connector", "properties": {}},
                {"name": "conn2", "type": "mysql_connector", "properties": {}},
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
                    "id": "step1",
                    "name": "First summary test execution",
                    "description": "First step in runbook summary test",
                    "connector": "conn1",
                    "analyser": "anal1",
                    "input_schema": "input",
                    "output_schema": "output1",
                },
                {
                    "id": "step2",
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
        assert set(summary.connector_types) == {
            "filesystem_connector",
            "mysql_connector",
        }
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
                    "type": "filesystem_connector",
                    "properties": {
                        "path": "./data",
                        "exclude_patterns": ["*.pyc", "__pycache__"],
                        "max_files": 100,
                    },
                },
                {
                    "name": "database_connector",
                    "type": "mysql_connector",
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
                    "id": "step1",
                    "name": "Filesystem personal data analysis",
                    "description": "Comprehensive analysis of filesystem for personal data patterns",
                    "contact": "Data Analysis Team <data-analysis@company.com>",
                    "connector": "filesystem_connector",
                    "analyser": "personal_data_detector",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                },
                {
                    "id": "step2",
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


class TestPipelineExecutionStep:
    """Tests for pipeline-only ExecutionStep model."""

    def test_connector_based_step_with_analyser(self) -> None:
        """Test connector-based step with analyser."""
        step = ExecutionStep(
            id="read_and_analyse",
            name="Read and analyse files",
            description="Read files and analyse for personal data",
            connector="filesystem",
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            save_output=True,
        )

        assert step.id == "read_and_analyse"
        assert step.connector == "filesystem"
        assert step.analyser == "personal_data"
        assert step.input_from is None
        assert step.save_output is True

    def test_connector_based_step_without_analyser(self) -> None:
        """Test connector-only step (no analyser)."""
        step = ExecutionStep(
            id="read_files",
            name="Read source files",
            description="Read files from filesystem",
            connector="filesystem",
            input_schema="standard_input",
            output_schema="standard_input",
            save_output=True,
        )

        assert step.connector == "filesystem"
        assert step.analyser is None
        assert step.input_from is None

    def test_input_based_step_with_analyser(self) -> None:
        """Test input-based transformer step."""
        step = ExecutionStep(
            id="parse_code",
            name="Parse source code",
            description="Transform files to code structure",
            input_from="read_files",
            analyser="source_code_parser",
            input_schema="standard_input",
            output_schema="source_code",
            save_output=True,
        )

        assert step.id == "parse_code"
        assert step.input_from == "read_files"
        assert step.analyser == "source_code_parser"
        assert step.connector is None
        assert step.save_output is True

    def test_id_field_required(self) -> None:
        """Test that id field is required."""
        with pytest.raises(ValidationError, match="id"):
            ExecutionStep(  # type: ignore[call-arg]  # Intentionally missing id
                name="No ID step",
                description="Missing ID",
                connector="filesystem",
                input_schema="standard_input",
                output_schema="standard_input",
            )

    def test_connector_xor_input_from_both_fails(self) -> None:
        """Test that having both connector and input_from fails validation."""
        with pytest.raises(ValidationError, match="cannot have both"):
            ExecutionStep(
                id="invalid",
                name="Invalid step",
                description="Has both connector and input_from",
                connector="filesystem",
                input_from="previous_step",
                analyser="analyser",
                input_schema="standard_input",
                output_schema="output",
            )

    def test_connector_xor_input_from_neither_fails(self) -> None:
        """Test that having neither connector nor input_from fails validation."""
        with pytest.raises(ValidationError, match="must have either"):
            ExecutionStep(
                id="invalid",
                name="Invalid step",
                description="Has neither connector nor input_from",
                analyser="analyser",
                input_schema="standard_input",
                output_schema="output",
            )

    def test_save_output_defaults_false(self) -> None:
        """Test that save_output defaults to False."""
        step = ExecutionStep(
            id="step1",
            name="Test step",
            description="Test",
            connector="conn",
            input_schema="input",
            output_schema="output",
        )

        assert step.save_output is False


class TestPipelineCrossReferenceValidation:
    """Tests for pipeline cross-reference validation (Step 2)."""

    def test_runbook_validates_input_from_references_valid_step_id(self) -> None:
        """Test that input_from must reference a valid step ID."""
        runbook_data = {
            "name": "Test Pipeline",
            "description": "Test cross-reference validation",
            "connectors": [
                {"name": "reader", "type": "filesystem_connector", "properties": {}}
            ],
            "analysers": [
                {"name": "analyser", "type": "personal_data_analyser", "properties": {}}
            ],
            "execution": [
                {
                    "id": "step1",
                    "name": "Read files",
                    "description": "Read from filesystem",
                    "connector": "reader",
                    "analyser": "analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                    "save_output": True,
                },
                {
                    "id": "step2",
                    "name": "Process output",
                    "description": "Process previous step output",
                    "input_from": "non_existent_step",  # Invalid reference!
                    "analyser": "analyser",
                    "input_schema": "personal_data_finding",
                    "output_schema": "personal_data_finding",
                },
            ],
        }

        with pytest.raises(ValidationError, match="references unknown step ID"):
            Runbook.model_validate(runbook_data)

    def test_runbook_accepts_valid_pipeline_with_chained_steps(self) -> None:
        """Test that valid pipeline with proper references is accepted."""
        runbook_data = {
            "name": "Valid Pipeline",
            "description": "Test valid pipeline",
            "connectors": [
                {"name": "reader", "type": "filesystem_connector", "properties": {}}
            ],
            "analysers": [
                {"name": "parser", "type": "source_code_analyser", "properties": {}},
                {
                    "name": "analyser",
                    "type": "personal_data_analyser",
                    "properties": {},
                },
            ],
            "execution": [
                {
                    "id": "read",
                    "name": "Read files",
                    "description": "Read source files",
                    "connector": "reader",
                    "analyser": "parser",
                    "input_schema": "standard_input",
                    "output_schema": "source_code",
                    "save_output": True,
                },
                {
                    "id": "analyse",
                    "name": "Analyse code",
                    "description": "Analyse parsed code",
                    "input_from": "read",  # Valid reference
                    "analyser": "analyser",
                    "input_schema": "source_code",
                    "output_schema": "personal_data_finding",
                },
            ],
        }

        runbook = Runbook.model_validate(runbook_data)

        assert len(runbook.execution) == 2
        assert runbook.execution[0].id == "read"
        assert runbook.execution[0].connector == "reader"
        assert runbook.execution[1].id == "analyse"
        assert runbook.execution[1].input_from == "read"
