"""Pytest configuration for waivern-community tests.

This module provides fixtures and configuration for the waivern-community test suite.
"""

from typing import Any

import pytest

from waivern_community.rulesets import RulesetRegistry
from waivern_community.rulesets.base import AbstractRuleset
from waivern_community.rulesets.types import BaseRule


@pytest.fixture
def isolated_registry() -> RulesetRegistry:
    """Provide isolated registry that auto-restores state after test.

    This fixture captures the current registry state before the test runs,
    then restores it after the test completes. This allows tests to safely
    call registry.clear() without affecting other tests.

    Usage:
        def test_something(isolated_registry):
            isolated_registry.clear()  # Safe - state will be restored
            # Test code here

    Returns:
        The singleton RulesetRegistry instance
    """
    registry = RulesetRegistry()

    # Capture current state before test runs
    saved_state: dict[str, tuple[type[AbstractRuleset[Any]], type[BaseRule]]] = {
        name: (registry._registry[name], registry._type_mapping[name])  # type: ignore[attr-defined]
        for name in list(registry._registry.keys())  # type: ignore[attr-defined]
    }

    yield registry

    # Restore state after test completes
    registry.clear()
    for name, (ruleset_class, rule_type) in saved_state.items():
        registry.register(name, ruleset_class, rule_type)
