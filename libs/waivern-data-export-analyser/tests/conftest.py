"""Pytest configuration for waivern-data-export-analyser tests."""

import pytest

from waivern_data_export_analyser import register_schemas


@pytest.fixture(autouse=True)
def _register_schemas() -> None:  # pyright: ignore[reportUnusedFunction]
    """Register schemas for all tests.

    This fixture runs automatically for all tests.
    """
    register_schemas()
