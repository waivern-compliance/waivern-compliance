"""Tests for SecurityDocumentEvidenceExtractorFactory."""

from unittest.mock import Mock

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory
from waivern_core.testing import ComponentFactoryContractTests
from waivern_llm import LLMService

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
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))
        return SecurityDocumentEvidenceExtractorFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "enable_llm_classification": True,
        }


class TestSecurityDocumentEvidenceExtractorFactory:
    """Tests for factory behaviour."""

    def test_can_create_with_llm_service_available(self):
        """can_create() returns True when LLM service is in container."""
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))

        factory = SecurityDocumentEvidenceExtractorFactory(container)

        assert factory.can_create({"enable_llm_classification": True}) is True

    def test_can_create_without_llm_when_classification_disabled(self):
        """can_create() returns True without LLM when enable_llm_classification=False."""
        container = ServiceContainer()
        factory = SecurityDocumentEvidenceExtractorFactory(container)

        assert factory.can_create({"enable_llm_classification": False}) is True
