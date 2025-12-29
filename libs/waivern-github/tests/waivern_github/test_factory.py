"""Tests for GitHubConnectorFactory - Contract Tests Only."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services.container import ServiceContainer
from waivern_core.testing import ComponentFactoryContractTests

from waivern_github import GitHubConnector, GitHubConnectorFactory


class TestGitHubConnectorFactory(ComponentFactoryContractTests[GitHubConnector]):
    """Test suite for GitHubConnectorFactory.

    Inherits 6 contract tests from ComponentFactoryContractTests.
    """

    @pytest.fixture
    def factory(self) -> ComponentFactory[GitHubConnector]:
        """Provide factory instance for contract tests."""
        container = ServiceContainer()
        return GitHubConnectorFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for contract tests."""
        return {
            "repository": "owner/repo",
            "ref": "main",
            "clone_strategy": "minimal",
        }
