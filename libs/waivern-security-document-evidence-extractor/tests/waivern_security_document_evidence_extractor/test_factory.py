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
        return {}


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

        assert factory.can_create({}) is True

    def test_can_create_fails_without_llm_service(self):
        """can_create() returns False when LLM service is not in container."""
        container = ServiceContainer()
        factory = SecurityDocumentEvidenceExtractorFactory(container)

        assert factory.can_create({}) is False
