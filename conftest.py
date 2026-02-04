"""Workspace-level pytest configuration and fixtures.

This file provides shared fixtures and configuration for all tests across
the entire monorepo workspace.

See docs/how-tos/testing-patterns.md for the singleton testing pattern.
"""

import pytest
from dotenv import load_dotenv
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_core.schemas import SchemaRegistry
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_llm.v2 import LLMService, LLMServiceFactory
from waivern_rulesets.core.registry import RulesetRegistry
from waivern_source_code_analyser.languages.registry import LanguageRegistry
from wct.exporters.registry import ExporterRegistry

# Load environment variables from workspace root .env file
# This provides API keys and credentials for integration tests and CLI
load_dotenv()


@pytest.fixture
def llm_service() -> LLMService:
    """Create LLM service based on .env configuration.

    Uses LLM_PROVIDER env var to select provider:
    - anthropic: Uses ANTHROPIC_API_KEY
    - openai: Uses OPENAI_API_KEY (or OPENAI_BASE_URL for local LLMs)
    - google: Uses GOOGLE_API_KEY

    For local development with LM Studio:
        LLM_PROVIDER=openai
        OPENAI_BASE_URL=http://localhost:1234/v1
        OPENAI_MODEL=your-local-model

    Skips the test if LLM service is not configured.
    """
    # Create minimal container with dependencies
    container = ServiceContainer()
    container.register(
        ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
    )

    factory = LLMServiceFactory(container)
    if not factory.can_create():
        pytest.skip("LLM service not configured")

    service = factory.create()
    if service is None:
        pytest.skip("LLM service not configured")

    return service


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
