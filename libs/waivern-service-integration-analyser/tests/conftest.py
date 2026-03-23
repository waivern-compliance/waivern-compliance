"""Pytest configuration for waivern-service-integration-analyser tests."""

import pytest
from waivern_schemas import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    This package owns the service_integration_indicator/1.0.0 schema.
    Calling register_schemas() ensures Message.validate() can resolve
    the schema during tests.
    """
    register_schemas()
