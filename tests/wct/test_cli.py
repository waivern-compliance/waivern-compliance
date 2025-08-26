"""Tests for WCT CLI commands.

These tests focus on the public interface of CLI commands, testing various scenarios
and error conditions without testing internal implementation details. The tests use
real temporary files and realistic scenarios to ensure proper integration.

Following black-box testing principles:
- Focus on public API only - never test private methods (starting with _)
- Test behaviour and contracts, not implementation details
- Use realistic test scenarios with temporary resources
- Test edge cases and error conditions through public interfaces
- Avoid mocking internal dependencies
- Use British English spelling throughout ✔️
"""

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from wct.analysis import AnalysisResult
from wct.cli import (
    CLIError,
    OutputFormatter,
    execute_runbook_command,
    list_analysers_command,
    list_connectors_command,
    validate_runbook_command,
)


class TestExecuteRunbookCommand:
    """Test execute_runbook_command functionality."""

    def test_executes_valid_runbook_successfully(self, tmp_path: Path) -> None:
        """Test that a valid runbook executes successfully."""
        # Create a simple valid runbook
        runbook_content = """
name: "Test Runbook"
description: "Test runbook for CLI testing"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "tests/wct/connectors/filesystem/filesystem_mock"
      include_patterns: ["*.txt"]

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns:
        - "email"
        - "phone"

execution:
  - name: "File system analysis for personal data"
    description: "Test execution for filesystem connector with personal data analyser"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "test_runbook.yaml"
        runbook_path.write_text(runbook_content.strip())

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        output_file = Path("test_results.json")

        # Should execute without raising an exception
        execute_runbook_command(
            runbook_path=runbook_path,
            output_dir=output_dir,
            output=output_file,
            verbose=False,
            log_level="INFO",
        )

        # Verify output file was created
        expected_output = output_dir / output_file
        assert expected_output.exists()
        assert expected_output.stat().st_size > 0

    def test_handles_invalid_runbook_gracefully(self, tmp_path: Path) -> None:
        """Test that invalid runbook raises appropriate error."""
        # Create an invalid runbook (missing required fields)
        invalid_runbook = """
name: "Invalid Runbook"
# Missing description, connectors, analysers, execution
"""

        runbook_path = tmp_path / "invalid_runbook.yaml"
        runbook_path.write_text(invalid_runbook.strip())

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        output_file = Path("test_results.json")

        # Should raise typer.Exit due to validation error
        with pytest.raises(typer.Exit):
            execute_runbook_command(
                runbook_path=runbook_path,
                output_dir=output_dir,
                output=output_file,
                verbose=False,
                log_level="INFO",
            )

    def test_handles_nonexistent_runbook_file(self, tmp_path: Path) -> None:
        """Test that nonexistent runbook file raises appropriate error."""
        nonexistent_path = tmp_path / "nonexistent.yaml"
        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        output_file = Path("test_results.json")

        # Should raise typer.Exit due to file not found
        with pytest.raises(typer.Exit):
            execute_runbook_command(
                runbook_path=nonexistent_path,
                output_dir=output_dir,
                output=output_file,
                verbose=False,
                log_level="INFO",
            )

    def test_creates_output_directory_if_not_exists(self, tmp_path: Path) -> None:
        """Test that output directory is created if it doesn't exist."""
        runbook_content = """
name: "Test Runbook"
description: "Test runbook for CLI testing"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "tests/wct/connectors/filesystem/filesystem_mock"
      include_patterns: ["*.txt"]

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns:
        - "email"

execution:
  - name: "File system analysis with output directory creation"
    description: "Test execution that creates output directory if not exists"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "test_runbook.yaml"
        runbook_path.write_text(runbook_content.strip())

        # Use non-existent output directory
        output_dir = tmp_path / "new_outputs"
        output_file = Path("test_results.json")

        # Should handle creating the directory structure
        execute_runbook_command(
            runbook_path=runbook_path,
            output_dir=output_dir,
            output=output_file,
            verbose=False,
            log_level="INFO",
        )

        # Verify output directory and file were created
        assert output_dir.exists()
        expected_output = output_dir / output_file
        assert expected_output.exists()

    def test_handles_absolute_output_path(self, tmp_path: Path) -> None:
        """Test that absolute output paths are handled correctly."""
        runbook_content = """
name: "Test Runbook"
description: "Test runbook for CLI testing"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "tests/wct/connectors/filesystem/filesystem_mock"
      include_patterns: ["*.txt"]

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns:
        - "email"

