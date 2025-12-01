"""Tests for runbook YAML parser."""

from pathlib import Path

import pytest

from waivern_orchestration import Runbook, RunbookParseError
from waivern_orchestration.parser import parse_runbook, parse_runbook_from_dict


class TestParseRunbook:
    """Tests for parse_runbook() function - file-based parsing with env var substitution."""

    def test_parse_runbook_from_valid_yaml_file(self, tmp_path: Path) -> None:
        """Parse a valid YAML runbook file and verify Runbook model is correct."""
        yaml_content = """
name: "Test Runbook"
description: "A test runbook"

artifacts:
  data_source:
    source:
      type: filesystem
      properties:
        path: /tmp

  findings:
    inputs: data_source
    transform:
      type: analyser
      properties: {}
    output: true
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        runbook = parse_runbook(runbook_file)

        assert isinstance(runbook, Runbook)
        assert runbook.name == "Test Runbook"
        assert runbook.description == "A test runbook"
        assert len(runbook.artifacts) == 2
        assert "data_source" in runbook.artifacts
        assert "findings" in runbook.artifacts

    def test_parse_runbook_substitutes_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables in ${VAR_NAME} format are substituted with actual values."""
        monkeypatch.setenv("TEST_PATH", "/data/files")

        yaml_content = """
name: "Test"
description: "Test"

artifacts:
  data:
    source:
      type: filesystem
      properties:
        path: ${TEST_PATH}
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        runbook = parse_runbook(runbook_file)

        assert runbook.artifacts["data"].source is not None
        assert runbook.artifacts["data"].source.properties["path"] == "/data/files"

    def test_parse_runbook_substitutes_env_vars_in_nested_structures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variables in nested dicts and lists are substituted."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "3306")

        yaml_content = """
name: "Test"
description: "Test"

artifacts:
  data:
    source:
      type: mysql
      properties:
        connection:
          host: ${DB_HOST}
          port: ${DB_PORT}
        tables:
          - ${DB_HOST}
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        runbook = parse_runbook(runbook_file)

        props = runbook.artifacts["data"].source.properties  # type: ignore[union-attr]
        assert props["connection"]["host"] == "localhost"
        assert props["connection"]["port"] == "3306"
        assert props["tables"] == ["localhost"]

    def test_parse_runbook_partial_string_substitution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Strings with multiple ${VAR} patterns are fully substituted (e.g., '${HOST}:${PORT}')."""
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "3306")

        yaml_content = """
name: "Test"
description: "Test"

artifacts:
  data:
    source:
      type: mysql
      properties:
        connection_string: "mysql://${DB_HOST}:${DB_PORT}/db"
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        runbook = parse_runbook(runbook_file)

        props = runbook.artifacts["data"].source.properties  # type: ignore[union-attr]
        assert props["connection_string"] == "mysql://localhost:3306/db"

    def test_parse_runbook_missing_env_var_raises_error(self, tmp_path: Path) -> None:
        """Referencing undefined ${MISSING_VAR} raises RunbookParseError with variable name."""
        yaml_content = """
name: "Test"
description: "Test"

artifacts:
  data:
    source:
      type: filesystem
      properties:
        path: ${UNDEFINED_VAR}
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        with pytest.raises(RunbookParseError) as exc_info:
            parse_runbook(runbook_file)

        assert "UNDEFINED_VAR" in str(exc_info.value)

    def test_parse_runbook_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Malformed YAML raises RunbookParseError with file path in message."""
        yaml_content = """
name: "Test"
description: "Test"
artifacts:
  data:
    - this: is
    invalid: yaml  # Invalid indentation
"""
        runbook_file = tmp_path / "bad.yaml"
        runbook_file.write_text(yaml_content)

        with pytest.raises(RunbookParseError) as exc_info:
            parse_runbook(runbook_file)

        assert "bad.yaml" in str(exc_info.value)

    def test_parse_runbook_file_not_found_raises_error(self) -> None:
        """Non-existent file path raises RunbookParseError."""
        non_existent = Path("/non/existent/runbook.yaml")

        with pytest.raises(RunbookParseError) as exc_info:
            parse_runbook(non_existent)

        assert "not found" in str(exc_info.value).lower()

    def test_parse_runbook_invalid_structure_raises_error(self, tmp_path: Path) -> None:
        """Valid YAML but invalid runbook structure raises RunbookParseError."""
        # Valid YAML but missing required fields
        yaml_content = """
artifacts:
  data:
    source:
      type: filesystem
"""
        runbook_file = tmp_path / "runbook.yaml"
        runbook_file.write_text(yaml_content)

        with pytest.raises(RunbookParseError) as exc_info:
            parse_runbook(runbook_file)

        assert "Invalid runbook structure" in str(exc_info.value)


class TestParseRunbookFromDict:
    """Tests for parse_runbook_from_dict() - direct dict parsing WITHOUT env var substitution."""

    def test_parse_runbook_from_dict_valid(self) -> None:
        """Parse a valid dict directly into Runbook model."""
        data = {
            "name": "Test Runbook",
            "description": "A test runbook for validation",
            "artifacts": {
                "data_source": {
                    "source": {"type": "filesystem", "properties": {"path": "/tmp"}}
                },
                "findings": {
                    "inputs": "data_source",
                    "transform": {"type": "analyser", "properties": {}},
                    "output": True,
                },
            },
        }

        runbook = parse_runbook_from_dict(data)

        assert isinstance(runbook, Runbook)
        assert runbook.name == "Test Runbook"
        assert runbook.description == "A test runbook for validation"
        assert len(runbook.artifacts) == 2
        assert "data_source" in runbook.artifacts
        assert "findings" in runbook.artifacts
        assert runbook.artifacts["findings"].output is True

    def test_parse_runbook_from_dict_does_not_substitute_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dict with ${VAR_NAME} strings remain as literal strings (no substitution)."""
        # Set an env var that would be substituted if substitution happened
        monkeypatch.setenv("TEST_PATH", "/actual/path")

        data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "data": {
                    "source": {
                        "type": "filesystem",
                        "properties": {"path": "${TEST_PATH}"},
                    }
                }
            },
        }

        runbook = parse_runbook_from_dict(data)

        # The ${TEST_PATH} should remain as a literal string, NOT substituted
        assert runbook.artifacts["data"].source is not None
        assert runbook.artifacts["data"].source.properties["path"] == "${TEST_PATH}"

    def test_parse_runbook_from_dict_invalid_structure_raises_error(self) -> None:
        """Invalid dict structure raises RunbookParseError."""
        # Missing required 'name' and 'description' fields
        data = {"artifacts": {}}

        with pytest.raises(RunbookParseError) as exc_info:
            parse_runbook_from_dict(data)

        assert "Invalid runbook structure" in str(exc_info.value)
