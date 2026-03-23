"""Pytest configuration for waivern-gdpr-data-subject-classifier tests."""

import pytest
from waivern_schemas import register_schemas

from waivern_gdpr_data_subject_classifier import (
    register_schemas as register_classifier_schemas,
)


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    waivern-schemas registers all indicator + classifier schemas in one call.
    The classifier's own register_schemas() is still needed for its JSON schema.
    """
    register_schemas()
    register_classifier_schemas()
