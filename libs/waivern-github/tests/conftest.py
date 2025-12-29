"""Pytest configuration for waivern-github tests."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require network/auth)",
    )
