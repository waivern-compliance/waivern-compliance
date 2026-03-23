"""Pytest configuration for waivern-security-control-analyser tests."""

import pytest
from waivern_schemas import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests."""
    register_schemas()
