"""Pytest configuration for waivern-gdpr-personal-data-classifier tests."""

import pytest

from waivern_gdpr_personal_data_classifier import register_schemas


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    register_schemas()
