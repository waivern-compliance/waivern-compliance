"""Pytest configuration for waivern-mysql tests."""

import pytest
from waivern_schemas import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Register waivern-schemas so standard_input JSON schema is discoverable."""
    register_schemas()


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require real API calls)",
    )
