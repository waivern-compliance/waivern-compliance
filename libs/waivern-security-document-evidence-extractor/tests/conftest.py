"""Pytest configuration for waivern-security-document-evidence-extractor tests."""

import pytest

from waivern_security_document_evidence_extractor import register_schemas


@pytest.fixture(autouse=True)
def register_test_schemas() -> None:
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    register_schemas()