execution:
  - name: "File system analysis with absolute output path"
    description: "Test execution that handles absolute output paths correctly"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "test_runbook.yaml"
        runbook_path.write_text(runbook_content.strip())

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        absolute_output = tmp_path / "absolute_results.json"

        execute_runbook_command(
            runbook_path=runbook_path,
            output_dir=output_dir,
            output=absolute_output,
            verbose=False,
            log_level="INFO",
        )

        # Verify absolute path was used (not combined with output_dir)
        assert absolute_output.exists()
        assert absolute_output.stat().st_size > 0

    def test_verbose_mode_changes_log_level(self, tmp_path: Path) -> None:
        """Test that verbose mode affects logging configuration."""
        runbook_content = """
name: "Test Runbook"
description: "Test runbook for CLI testing"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "tests/wct/connectors/filesystem/filesystem_mock"
      include_patterns: ["*.txt"]

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns:
        - "email"

execution:
  - name: "File system analysis with verbose mode"
    description: "Test execution that demonstrates verbose logging mode changes"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "test_runbook.yaml"
        runbook_path.write_text(runbook_content.strip())

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()
        output_file = Path("test_results.json")

        # Test with verbose mode
        with patch("wct.cli.setup_logging") as mock_setup_logging:
            execute_runbook_command(
                runbook_path=runbook_path,
                output_dir=output_dir,
                output=output_file,
                verbose=True,
                log_level="INFO",
            )

            # Verify setup_logging was called with DEBUG level due to verbose
            mock_setup_logging.assert_called_once_with(level="DEBUG")


class TestListConnectorsCommand:
    """Test list_connectors_command functionality."""

    def test_lists_connectors_successfully(self) -> None:
        """Test that connectors are listed without error."""
        # Should execute without raising an exception
        list_connectors_command(log_level="INFO")

    def test_respects_log_level_parameter(self) -> None:
        """Test that log level parameter is respected."""
        with patch("wct.cli.setup_logging") as mock_setup_logging:
            list_connectors_command(log_level="DEBUG")
            mock_setup_logging.assert_called_once_with(level="DEBUG")

    def test_handles_executor_creation_failure(self) -> None:
        """Test graceful handling of executor creation failure."""
        with patch("wct.cli.Executor.create_with_built_ins") as mock_create:
            mock_create.side_effect = Exception("Executor creation failed")

            with pytest.raises(typer.Exit):
                list_connectors_command(log_level="INFO")


class TestListAnalysersCommand:
    """Test list_analysers_command functionality."""

    def test_lists_analysers_successfully(self) -> None:
        """Test that analysers are listed without error."""
        # Should execute without raising an exception
        list_analysers_command(log_level="INFO")

    def test_respects_log_level_parameter(self) -> None:
        """Test that log level parameter is respected."""
        with patch("wct.cli.setup_logging") as mock_setup_logging:
            list_analysers_command(log_level="WARNING")
            mock_setup_logging.assert_called_once_with(level="WARNING")

    def test_handles_executor_creation_failure(self) -> None:
        """Test graceful handling of executor creation failure."""
        with patch("wct.cli.Executor.create_with_built_ins") as mock_create:
            mock_create.side_effect = Exception("Executor creation failed")

            with pytest.raises(typer.Exit):
                list_analysers_command(log_level="INFO")


class TestValidateRunbookCommand:
    """Test validate_runbook_command functionality."""

    def test_validates_correct_runbook_successfully(self, tmp_path: Path) -> None:
        """Test that a valid runbook validates successfully."""
        valid_runbook = """
name: "Valid Test Runbook"
description: "A valid runbook for testing validation"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "/tmp"
      include_patterns: ["*.txt"]

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns:
        - "email"
        - "phone"

execution:
  - name: "File system analysis for validation test"
    description: "Test execution for runbook validation functionality"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "valid_runbook.yaml"
        runbook_path.write_text(valid_runbook.strip())

        # Should execute without raising an exception
        validate_runbook_command(runbook_path=runbook_path, log_level="INFO")

    def test_rejects_invalid_runbook(self, tmp_path: Path) -> None:
        """Test that invalid runbook raises validation error."""
        invalid_runbook = """
name: "Invalid Runbook"
# Missing required fields: description, connectors, analysers, execution
"""

        runbook_path = tmp_path / "invalid_runbook.yaml"
        runbook_path.write_text(invalid_runbook.strip())

        # Should raise typer.Exit due to validation failure
        with pytest.raises(typer.Exit):
            validate_runbook_command(runbook_path=runbook_path, log_level="INFO")

    def test_handles_nonexistent_runbook_file(self, tmp_path: Path) -> None:
        """Test that nonexistent runbook file raises appropriate error."""
        nonexistent_path = tmp_path / "nonexistent.yaml"

        # Should raise typer.Exit due to file not found
        with pytest.raises(typer.Exit):
            validate_runbook_command(runbook_path=nonexistent_path, log_level="INFO")

    def test_respects_log_level_parameter(self, tmp_path: Path) -> None:
        """Test that log level parameter is respected."""
        valid_runbook = """
name: "Valid Test Runbook"
description: "A valid runbook for testing validation"
connectors:
  - name: "test_filesystem"
    type: "filesystem"
    properties:
      root_path: "/tmp"

analysers:
  - name: "test_personal_data"
    type: "personal_data_analyser"
    properties:
      patterns: ["email"]

execution:
  - name: "File system analysis for log level test"
    description: "Test execution for verifying log level parameter handling"
    connector: "test_filesystem"
    analyser: "test_personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
"""

        runbook_path = tmp_path / "valid_runbook.yaml"
        runbook_path.write_text(valid_runbook.strip())

        with patch("wct.cli.setup_logging") as mock_setup_logging:
            validate_runbook_command(runbook_path=runbook_path, log_level="CRITICAL")
            mock_setup_logging.assert_called_once_with(level="CRITICAL")


