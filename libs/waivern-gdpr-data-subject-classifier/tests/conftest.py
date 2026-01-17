"""Pytest configuration for waivern-gdpr-data-subject-classifier tests."""

import pytest
from waivern_data_subject_analyser import (
    register_schemas as register_analyser_schemas,
)

from waivern_gdpr_data_subject_classifier import register_schemas


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

    For pipeline integration tests, we also need the data_subject_indicator
    schema from waivern-data-subject-analyser.
    """
    register_schemas()
    register_analyser_schemas()
