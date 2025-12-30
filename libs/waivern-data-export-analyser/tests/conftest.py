"""Pytest configuration for waivern-data-export-analyser tests."""

import pytest

from waivern_data_export_analyser import register_schemas


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Register schemas for all tests.

    This fixture runs automatically for all tests.
    """
    register_schemas()
