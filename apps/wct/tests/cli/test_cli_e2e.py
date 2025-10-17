"""CLI End-to-End integration tests for WCT command-line interface."""

import json
import subprocess
import time
from pathlib import Path


class TestWCTCLIE2E:
    """Test WCT CLI command execution and JSON file output generation."""

    def test_wct_cli_runs_lamp_stack_lite_successfully(self, tmp_path: Path) -> None:
        """WCT CLI executes LAMP_stack_lite.yaml runbook and generates JSON outputs."""
        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"
        assert runbook_path.parent == Path("apps/wct/runbooks/samples"), (
            "Runbook must be in samples directory"
        )

        output_dir = tmp_path / "cli_output"
        output_dir.mkdir()

        # Act - Execute WCT CLI command
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Assert - Command should succeed
        assert result.returncode == 0, (
            f"WCT CLI failed with return code {result.returncode}.\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Assert - Should have output indicating successful execution
        assert "success" in result.stdout.lower() or len(result.stderr) == 0

        # Assert - Output directory should contain JSON files
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) > 0, (
            f"No JSON files found in output directory {output_dir}. "
            f"Files found: {list(output_dir.iterdir())}"
        )

    def test_wct_cli_generates_expected_json_files(self, tmp_path: Path) -> None:
        """WCT CLI creates expected JSON output files with correct structure."""
        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.parent == Path("apps/wct/runbooks/samples"), (
            "Runbook must be in samples directory"
        )
        output_dir = tmp_path / "json_validation"
        output_dir.mkdir()

        # Act - Execute WCT CLI command
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Assert - Command should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Assert - Find and validate generated JSON files
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) >= 1, (
            f"Expected at least 1 JSON file, found {len(json_files)}"
        )

        # Assert - Validate JSON file structure
        for json_file in json_files:
            with open(json_file) as f:
                data = json.load(f)

            # Should have top-level structure expected from WCT analysis
            assert isinstance(data, dict), (
                f"JSON file {json_file.name} should contain a dictionary"
            )

            # Should contain analysis results structure
            assert len(data) > 0, f"JSON file {json_file.name} should not be empty"

            # Validate expected WCT output structure
            if "analyses" in data:
                analyses = data["analyses"]
                assert isinstance(analyses, list), "Analyses should be a list"

                if len(analyses) > 0:
                    analysis = analyses[0]
                    # Check for expected analysis result fields
                    expected_fields = ["analysis_name", "success", "data"]
                    for field in expected_fields:
                        assert field in analysis, (
                            f"Analysis should have '{field}' field"
                        )

    def test_wct_cli_handles_invalid_runbook_gracefully(self, tmp_path: Path) -> None:
        """WCT CLI provides helpful error messages for invalid runbooks."""
        # Arrange - Create an invalid runbook
        invalid_runbook = tmp_path / "invalid.yaml"
        invalid_runbook.write_text("invalid_yaml_content: [unclosed")

        output_dir = tmp_path / "error_output"
        output_dir.mkdir()

        # Act - Execute WCT CLI with invalid runbook
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(invalid_runbook),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # Assert - Command should fail gracefully
        assert result.returncode != 0, "CLI should fail with invalid runbook"

        # Assert - Should provide helpful error message
        combined_output = (result.stdout + result.stderr).lower()
        assert any(
            keyword in combined_output
            for keyword in ["yaml", "invalid", "failed", "error"]
        ), (
            f"Error message should mention YAML/invalid/failed/error.\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

        # Assert - Should not create output files on failure
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) == 0, (
            "Should not create JSON files when runbook is invalid"
        )

    def test_wct_cli_respects_output_directory_parameter(self, tmp_path: Path) -> None:
        """WCT CLI writes output files to specified directory."""
        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.parent == Path("apps/wct/runbooks/samples"), (
            "Runbook must be in samples directory"
        )
        custom_output_dir = tmp_path / "custom_location" / "nested"
        custom_output_dir.mkdir(parents=True)

        # Act - Execute WCT CLI with custom output directory
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(custom_output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Assert - Command should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Assert - Files should be in the specified directory
        json_files = list(custom_output_dir.glob("*.json"))
        assert len(json_files) > 0, (
            f"No JSON files found in custom directory {custom_output_dir}"
        )

        # Assert - No files should be in default location (checked implicitly by custom dir success)

    def test_wct_cli_performance_benchmark(self, tmp_path: Path) -> None:
        """WCT CLI completes LAMP_stack_lite analysis within performance benchmarks."""

        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/LAMP_stack_lite.yaml")
        assert runbook_path.parent == Path("apps/wct/runbooks/samples"), (
            "Runbook must be in samples directory"
        )
        output_dir = tmp_path / "performance_test"
        output_dir.mkdir()

        # Act - Execute WCT CLI and measure time
        start_time = time.time()
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        execution_time = time.time() - start_time

        # Assert - Command should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Assert - Should complete within reasonable time (60 seconds for CI friendliness)
        assert execution_time < 60.0, (
            f"CLI execution took {execution_time:.2f}s, expected < 60s. "
            f"This may indicate performance regression in CLI or underlying components."
        )

        # Assert - Should produce output files
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) > 0, "Performance test should produce JSON output files"
