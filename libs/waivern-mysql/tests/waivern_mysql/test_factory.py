"""Tests for MySQLConnectorFactory - Contract Tests Only."""

import os
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.testing import ComponentFactoryContractTests

from waivern_mysql import MySQLConnector, MySQLConnectorFactory


@contextmanager
def clear_mysql_env_vars() -> Generator[None, None, None]:
    """Context manager to temporarily clear MySQL environment variables for test isolation."""
    mysql_env_vars = [
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ]
    saved_env = {var: os.environ.pop(var, None) for var in mysql_env_vars}
    try:
        yield
    finally:
        # Restore environment variables
        for var, value in saved_env.items():
            if value is not None:
                os.environ[var] = value


class TestMySQLConnectorFactory(ComponentFactoryContractTests[MySQLConnector]):
    """Test suite for MySQLConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[MySQLConnector]:
        """Provide factory instance for contract tests."""
        return MySQLConnectorFactory()

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        with clear_mysql_env_vars():
            return {
                "host": "test.mysql.com",
                "user": "test_user",
            }
