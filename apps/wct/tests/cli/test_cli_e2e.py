"""CLI End-to-End integration tests for WCT command-line interface."""

import json
import subprocess
import time
from pathlib import Path

import pytest


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

    def test_wct_cli_uses_json_exporter_for_generic_analysers(
        self, tmp_path: Path
    ) -> None:
        """CLI uses JSON exporter when no framework-specific analysers are detected."""
        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/file_content_analysis.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"

        output_dir = tmp_path / "exporter_test"
        output_dir.mkdir()

        # Act - Execute WCT CLI command with generic analysers
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

        # Assert - Output should indicate JSON exporter was used
        assert (
            "Using exporter: json" in result.stdout or "json" in result.stdout.lower()
        )

        # Assert - Output file should use CoreExport structure
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) > 0, "Should produce JSON output file"

        with json_files[0].open() as f:
            export_data = json.load(f)

        # Verify CoreExport structure
        assert "format_version" in export_data
        assert export_data["format_version"] == "2.0.0"
        assert "run" in export_data
        assert "runbook" in export_data
        assert "summary" in export_data
        assert "outputs" in export_data

    @pytest.mark.skip(
        reason="TODO: Requires framework-specific analyser (e.g., GDPR analyser) "
        "that returns non-empty compliance frameworks from get_compliance_frameworks()"
    )
    def test_wct_cli_uses_framework_specific_exporter_for_single_framework(
        self, tmp_path: Path
    ) -> None:
        """CLI uses framework-specific exporter when single framework detected.

        This test will be implemented when we have framework-specific analysers
        (e.g., GDPR analyser) that declare compliance frameworks.

        Expected behaviour:
        - Runbook uses GDPR analyser (returns ["GDPR"] from get_compliance_frameworks())
        - CLI detects single framework
        - CLI uses "gdpr" exporter instead of "json" exporter
        - Output follows GdprExport format
        """
        pytest.skip("Framework-specific analysers not yet implemented")

    @pytest.mark.skip(
        reason="TODO: Requires multiple framework-specific analysers "
        "(e.g., GDPR + CCPA analysers) that return different frameworks"
    )
    def test_wct_cli_falls_back_to_json_for_multiple_frameworks(
        self, tmp_path: Path
    ) -> None:
        """CLI falls back to JSON exporter when multiple frameworks detected.

        This test will be implemented when we have multiple framework-specific
        analysers that declare different compliance frameworks.

        Expected behaviour:
        - Runbook uses GDPR analyser (returns ["GDPR"]) + CCPA analyser (returns ["CCPA"])
        - CLI detects multiple frameworks: {"GDPR", "CCPA"}
        - CLI logs: "Multiple compliance frameworks detected: {...}. Using JSON exporter."
        - CLI falls back to "json" exporter
        - Output follows CoreExport format
        """
        pytest.skip("Multiple framework-specific analysers not yet implemented")

    def test_wct_cli_rejects_invalid_exporter_with_helpful_message(
        self, tmp_path: Path
    ) -> None:
        """CLI rejects invalid exporter with helpful error message."""
        # Arrange
        runbook_path = Path("apps/wct/runbooks/samples/file_content_analysis.yaml")
        assert runbook_path.exists(), f"Runbook not found: {runbook_path}"

        output_dir = tmp_path / "invalid_exporter_test"
        output_dir.mkdir()

        # Act - Execute with invalid exporter
        result = subprocess.run(  # noqa: S603
            [  # noqa: S607
                "uv",
                "run",
                "wct",
                "run",
                str(runbook_path),
                "--output-dir",
                str(output_dir),
                "--exporter",
                "invalid_exporter",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        # Assert - Command should fail
        assert result.returncode == 1, (
            f"Expected CLI to fail with invalid exporter, but got return code {result.returncode}"
        )

        # Assert - Error message should mention unknown exporter and show available
        assert "Unknown exporter 'invalid_exporter'" in result.stderr or (
            "Unknown exporter 'invalid_exporter'" in result.stdout
        )
        assert "Available:" in result.stderr or "Available:" in result.stdout
        assert "json" in result.stderr or "json" in result.stdout

    def test_wct_cli_lists_available_exporters(self) -> None:
        """CLI lists available exporters with their supported frameworks."""
        # Act - Execute ls-exporters command
        result = subprocess.run(
            ["uv", "run", "wct", "ls-exporters"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        # Assert - Command should succeed
        assert result.returncode == 0, (
            f"wct ls-exporters failed with return code {result.returncode}.\\n"
            f"STDOUT: {result.stdout}\\n"
            f"STDERR: {result.stderr}"
        )

        # Assert - Output should contain JSON exporter
        assert "json" in result.stdout.lower(), (
            "Expected to find 'json' exporter in output"
        )

        # Assert - Output should indicate framework support
        assert "any" in result.stdout.lower() or "generic" in result.stdout.lower(), (
            "Expected JSON exporter to show 'Any (generic)' framework support"
        )

    @pytest.mark.skip(
        reason="TODO: Requires multiple exporters (e.g., GDPR exporter) "
        "to test override meaningfully - currently auto-detection always returns 'json'"
    )
    def test_wct_cli_respects_manual_exporter_override(self, tmp_path: Path) -> None:
        """CLI respects --exporter flag to override auto-detection.

        This test will be implemented when we have multiple exporters (e.g., GDPR exporter).

        Expected behaviour:
        - Runbook with GDPR analyser would auto-detect "gdpr" exporter
        - But `--exporter json` overrides to use "json" exporter
        - Output follows CoreExport format (not GdprExport format)
        """
        # TODO: Implement this test when GDPR exporter is available
        # Need runbook with GDPR analyser that would auto-detect "gdpr" exporter
        # Then test that --exporter json overrides to use JSON exporter instead
        pytest.skip("Multiple exporters not yet implemented")
