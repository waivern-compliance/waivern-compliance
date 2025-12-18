"""Tests for MySQLConnectorFactory - Contract Tests Only."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_core.testing import ComponentFactoryContractTests

from waivern_mysql import MySQLConnector, MySQLConnectorFactory

MYSQL_ENV_VARS = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
]


class TestMySQLConnectorFactory(ComponentFactoryContractTests[MySQLConnector]):
    """Test suite for MySQLConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[MySQLConnector]:
        """Provide factory instance for contract tests."""
        container = ServiceContainer()
        return MySQLConnectorFactory(container)

    @pytest.fixture
    def valid_config(self, monkeypatch: pytest.MonkeyPatch) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        for var in MYSQL_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        return {
            "host": "test.mysql.com",
            "user": "test_user",
        }
