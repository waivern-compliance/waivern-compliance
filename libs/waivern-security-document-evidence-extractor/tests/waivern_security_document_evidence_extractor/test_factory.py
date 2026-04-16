"""Tests for SecurityDocumentEvidenceExtractorFactory."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services import ServiceContainer
from waivern_core.testing import ComponentFactoryContractTests

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
    SecurityDocumentEvidenceExtractorFactory,
)


class TestSecurityDocumentEvidenceExtractorFactoryContract(
    ComponentFactoryContractTests[SecurityDocumentEvidenceExtractor],
):
    """Contract tests for SecurityDocumentEvidenceExtractorFactory."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[SecurityDocumentEvidenceExtractor]:
        return SecurityDocumentEvidenceExtractorFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {}
