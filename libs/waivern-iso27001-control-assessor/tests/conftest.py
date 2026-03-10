"""Pytest configuration for waivern-iso27001-control-assessor tests."""

import pytest
from waivern_security_document_evidence_extractor import (
    register_schemas as register_document_context_schemas,
)
from waivern_security_evidence import register_schemas as register_evidence_schemas

from waivern_iso27001_control_assessor import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    Registers schemas from this package and its dependencies so that
    Schema objects can resolve their JSON schemas during tests.
    """
    register_schemas()
    register_evidence_schemas()
    register_document_context_schemas()
