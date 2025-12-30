"""Pytest configuration for waivern-rulesets tests.

This module provides fixtures and configuration for the waivern-rulesets test suite.
"""

import pytest

from waivern_rulesets import RulesetRegistry


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )


@pytest.fixture
def isolated_registry() -> RulesetRegistry:
    """Provide RulesetRegistry instance for tests that need it.

    Note: Workspace-level autouse fixture (conftest.py) already handles
    state isolation automatically. This fixture is for tests that need
    to explicitly access the registry instance.

    Usage:
        def test_something(isolated_registry):
            # Can safely modify registry - workspace fixture restores state
            isolated_registry.register(...)

        # Tests that don't need the instance don't request it:
        def test_without_registry():
            # Still gets automatic state isolation from workspace fixture
            pass

    Returns:
        The singleton RulesetRegistry instance

    """
    return RulesetRegistry()
