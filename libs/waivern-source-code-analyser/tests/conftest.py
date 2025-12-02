"""Pytest configuration for waivern-source-code tests."""

import pytest


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    from waivern_source_code_analyser import register_schemas

    register_schemas()
