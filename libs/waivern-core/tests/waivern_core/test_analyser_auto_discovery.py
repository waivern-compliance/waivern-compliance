"""Tests for Analyser auto-discovery functionality."""

import tempfile
from pathlib import Path

from waivern_core.schemas.base import Schema


class TestAnalyserAutoDiscovery:
    """Tests for auto-discovery of supported input/output schemas."""

    def _create_test_analyser_with_schemas(
        self,
        input_schema_files: dict[str, str] | None = None,
        output_schema_files: dict[str, str] | None = None,
    ) -> tuple[list[Schema], list[Schema]]:
        """Helper to create test analyser and return discovered schemas.

        Args:
            input_schema_files: Dict mapping filename -> file content for schema_readers/
            output_schema_files: Dict mapping filename -> file content for schema_producers/

        Returns:
            Tuple of (input_schemas, output_schemas)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            analyser_dir = Path(tmpdir) / "test_analyser"
            analyser_dir.mkdir()

            # Create schema_readers directory if there are input schema files
            if input_schema_files:
                schema_readers_dir = analyser_dir / "schema_readers"
                schema_readers_dir.mkdir()
                for filename, content in input_schema_files.items():
                    (schema_readers_dir / filename).write_text(content)

            # Create schema_producers directory if there are output schema files
            if output_schema_files:
                schema_producers_dir = analyser_dir / "schema_producers"
                schema_producers_dir.mkdir()
                for filename, content in output_schema_files.items():
                    (schema_producers_dir / filename).write_text(content)

            # Create analyser class file
            analyser_file = analyser_dir / "analyser.py"
            analyser_file.write_text(
                "from waivern_core.base_analyser import Analyser\n"
                "from waivern_core.message import Message\n"
                "from waivern_core.schemas.base import Schema\n\n"
                "class TestAnalyser(Analyser):\n"
                "    @classmethod\n"
                "    def get_name(cls) -> str:\n"
                "        return 'test'\n"
                "    def process_data(self, message: Message) -> Message:\n"
                "        pass\n"
            )

            # Dynamically import and get schemas
            import sys

            sys.path.insert(0, str(analyser_dir))
            try:
                # Clear any cached analyser module
                if "analyser" in sys.modules:
                    del sys.modules["analyser"]

                from analyser import TestAnalyser  # type: ignore[import-not-found]

                input_schemas = TestAnalyser.get_supported_input_schemas()
                output_schemas = TestAnalyser.get_supported_output_schemas()
                return (input_schemas, output_schemas)
            finally:
                # Clean up
                if "analyser" in sys.modules:
                    del sys.modules["analyser"]
                sys.path.remove(str(analyser_dir))

    def test_input_schema_auto_discovery_finds_single_schema(self) -> None:
        """Test input schema discovery from schema_readers/ directory."""
        input_schemas, output_schemas = self._create_test_analyser_with_schemas(
            input_schema_files={"standard_input_1_0_0.py": "# Input schema"}
        )

        assert len(input_schemas) == 1
        assert input_schemas[0].name == "standard_input"
        assert input_schemas[0].version == "1.0.0"
        assert output_schemas == []  # No output schemas defined

    def test_output_schema_auto_discovery_finds_single_schema(self) -> None:
        """Test output schema discovery from schema_producers/ directory."""
        input_schemas, output_schemas = self._create_test_analyser_with_schemas(
            output_schema_files={"personal_data_finding_1_0_0.py": "# Output schema"}
        )

        assert input_schemas == []  # No input schemas defined
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_finding"
        assert output_schemas[0].version == "1.0.0"

    def test_both_directories_work_independently(self) -> None:
        """Test both directories can exist and work together."""
        input_schemas, output_schemas = self._create_test_analyser_with_schemas(
            input_schema_files={"standard_input_1_0_0.py": "# Input schema"},
            output_schema_files={"personal_data_finding_1_0_0.py": "# Output schema"},
        )

        assert len(input_schemas) == 1
        assert input_schemas[0].name == "standard_input"
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_finding"

    def test_input_discovery_finds_multiple_versions(self) -> None:
        """Test multiple input schema versions discovered."""
        input_schemas, _ = self._create_test_analyser_with_schemas(
            input_schema_files={
                "standard_input_1_0_0.py": "# v1.0.0",
                "standard_input_1_1_0.py": "# v1.1.0",
            }
        )

        assert len(input_schemas) == 2
        schema_tuples = {(s.name, s.version) for s in input_schemas}
        assert ("standard_input", "1.0.0") in schema_tuples
        assert ("standard_input", "1.1.0") in schema_tuples

    def test_output_discovery_finds_multiple_versions(self) -> None:
        """Test multiple output schema versions discovered."""
        _, output_schemas = self._create_test_analyser_with_schemas(
            output_schema_files={
                "finding_1_0_0.py": "# v1.0.0",
                "finding_2_0_0.py": "# v2.0.0",
            }
        )

        assert len(output_schemas) == 2
        schema_tuples = {(s.name, s.version) for s in output_schemas}
        assert ("finding", "1.0.0") in schema_tuples
        assert ("finding", "2.0.0") in schema_tuples

    def test_returns_empty_lists_when_directories_missing(self) -> None:
        """Test graceful handling when directories don't exist."""
        input_schemas, output_schemas = self._create_test_analyser_with_schemas()

        assert input_schemas == []
        assert output_schemas == []

    def test_input_discovery_skips_private_files(self) -> None:
        """Test __init__.py and _*.py ignored in schema_readers/."""
        input_schemas, _ = self._create_test_analyser_with_schemas(
            input_schema_files={
                "__init__.py": "# Init file",
                "_helper.py": "# Helper",
                "_private_1_0_0.py": "# Private",
                "valid_1_0_0.py": "# Valid",
            }
        )

        assert len(input_schemas) == 1
        assert input_schemas[0].name == "valid"

    def test_output_discovery_skips_private_files(self) -> None:
        """Test __init__.py and _*.py ignored in schema_producers/."""
        _, output_schemas = self._create_test_analyser_with_schemas(
            output_schema_files={
                "__init__.py": "# Init file",
                "_helper.py": "# Helper",
                "_private_1_0_0.py": "# Private",
                "valid_1_0_0.py": "# Valid",
            }
        )

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "valid"

    def test_input_discovery_parses_multi_word_schema_names(self) -> None:
        """Test correct parsing of names like processing_purpose_finding."""
        input_schemas, _ = self._create_test_analyser_with_schemas(
            input_schema_files={"processing_purpose_finding_1_0_0.py": "# Schema"}
        )

        assert len(input_schemas) == 1
        assert input_schemas[0].name == "processing_purpose_finding"
        assert input_schemas[0].version == "1.0.0"

    def test_output_discovery_parses_multi_word_schema_names(self) -> None:
        """Test multi-word names work in schema_producers/."""
        _, output_schemas = self._create_test_analyser_with_schemas(
            output_schema_files={"personal_data_finding_1_0_0.py": "# Schema"}
        )

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_finding"
        assert output_schemas[0].version == "1.0.0"

    def test_component_can_override_both_methods(self) -> None:
        """Test analysers can override both discovery methods."""
        from typing import override

        from waivern_core.base_analyser import Analyser
        from waivern_core.message import Message

        class CustomAnalyser(Analyser):
            @classmethod
            @override
            def get_name(cls) -> str:
                return "custom"

            @classmethod
            @override
            def get_supported_input_schemas(cls) -> list[Schema]:
                # Custom logic - return hardcoded schemas
                return [
                    Schema("custom_input", "2.0.0"),
                    Schema("another_input", "3.5.1"),
                ]

            @classmethod
            @override
            def get_supported_output_schemas(cls) -> list[Schema]:
                # Custom logic - return hardcoded schemas
                return [
                    Schema("custom_output", "1.2.3"),
                    Schema("another_output", "4.0.0"),
                ]

            @override
            def process(
                self, input_schema: Schema, output_schema: Schema, message: Message
            ) -> Message:
                raise NotImplementedError  # Not needed for this test

        input_schemas = CustomAnalyser.get_supported_input_schemas()
        output_schemas = CustomAnalyser.get_supported_output_schemas()

        assert len(input_schemas) == 2
        assert input_schemas[0].name == "custom_input"
        assert input_schemas[0].version == "2.0.0"
        assert input_schemas[1].name == "another_input"
        assert input_schemas[1].version == "3.5.1"

        assert len(output_schemas) == 2
        assert output_schemas[0].name == "custom_output"
        assert output_schemas[0].version == "1.2.3"
        assert output_schemas[1].name == "another_output"
        assert output_schemas[1].version == "4.0.0"

    def test_input_discovery_skips_invalid_filename_formats(self) -> None:
        """Test files without proper version format ignored in schema_readers/."""
        input_schemas, _ = self._create_test_analyser_with_schemas(
            input_schema_files={
                "invalid.py": "# No version",
                "schema_1_0.py": "# Only two version parts",
                "schema.py": "# No version at all",
                "valid_1_0_0.py": "# Valid schema",
            }
        )

        assert len(input_schemas) == 1
        assert input_schemas[0].name == "valid"
        assert input_schemas[0].version == "1.0.0"

    def test_output_discovery_skips_invalid_filename_formats(self) -> None:
        """Test invalid formats ignored in schema_producers/."""
        _, output_schemas = self._create_test_analyser_with_schemas(
            output_schema_files={
                "invalid.py": "# No version",
                "schema_1_0.py": "# Only two version parts",
                "schema.py": "# No version at all",
                "valid_1_0_0.py": "# Valid schema",
            }
        )

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "valid"
        assert output_schemas[0].version == "1.0.0"
