"""Pytest configuration for waivern-data-collection-analyser tests."""

import pytest

from waivern_data_collection_analyser import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    This package owns the data_collection_indicator/1.0.0 schema.
    Calling register_schemas() ensures Message.validate() can resolve
    the schema during tests.
    """
    register_schemas()
