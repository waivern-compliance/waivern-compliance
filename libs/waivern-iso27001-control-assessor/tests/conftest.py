"""Pytest configuration for waivern-iso27001-control-assessor tests."""

import pytest

from waivern_iso27001_control_assessor import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    register_schemas()
