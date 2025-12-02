"""Tests for Connector auto-discovery functionality."""

import tempfile
from pathlib import Path

from waivern_core.schemas.base import Schema


class TestConnectorAutoDiscovery:
    """Tests for auto-discovery of supported output schemas."""

    def create_test_connector_with_schemas(
        self, schema_files: dict[str, str]
    ) -> list[Schema]:
        """Helper to create test connector and return discovered schemas.

        Args:
            schema_files: Dict mapping filename -> file content

        Returns:
            List of discovered schemas
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            connector_dir = Path(tmpdir) / "test_connector"
            connector_dir.mkdir()

            # Create schema_producers directory if there are schema files
            if schema_files:
                schema_dir = connector_dir / "schema_producers"
                schema_dir.mkdir()
                for filename, content in schema_files.items():
                    (schema_dir / filename).write_text(content)

            # Create connector class file
            connector_file = connector_dir / "connector.py"
            connector_file.write_text(
                "from waivern_core.base_connector import Connector\n"
                "from waivern_core.message import Message\n"
                "from waivern_core.schemas.base import Schema\n\n"
                "class TestConnector(Connector):\n"
                "    @classmethod\n"
                "    def get_name(cls) -> str:\n"
                "        return 'test'\n"
                "    def extract(self, output_schema: Schema) -> Message:\n"
                "        pass\n"
            )

            # Dynamically import and get schemas
            import sys

            sys.path.insert(0, str(connector_dir))
            try:
                # Clear any cached connector module
                if "connector" in sys.modules:
                    del sys.modules["connector"]

                from connector import TestConnector  # type: ignore[import-not-found]

                return TestConnector.get_supported_output_schemas()
            finally:
                # Clean up
                if "connector" in sys.modules:
                    del sys.modules["connector"]
                sys.path.remove(str(connector_dir))

    def test_auto_discovery_finds_single_schema_version(self) -> None:
        """Test auto-discovery finds a single schema file."""
        schemas = self.create_test_connector_with_schemas(
            {"standard_input_1_0_0.py": "# Schema producer"}
        )

        assert len(schemas) == 1
        assert schemas[0].name == "standard_input"
        assert schemas[0].version == "1.0.0"

    def test_auto_discovery_finds_multiple_schema_versions(self) -> None:
        """Test auto-discovery finds multiple versions of same schema."""
        schemas = self.create_test_connector_with_schemas(
            {
                "standard_input_1_0_0.py": "# Schema producer v1.0.0",
                "standard_input_1_1_0.py": "# Schema producer v1.1.0",
            }
        )

        assert len(schemas) == 2
        schema_tuples = {(s.name, s.version) for s in schemas}
        assert ("standard_input", "1.0.0") in schema_tuples
        assert ("standard_input", "1.1.0") in schema_tuples

    def test_auto_discovery_parses_multi_word_schema_names(self) -> None:
        """Test correct parsing of schema names with underscores."""
        schemas = self.create_test_connector_with_schemas(
            {"personal_data_finding_1_0_0.py": "# Schema producer"}
        )

        assert len(schemas) == 1
        assert schemas[0].name == "personal_data_finding"
        assert schemas[0].version == "1.0.0"

    def test_auto_discovery_returns_empty_list_when_no_directory(self) -> None:
        """Test graceful handling when schema_producers/ doesn't exist."""
        schemas = self.create_test_connector_with_schemas({})  # No schema files

        assert schemas == []

    def test_auto_discovery_skips_private_files(self) -> None:
        """Test that __init__.py and _private.py files are ignored."""
        schemas = self.create_test_connector_with_schemas(
            {
                "__init__.py": "# Init file",
                "_helper.py": "# Helper file",
                "_private_1_0_0.py": "# Private file",
                "valid_schema_1_0_0.py": "# Valid schema",
            }
        )

        assert len(schemas) == 1
        assert schemas[0].name == "valid_schema"
        assert schemas[0].version == "1.0.0"

    def test_auto_discovery_skips_invalid_filename_formats(self) -> None:
        """Test files without proper version format are ignored."""
        schemas = self.create_test_connector_with_schemas(
            {
                "invalid.py": "# No version",
                "schema_1_0.py": "# Only two version parts",
                "schema.py": "# No version at all",
                "valid_1_0_0.py": "# Valid schema",
            }
        )

        assert len(schemas) == 1
        assert schemas[0].name == "valid"
        assert schemas[0].version == "1.0.0"

    def test_auto_discovery_ignores_non_python_files(self) -> None:
        """Test only .py files are processed."""
        schemas = self.create_test_connector_with_schemas(
            {
                "schema_1_0_0.txt": "# Text file",
                "schema_1_0_0.md": "# Markdown file",
                "README.md": "# Readme",
            }
        )

        assert schemas == []

    def test_component_can_override_auto_discovery(self) -> None:
        """Test components can override with custom logic."""
        # Create a connector that overrides get_supported_output_schemas
        from typing import override

        from waivern_core.base_connector import Connector
        from waivern_core.message import Message
        from waivern_core.schemas.base import Schema

        class CustomConnector(Connector):
            @classmethod
            @override
            def get_name(cls) -> str:
                return "custom"

            @classmethod
            @override
            def get_supported_output_schemas(cls) -> list[Schema]:
                # Custom logic - return hardcoded schemas
                return [
                    Schema("custom_schema", "2.0.0"),
                    Schema("another_schema", "3.5.1"),
                ]

            @override
            def extract(self, output_schema: Schema) -> Message:
                raise NotImplementedError  # Not needed for this test

        schemas = CustomConnector.get_supported_output_schemas()

        assert len(schemas) == 2
        assert schemas[0].name == "custom_schema"
        assert schemas[0].version == "2.0.0"
        assert schemas[1].name == "another_schema"
        assert schemas[1].version == "3.5.1"

    def test_auto_discovery_version_parsing_correctness(self) -> None:
        """Test version numbers are correctly parsed and formatted."""
        schemas = self.create_test_connector_with_schemas(
            {"schema_2_5_11.py": "# Schema with double-digit version"}
        )

        assert len(schemas) == 1
        assert schemas[0].name == "schema"
        assert schemas[0].version == "2.5.11"
