"""Tests for iso27001_assessment/1.0.0 schema models."""

from waivern_core.schemas import BaseAnalysisOutputMetadata, Schema
from waivern_schemas.iso27001_assessment import (
    CIAProperty,
    ControlStatus,
    ControlType,
    CybersecurityConcept,
    EvidenceStatus,
    ISO27001AssessmentMetadata,
    ISO27001AssessmentModel,
    ISO27001AssessmentOutput,
    ISO27001AssessmentSummary,
    ISOSecurityDomain,
    OperationalCapability,
)


def _build_assessment_model(
    **overrides: object,
) -> ISO27001AssessmentModel:
    """Build an ISO27001AssessmentModel with sensible defaults."""
    defaults: dict[str, object] = {
        "control_ref": "A.8.24",
        "status": ControlStatus.COMPLIANT,
        "evidence_status": EvidenceStatus.AUTOMATED,
        "rationale": "AES-256 encryption detected in data-at-rest layer.",
        "gap_description": None,
        "control_type": ControlType.PREVENTIVE,
        "cia": [CIAProperty.CONFIDENTIALITY],
        "cybersecurity_concept": CybersecurityConcept.PROTECT,
        "operational_capability": OperationalCapability.INFORMATION_PROTECTION,
        "iso_security_domain": ISOSecurityDomain.PROTECTION,
        "metadata": ISO27001AssessmentMetadata(source="A.8.24"),
    }
    defaults.update(overrides)
    return ISO27001AssessmentModel(**defaults)  # type: ignore[arg-type]


class TestISO27001AssessmentModel:
    """Tests for the ISO27001AssessmentModel."""

    def test_assessment_model_valid_instantiation(self):
        """Model accepts valid fields with all StrEnum values coerced correctly."""
        model = _build_assessment_model()

        assert model.control_ref == "A.8.24"
        assert model.status == ControlStatus.COMPLIANT
        assert model.evidence_status == EvidenceStatus.AUTOMATED
        assert model.rationale == "AES-256 encryption detected in data-at-rest layer."
        assert model.gap_description is None
        assert model.control_type == ControlType.PREVENTIVE
        assert model.cia == [CIAProperty.CONFIDENTIALITY]
        assert model.cybersecurity_concept == CybersecurityConcept.PROTECT
        assert (
            model.operational_capability == OperationalCapability.INFORMATION_PROTECTION
        )
        assert model.iso_security_domain == ISOSecurityDomain.PROTECTION
        assert model.metadata.source == "A.8.24"
        assert model.id  # UUID auto-generated

    def test_assessment_model_satisfies_finding_protocol(self):
        """Model instance satisfies Finding protocol (id + metadata.source)."""
        model = _build_assessment_model()

        assert isinstance(model.id, str)
        assert len(model.id) > 0
        assert isinstance(model.metadata.source, str)
        assert model.metadata.source == "A.8.24"


class TestISO27001AssessmentOutput:
    """Tests for the output wire format model."""

    def test_output_model_serialisation_round_trip(self):
        """Output serialises to dict and deserialises back correctly."""
        model = _build_assessment_model(
            status=ControlStatus.NON_COMPLIANT,
            evidence_status=EvidenceStatus.AUTOMATED,
            rationale="No encryption detected.",
            gap_description="Implement AES-256 for data at rest.",
        )
        output = ISO27001AssessmentOutput(
            findings=[model],
            summary=ISO27001AssessmentSummary(
                total_controls=1,
                compliant_count=0,
                partial_count=0,
                non_compliant_count=1,
                not_assessed_count=0,
                automated_count=1,
                requires_attestation_count=0,
                insufficient_evidence_count=0,
            ),
            analysis_metadata=BaseAnalysisOutputMetadata(
                ruleset_used="local/iso27001_domains/1.0.0",
                llm_validation_enabled=True,
            ),
        )

        serialised = output.model_dump()
        restored = ISO27001AssessmentOutput.model_validate(serialised)

        assert len(restored.findings) == 1
        finding = restored.findings[0]
        assert finding.control_ref == "A.8.24"
        assert finding.status == ControlStatus.NON_COMPLIANT
        assert finding.evidence_status == EvidenceStatus.AUTOMATED
        assert finding.gap_description == "Implement AES-256 for data at rest."
        assert finding.control_type == ControlType.PREVENTIVE
        assert finding.cia == [CIAProperty.CONFIDENTIALITY]
        assert finding.cybersecurity_concept == CybersecurityConcept.PROTECT
        assert (
            finding.operational_capability
            == OperationalCapability.INFORMATION_PROTECTION
        )
        assert finding.iso_security_domain == ISOSecurityDomain.PROTECTION
        assert restored.summary.total_controls == 1
        assert restored.summary.non_compliant_count == 1
        assert restored.analysis_metadata.ruleset_used == "local/iso27001_domains/1.0.0"


class TestRegisterSchemas:
    """Tests for schema registration."""

    def test_register_schemas_registers_search_path(self):
        """register_schemas() registers with SchemaRegistry successfully."""
        # register_schemas() is called by conftest autouse fixture
        # Verify the schema can be loaded by constructing a Schema and
        # triggering lazy load via get_json_schema()
        schema = Schema("iso27001_assessment", "1.0.0")

        assert schema.name == "iso27001_assessment"
        assert schema.version == "1.0.0"
        assert schema.schema is not None
