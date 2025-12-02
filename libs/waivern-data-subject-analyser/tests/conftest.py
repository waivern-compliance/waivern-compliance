"""Test configuration for waivern-data-subject-analyser."""

import pytest

from waivern_data_subject_analyser import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Register schemas for all tests.

    This fixture automatically runs before every test to ensure schemas are registered.
    """
    register_schemas()
