"""Workspace-level pytest configuration and fixtures.

This file provides shared fixtures and configuration for all tests across
the entire monorepo workspace.

See docs/how-tos/testing-patterns.md for the singleton testing pattern.
"""

import pytest
from dotenv import load_dotenv
from waivern_core.schemas import SchemaRegistry
from waivern_rulesets import RulesetRegistry
from waivern_source_code_analyser.languages.registry import LanguageRegistry
from wct.exporters.registry import ExporterRegistry

# Load environment variables from workspace root .env file
# This provides API keys and credentials for integration tests and CLI
load_dotenv()


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


@pytest.fixture(autouse=True, scope="function")
def isolate_ruleset_registry():
    """Automatically preserve and restore RulesetRegistry state for each test.

    This fixture ensures test isolation by:
    1. Capturing RulesetRegistry state before each test
    2. Restoring the exact state after each test completes
    3. Running automatically for ALL tests (autouse=True)

    Why this is needed:
    - RulesetRegistry is a singleton with mutable global state
    - Tests that clear/modify the registry would break subsequent tests
    - Without isolation, test execution order affects test results

    This is the industry standard pattern for testing singletons in Python.
    """
    # Capture state before test runs
    saved_state = RulesetRegistry.snapshot_state()

    yield  # Test runs here

    # Restore state after test completes (even if test fails)
    RulesetRegistry.restore_state(saved_state)


@pytest.fixture(autouse=True, scope="function")
def isolate_exporter_registry():
    """Automatically preserve and restore ExporterRegistry state for each test.

    This fixture ensures test isolation by:
    1. Capturing ExporterRegistry state before each test
    2. Restoring the exact state after each test completes
    3. Running automatically for ALL tests (autouse=True)

    Why this is needed:
    - ExporterRegistry is a singleton with mutable global state
    - Tests that clear/modify the registry would break subsequent tests
    - Without isolation, test execution order affects test results

    This is the industry standard pattern for testing singletons in Python.
    """
    # Capture state before test runs
    saved_state = ExporterRegistry.snapshot_state()

    yield  # Test runs here

    # Restore state after test completes (even if test fails)
    ExporterRegistry.restore_state(saved_state)


@pytest.fixture(autouse=True, scope="function")
def isolate_language_registry():
    """Automatically preserve and restore LanguageRegistry state for each test.

    This fixture ensures test isolation by:
    1. Capturing LanguageRegistry state before each test
    2. Restoring the exact state after each test completes
    3. Running automatically for ALL tests (autouse=True)

    Why this is needed:
    - LanguageRegistry is a singleton with mutable global state
    - Tests that clear/modify the registry would break subsequent tests
    - Without isolation, test execution order affects test results

    This is the industry standard pattern for testing singletons in Python.
    """
    # Capture state before test runs
    saved_state = LanguageRegistry.snapshot_state()

    yield  # Test runs here

    # Restore state after test completes (even if test fails)
    LanguageRegistry.restore_state(saved_state)
