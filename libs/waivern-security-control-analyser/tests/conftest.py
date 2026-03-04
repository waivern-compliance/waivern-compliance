"""Pytest configuration for waivern-security-control-analyser tests."""

import pytest
from waivern_security_evidence import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    This package does not own the security_evidence/1.0.0 schema —
    waivern-security-evidence does. That package exposes register_schemas()
    which loads the JSON schema into the shared schema registry.
    Calling it here ensures Message.validate() can resolve the schema
    during tests without the package having its own schema files.
    """
    register_schemas()
