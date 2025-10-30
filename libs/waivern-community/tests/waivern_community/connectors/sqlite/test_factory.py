"""Tests for SQLiteConnectorFactory - Contract Tests Only."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.testing import ComponentFactoryContractTests

from waivern_community.connectors.sqlite import (
    SQLiteConnector,
    SQLiteConnectorFactory,
)


class TestSQLiteConnectorFactory(ComponentFactoryContractTests[SQLiteConnector]):
    """Test suite for SQLiteConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[SQLiteConnector]:
        """Provide factory instance for contract tests."""
        return SQLiteConnectorFactory()

    @pytest.fixture
    def valid_config(self, tmp_path) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        # Create a temporary SQLite database file
        db_file = tmp_path / "test.db"
        db_file.touch()

        return {"database_path": str(db_file), "max_rows_per_table": 10}