class TestOutputFormatter:
    """Test OutputFormatter UI methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.formatter = OutputFormatter()

    def test_show_startup_banner_displays_information(self, tmp_path: Path) -> None:
        """Test that startup banner shows expected information."""
        runbook_path = tmp_path / "test.yaml"
        output_dir = tmp_path / "outputs"

        # Should execute without error - we can't easily test output content
        # without mocking Rich components, which would violate black-box principles
        self.formatter.show_startup_banner(
            runbook_path=runbook_path,
            output_dir=output_dir,
            log_level="INFO",
            verbose=False,
        )

    def test_show_startup_banner_with_verbose_mode(self, tmp_path: Path) -> None:
        """Test that startup banner handles verbose mode correctly."""
        runbook_path = tmp_path / "test.yaml"
        output_dir = tmp_path / "outputs"

        # Should execute without error
        self.formatter.show_startup_banner(
            runbook_path=runbook_path,
            output_dir=output_dir,
            log_level="DEBUG",
            verbose=True,
        )

    def test_show_analysis_completion_executes_successfully(self) -> None:
        """Test that analysis completion message displays without error."""
        # Should execute without error
        self.formatter.show_analysis_completion()

    def test_show_file_save_success_executes_successfully(self, tmp_path: Path) -> None:
        """Test that file save success message displays without error."""
        test_path = tmp_path / "test_file.json"

        # Should execute without error
        self.formatter.show_file_save_success(test_path)

    def test_show_file_save_error_executes_successfully(self) -> None:
        """Test that file save error message displays without error."""
        # Should execute without error
        self.formatter.show_file_save_error("Test error message")

    def test_show_completion_summary_executes_successfully(
        self, tmp_path: Path
    ) -> None:
        """Test that completion summary displays without error."""
        # Create mock results - we only test that the method executes without error
        mock_results = [
            AnalysisResult(
                analysis_name="Test Analysis",
                analysis_description="Test analysis for completion summary display",
                success=True,
                input_schema="standard_input",
                output_schema="test_output",
                data={},
                metadata={},
            )
        ]

        output_path = tmp_path / "test_output.json"

        # Should execute without error
        self.formatter.show_completion_summary(mock_results, output_path)


class TestCLIError:
    """Test CLIError exception class."""

    def test_cli_error_is_exception_subclass(self) -> None:
        """Test that CLIError is a proper exception subclass."""
        error = CLIError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_cli_error_can_be_raised_and_caught(self) -> None:
        """Test that CLIError can be raised and caught normally."""
        with pytest.raises(CLIError) as exc_info:
            raise CLIError("Test error message")

        assert str(exc_info.value) == "Test error message"

    def test_cli_error_with_command_context(self) -> None:
        """Test that CLIError includes command context in error message."""
        error = CLIError("Something went wrong", command="run")
        expected_message = "CLI command 'run' failed: Something went wrong"
        assert str(error) == expected_message

    def test_cli_error_with_original_error(self) -> None:
        """Test that CLIError stores original error information."""
        original_error = ValueError("Original problem")
        cli_error = CLIError(
            "Wrapper message", command="validate-runbook", original_error=original_error
        )

        assert cli_error.command == "validate-runbook"
        assert cli_error.original_error is original_error
        assert isinstance(cli_error.original_error, ValueError)

    def test_cli_error_without_command_context(self) -> None:
        """Test that CLIError works without command context."""
        error = CLIError("Generic error message")
        assert str(error) == "Generic error message"
        assert error.command is None
        assert error.original_error is None

    def test_cli_error_with_all_parameters(self) -> None:
        """Test CLIError with all parameters provided."""
        original_error = FileNotFoundError("File not found")
        cli_error = CLIError(
            "Failed to process file",
            command="ls-connectors",
            original_error=original_error,
        )

        expected_message = "CLI command 'ls-connectors' failed: Failed to process file"
        assert str(cli_error) == expected_message
        assert cli_error.command == "ls-connectors"
        assert cli_error.original_error is original_error
