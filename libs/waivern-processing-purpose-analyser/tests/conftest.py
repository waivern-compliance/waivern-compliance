"""Test configuration for waivern-processing-purpose-analyser."""

import pytest

from waivern_processing_purpose_analyser import register_schemas


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Register schemas for all tests.

    This fixture automatically runs before every test to ensure schemas are registered.
    """
    register_schemas()
