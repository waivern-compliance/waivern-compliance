"""Integration tests for SourceCodeAnalyser pipeline execution.

These tests verify the complete pipeline: FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser
using real components through the executor's public API.
"""

import tempfile
from pathlib import Path

import pytest
from wct.executor import Executor


@pytest.fixture
def temp_php_file():
    """Create a temporary PHP file with sample code for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        php_file = Path(tmpdir) / "sample.php"
        php_file.write_text(
            """<?php
function collectUserData($userId) {
    $userData = [
        'name' => getUserName($userId),
        'email' => getUserEmail($userId),
        'age' => getUserAge($userId)
    ];
    return $userData;
}

class UserManager {
    public function registerUser($name, $email) {
        // Registration logic
        $this->saveToDatabase($name, $email);
    }
}
?>"""
        )
        yield Path(tmpdir), php_file


@pytest.fixture
def executor():
    """Create executor instance for testing with discovered components."""
    return Executor.create_with_built_ins()


@pytest.mark.integration
class TestSourceCodeAnalyserPipeline:
    """Integration tests for SourceCodeAnalyser in pipeline execution."""

    def test_filesystem_to_source_code_to_processing_purpose_3step_pipeline(
        self, executor, temp_php_file, tmp_path
    ):
        """Test 2-step pipeline: (Filesystem+SourceCode) → ProcessingPurpose."""
        temp_dir, _php_file = temp_php_file

        # Create runbook YAML for 2-step pipeline
        runbook_content = f"""
name: Source Code to Processing Purpose Pipeline
description: Test 2-step pipeline with saved artifacts
contact: test@example.com

connectors:
  - name: filesystem_reader
    type: filesystem_connector
    properties:
      path: {temp_dir}

analysers:
  - name: code_parser
    type: source_code_analyser
    properties:
      language: php
      max_file_size: 10485760

  - name: purpose_analyser
    type: processing_purpose_analyser
    properties:
      pattern_matching:
        ruleset: processing_purposes
        evidence_context_size: medium
      llm_validation:
        enable_llm_validation: false

execution:
  - id: parse_code
    name: Parse source code
    description: Read files and parse to code structure
    connector: filesystem_reader
    analyser: code_parser
    input_schema: standard_input
    output_schema: source_code
    save_output: true

  - id: analyze_purposes
    name: Analyze processing purposes
    description: Detect processing purposes from parsed code
    input_from: parse_code
    analyser: purpose_analyser
    input_schema: source_code
    output_schema: processing_purpose_finding
"""

        # Write runbook to temp file
        runbook_file = tmp_path / "test_runbook.yaml"
        runbook_file.write_text(runbook_content)

        # Execute pipeline
        results = executor.execute_runbook(str(runbook_file))

        # Verify both steps executed successfully
        assert len(results) == 2

        # Verify step 1 (source code parser)
        assert results[0].success is True
        assert results[0].analysis_name == "Parse source code"
        assert results[0].output_schema == "source_code"

        # Verify step 2 (processing purpose analyser)
        assert results[1].success is True
        assert results[1].analysis_name == "Analyze processing purposes"
        assert results[1].input_schema == "source_code"
        assert results[1].output_schema == "processing_purpose_finding"

        # Verify processing purpose findings
        output_data = results[1].data
        assert "findings" in output_data

        findings = output_data["findings"]
        assert isinstance(findings, list)
        # Should have detected processing purposes from the PHP code
        assert len(findings) > 0

    def test_schema_incompatibility_caught(self, executor, temp_php_file, tmp_path):
        """Test that executor catches schema incompatibility in pipeline.

        PersonalDataAnalyser outputs personal_data_finding schema,
        but SourceCodeAnalyser only accepts standard_input schema.
        """
        temp_dir, _php_file = temp_php_file

        # Create runbook with incompatible schema chain
        runbook_content = f"""
name: Invalid Schema Chain Test
description: Test schema incompatibility detection
contact: test@example.com

connectors:
  - name: filesystem_reader
    type: filesystem_connector
    properties:
      path: {temp_dir}

analysers:
  - name: personal_data_detector
    type: personal_data_analyser
    properties:
      pattern_matching:
        ruleset: personal_data
        evidence_context_size: medium
      llm_validation:
        enable_llm_validation: false

  - name: code_parser
    type: source_code_analyser
    properties:
      language: php
      max_file_size: 10485760

execution:
  - id: detect_personal_data
    name: Detect personal data
    description: Analyze files for personal data
    connector: filesystem_reader
    analyser: personal_data_detector
    input_schema: standard_input
    output_schema: personal_data_finding
    save_output: true

  - id: parse_code
    name: Parse source code
    description: This should fail - wrong input schema
    input_from: detect_personal_data
    analyser: code_parser
    input_schema: personal_data_finding
    output_schema: source_code
"""

        # Write runbook to temp file
        runbook_file = tmp_path / "invalid_schema_runbook.yaml"
        runbook_file.write_text(runbook_content)

        # Execute pipeline - should return error result
        results = executor.execute_runbook(str(runbook_file))

        # Verify step 1 succeeded
        assert len(results) == 2
        assert results[0].success is True

        # Verify step 2 failed due to schema mismatch
        assert results[1].success is False
        error_message = results[1].error_message or ""
        assert (
            "mismatch" in error_message.lower()
            or "does not support" in error_message.lower()
        )
        assert "personal_data_finding" in error_message
        assert "standard_input" in error_message

    def test_missing_save_output_flag(self, executor, temp_php_file, tmp_path):
        """Test that missing save_output flag is detected.

        When step 2 tries to use input_from step 1, but step 1 doesn't have
        save_output: true, the executor should raise ExecutorError.
        """
        temp_dir, _php_file = temp_php_file

        # Create runbook where step 1 forgets save_output: true
        runbook_content = f"""
name: Missing save_output Test
description: Test missing save_output flag detection
contact: test@example.com

connectors:
  - name: filesystem_reader
    type: filesystem_connector
    properties:
      path: {temp_dir}

analysers:
  - name: code_parser
    type: source_code_analyser
    properties:
      language: php
      max_file_size: 10485760

  - name: purpose_analyser
    type: processing_purpose_analyser
    properties:
      pattern_matching:
        ruleset: processing_purposes
        evidence_context_size: medium
      llm_validation:
        enable_llm_validation: false

execution:
  - id: parse_code
    name: Parse source code
    description: Read files and parse to code structure
    connector: filesystem_reader
    analyser: code_parser
    input_schema: standard_input
    output_schema: source_code
    # MISSING: save_output: true

  - id: analyze_purposes
    name: Analyze processing purposes
    description: This should fail - artifact not saved
    input_from: parse_code
    analyser: purpose_analyser
    input_schema: source_code
    output_schema: processing_purpose_finding
"""

        # Write runbook to temp file
        runbook_file = tmp_path / "missing_save_output_runbook.yaml"
        runbook_file.write_text(runbook_content)

        # Execute runbook - second step should fail gracefully
        results = executor.execute_runbook(str(runbook_file))

        # First step should succeed
        assert len(results) == 2
        assert results[0].success is True
        assert results[0].analysis_name == "Parse source code"

        # Second step should fail with helpful error message
        assert results[1].success is False
        error_message = results[1].error_message or ""
        assert "artifact not found" in error_message.lower()
        assert "save_output: true" in error_message
        assert "parse_code" in error_message
