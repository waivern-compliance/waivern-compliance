"""Tests for SourceCodeConnectorFactory - Contract Tests Only."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.testing import ComponentFactoryContractTests

from waivern_community.connectors.source_code import (
    SourceCodeConnector,
    SourceCodeConnectorFactory,
)


class TestSourceCodeConnectorFactory(
    ComponentFactoryContractTests[SourceCodeConnector]
):
    """Test suite for SourceCodeConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[SourceCodeConnector]:
        """Provide factory instance for contract tests."""
        return SourceCodeConnectorFactory()

    @pytest.fixture
    def valid_config(self, tmp_path) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        # Create a temporary PHP file for testing
        test_file = tmp_path / "test.php"
        test_file.write_text("<?php\nfunction hello() {\n    return 'world';\n}\n")

        return {
            "path": str(test_file),
            "language": "php",
        }
