"""Workspace-level pytest configuration and fixtures.

This file provides shared fixtures and configuration for all tests across
the entire monorepo workspace.
"""

import pytest
from waivern_core.schemas import SchemaRegistry


@pytest.fixture(autouse=True, scope="function")
def isolate_schema_registry():
    """Automatically preserve and restore SchemaRegistry state for each test.

    This fixture ensures test isolation by:
    1. Capturing SchemaRegistry state before each test
    2. Restoring the exact state after each test completes
    3. Running automatically for ALL tests (autouse=True)

    Why this is needed:
    - SchemaRegistry is a singleton with mutable global state
    - Tests that clear/modify the registry would break subsequent tests
    - Without isolation, test execution order affects test results

    This is the industry standard pattern for testing singletons in Python.
    """
    # Capture state before test runs
    saved_state = SchemaRegistry.snapshot_state()

    yield  # Test runs here

    # Restore state after test completes (even if test fails)
    SchemaRegistry.restore_state(saved_state)
