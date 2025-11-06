"""Tests for runbook schema version format validation.

These tests verify that the ExecutionStep Pydantic model correctly validates
semantic version format for input_schema_version and output_schema_version fields.

Tests focus on user-facing behaviour through the public API (RunbookLoader.load()).
"""

import tempfile
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from wct.runbook import RunbookLoader, RunbookValidationError


@pytest.fixture
def runbook_file() -> Generator[Callable[[str], Path], None, None]:
    """Fixture that creates temporary runbook files and handles cleanup.

    Returns:
        Callable that takes YAML content and returns path to temp file

    """
    temp_files: list[Path] = []

    def _create_file(yaml_content: str) -> Path:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            file_path = Path(f.name)
            temp_files.append(file_path)
            return file_path

    yield _create_file

    # Cleanup all created files
    for file_path in temp_files:
        if file_path.exists():
            file_path.unlink()


class TestRunbookVersionValidation:
    """Tests for schema version format validation in runbooks."""

    def _create_test_runbook_yaml(
        self,
        input_schema_version: str | None = None,
        output_schema_version: str | None = None,
        description: str = "Testing version validation",
    ) -> str:
        """Create test runbook YAML with optional version fields.

        Args:
            input_schema_version: Optional input schema version to include
            output_schema_version: Optional output schema version to include
            description: Runbook description

        Returns:
            Complete runbook YAML string

        """
        lines = [
            "name: Test Runbook",
            f"description: {description}",
            "connectors:",
            "  - name: test_connector",
            "    type: filesystem",
            "    properties: {}",
            "analysers:",
            "  - name: test_analyser",
            "    type: personal_data_analyser",
            "    properties: {}",
            "execution:",
            '  - name: "Test step"',
            '    description: "Testing version validation"',
            "    connector: test_connector",
            "    analyser: test_analyser",
            "    input_schema: standard_input",
        ]

        if input_schema_version is not None:
            lines.append(f'    input_schema_version: "{input_schema_version}"')

        lines.append("    output_schema: personal_data_finding")

        if output_schema_version is not None:
            lines.append(f'    output_schema_version: "{output_schema_version}"')

        return "\n".join(lines)

    def test_valid_input_schema_version(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that valid semantic version for input_schema_version is accepted."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="1.0.0",
            description="Testing valid input schema version",
        )
        runbook_path = runbook_file(runbook_yaml)

        runbook = RunbookLoader.load(runbook_path)
        assert runbook.execution[0].input_schema_version == "1.0.0"

    def test_valid_output_schema_version(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that valid semantic version for output_schema_version is accepted."""
        runbook_yaml = self._create_test_runbook_yaml(
            output_schema_version="2.10.5",
            description="Testing valid output schema version",
        )
        runbook_path = runbook_file(runbook_yaml)

        runbook = RunbookLoader.load(runbook_path)
        assert runbook.execution[0].output_schema_version == "2.10.5"

    def test_valid_both_schema_versions(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that both input and output schema versions can be specified together."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="1.0.0",
            output_schema_version="2.10.5",
            description="Testing both schema versions together",
        )
        runbook_path = runbook_file(runbook_yaml)

        runbook = RunbookLoader.load(runbook_path)
        assert runbook.execution[0].input_schema_version == "1.0.0"
        assert runbook.execution[0].output_schema_version == "2.10.5"

    def test_invalid_input_version_two_parts(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that input version with only major.minor is rejected."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="1.0",
            description="Testing invalid input version with two parts",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError, match=r"Version must be in format"):
            RunbookLoader.load(runbook_path)

    def test_invalid_input_version_with_prefix(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that input version with 'v' prefix is rejected."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="v1.0.0",
            description="Testing invalid input version with v prefix",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError, match=r"Version must be in format"):
            RunbookLoader.load(runbook_path)

    def test_invalid_input_version_with_prerelease(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that input version with pre-release suffix is rejected."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="1.0.0-beta",
            description="Testing invalid input version with prerelease suffix",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError, match=r"Version must be in format"):
            RunbookLoader.load(runbook_path)

    def test_invalid_input_version_non_numeric(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that non-semantic version strings like 'latest' are rejected."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="latest",
            description="Testing invalid non-numeric version string",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError, match=r"Version must be in format"):
            RunbookLoader.load(runbook_path)

    def test_invalid_output_version_format(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that output_schema_version field also validates format."""
        runbook_yaml = self._create_test_runbook_yaml(
            output_schema_version="1.0",
            description="Testing invalid output version format",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError, match=r"Version must be in format"):
            RunbookLoader.load(runbook_path)

    def test_missing_versions_backward_compatibility(
        self, runbook_file: Callable[[str], Path]
    ) -> None:
        """Test that runbooks without version fields still load successfully."""
        runbook_yaml = self._create_test_runbook_yaml(
            description="Testing backward compatibility without version fields",
        )
        runbook_path = runbook_file(runbook_yaml)

        runbook = RunbookLoader.load(runbook_path)
        assert runbook.execution[0].input_schema_version is None
        assert runbook.execution[0].output_schema_version is None

    def test_error_message_clarity(self, runbook_file: Callable[[str], Path]) -> None:
        """Test that validation error messages are clear and helpful."""
        runbook_yaml = self._create_test_runbook_yaml(
            input_schema_version="invalid",
            description="Testing error message clarity",
        )
        runbook_path = runbook_file(runbook_yaml)

        with pytest.raises(RunbookValidationError) as exc_info:
            RunbookLoader.load(runbook_path)

        error_message = str(exc_info.value)
        # Verify error message contains helpful information
        assert "input_schema_version" in error_message
        assert "major.minor.patch" in error_message
        assert "1.0.0" in error_message
        assert "invalid" in error_message
