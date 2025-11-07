"""Pytest configuration for waivern-community tests.

This module provides fixtures and configuration for the waivern-community test suite.
"""

from collections.abc import Iterator
from importlib.metadata import entry_points
from typing import Any

import pytest
from waivern_core import BaseRule
from waivern_rulesets import RulesetRegistry
from waivern_rulesets.base import AbstractRuleset


@pytest.fixture(autouse=True)
def _register_all_schemas():  # pyright: ignore[reportUnusedFunction]
    """Automatically register all schemas for waivern-community tests.

    Discovers and registers schemas from all installed packages via entry points.
    This ensures that schemas from standalone packages (like waivern-source-code)
    are available to tests.
    """
    schema_eps = entry_points(group="waivern.schemas")

    for ep in schema_eps:
        try:
            register_func = ep.load()
            register_func()
        except Exception:  # noqa: S110
            # Ignore failures - some schemas might not be available
            pass


@pytest.fixture
def isolated_registry() -> Iterator[RulesetRegistry]:
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
