"""Tests for security_document_context/1.0.0 schema models."""

import pytest
from pydantic import ValidationError
from waivern_core.types import SecurityDomain

from waivern_security_document_evidence_extractor.schemas.types import (
    SecurityDocumentContextMetadata,
    SecurityDocumentContextModel,
    SecurityDocumentContextOutput,
    SecurityDocumentContextSummary,
)


def _build_context_model(
    **overrides: object,
) -> SecurityDocumentContextModel:
    """Build a SecurityDocumentContextModel with sensible defaults."""
    defaults: dict[str, object] = {
        "filename": "encryption-policy.md",
        "content": "All data at rest must be encrypted using AES-256.",
        "summary": "Mandates AES-256 encryption for all data at rest.",
        "security_domains": [SecurityDomain.ENCRYPTION],
        "metadata": SecurityDocumentContextMetadata(source="encryption-policy.md"),
    }
    defaults.update(overrides)
    return SecurityDocumentContextModel(**defaults)  # type: ignore[arg-type]


class TestSecurityDocumentContextModel:
    """Tests for the SecurityDocumentContextModel."""

    # =========================================================================
    # Model validation
    # =========================================================================

    def test_context_model_valid_instantiation(self):
        """Model accepts valid fields with SecurityDomain values."""
        model = _build_context_model()

        assert model.filename == "encryption-policy.md"
        assert model.content == "All data at rest must be encrypted using AES-256."
        assert model.security_domains == [SecurityDomain.ENCRYPTION]
        assert model.metadata.source == "encryption-policy.md"
        assert model.id  # UUID auto-generated

    def test_context_model_empty_security_domains_accepted(self):
        """Empty security_domains list is accepted (cross-cutting flag)."""
        model = _build_context_model(
            filename="org-context.md",
            content="We are a fintech startup.",
            security_domains=[],
            metadata=SecurityDocumentContextMetadata(source="org-context.md"),
        )

        assert model.security_domains == []

    def test_context_model_all_security_domain_values_accepted(self):
        """Every SecurityDomain enum member is accepted in security_domains."""
        all_domains = list(SecurityDomain)
        model = _build_context_model(security_domains=all_domains)

        assert model.security_domains == all_domains

    def test_context_model_invalid_security_domain_rejected(self):
        """Invalid string in security_domains raises ValidationError."""
        with pytest.raises(ValidationError, match="security_domains"):
            _build_context_model(security_domains=["not_a_real_domain"])

    # =========================================================================
    # Finding protocol compatibility
    # =========================================================================

    def test_context_model_satisfies_finding_protocol(self):
        """Model instance satisfies Finding protocol (id + metadata.source)."""
        model = _build_context_model()

        # Finding protocol requires: id (str) and metadata.source (str)
        assert isinstance(model.id, str)
        assert len(model.id) > 0
        assert isinstance(model.metadata.source, str)
        assert model.metadata.source == "encryption-policy.md"


class TestSecurityDocumentContextOutput:
    """Tests for the output wire format model."""

    def test_output_model_serialisation_round_trip(self):
        """Output serialises to dict and deserialises back correctly."""
        from waivern_core.schemas import BaseAnalysisOutputMetadata

        model = _build_context_model()
        output = SecurityDocumentContextOutput(
            findings=[model],
            summary=SecurityDocumentContextSummary(
                total_documents=1,
                cross_cutting_count=0,
                domain_coverage=["encryption"],
            ),
            analysis_metadata=BaseAnalysisOutputMetadata(
                ruleset_used="n/a",
                llm_validation_enabled=True,
            ),
        )

        serialised = output.model_dump()
        restored = SecurityDocumentContextOutput.model_validate(serialised)

        assert len(restored.findings) == 1
        assert restored.findings[0].filename == "encryption-policy.md"
        assert restored.findings[0].content == model.content
        assert restored.findings[0].security_domains == [SecurityDomain.ENCRYPTION]
        assert restored.summary.total_documents == 1
        assert restored.summary.cross_cutting_count == 0
        assert restored.summary.domain_coverage == ["encryption"]


class TestRegisterSchemas:
    """Tests for schema registration."""

    def test_register_schemas_registers_search_path(self):
        """register_schemas() registers with SchemaRegistry successfully."""
        from waivern_core.schemas import Schema

        # register_schemas() is called by conftest autouse fixture
        # Verify the schema can be loaded by constructing a Schema and
        # triggering lazy load via get_json_schema()
        schema = Schema("security_document_context", "1.0.0")

        assert schema.name == "security_document_context"
        assert schema.version == "1.0.0"
        assert schema.schema is not None
