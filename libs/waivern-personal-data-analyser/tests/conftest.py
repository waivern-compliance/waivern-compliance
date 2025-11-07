"""Pytest configuration for waivern-personal-data-analyser tests."""

import pytest

from waivern_personal_data_analyser import register_schemas


@pytest.fixture(autouse=True)
def _register_schemas() -> None:  # pyright: ignore[reportUnusedFunction]
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    register_schemas()
