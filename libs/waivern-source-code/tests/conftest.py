"""Pytest configuration for waivern-source-code tests."""

import pytest


@pytest.fixture(autouse=True)
def _register_schemas():  # pyright: ignore[reportUnusedFunction]
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    from waivern_source_code import register_schemas

    register_schemas()
