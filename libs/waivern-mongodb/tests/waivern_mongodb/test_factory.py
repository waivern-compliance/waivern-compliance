"""Tests for MongoDBConnectorFactory - Contract Tests Only."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_core.testing import ComponentFactoryContractTests

from waivern_mongodb import MongoDBConnector, MongoDBConnectorFactory

MONGODB_ENV_VARS = ["MONGODB_URI", "MONGODB_DATABASE"]


class TestMongoDBConnectorFactory(ComponentFactoryContractTests[MongoDBConnector]):
    """Test suite for MongoDBConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[MongoDBConnector]:
        """Provide factory instance for contract tests."""
        container = ServiceContainer()
        return MongoDBConnectorFactory(container)

    @pytest.fixture
    def valid_config(self, monkeypatch: pytest.MonkeyPatch) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        return {
            "uri": "mongodb://localhost:27017",
            "database": "test_db",
        }
