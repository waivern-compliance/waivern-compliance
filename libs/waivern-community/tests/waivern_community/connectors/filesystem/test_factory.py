"""Tests for FilesystemConnectorFactory."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.testing import ComponentFactoryContractTests

from waivern_community.connectors.filesystem import (
    FilesystemConnector,
    FilesystemConnectorConfig,
    FilesystemConnectorFactory,
)


class TestFilesystemConnectorFactory(
    ComponentFactoryContractTests[FilesystemConnector]
):
    """Test suite for FilesystemConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests:
    - test_create_returns_correct_type
    - test_create_with_invalid_config_raises_type_error
    - test_can_create_returns_true_for_valid_config
    - test_can_create_returns_false_for_invalid_config
    - test_get_component_name_returns_string
    - test_schemas_are_wct_schema_instances
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[FilesystemConnector]:
        """Provide factory instance for contract tests."""
        return FilesystemConnectorFactory()

    @pytest.fixture
    def valid_config(self, tmp_path) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        # Create a temporary file for testing
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        return FilesystemConnectorConfig.from_properties({"path": str(test_file)})
