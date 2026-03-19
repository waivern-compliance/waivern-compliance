"""Unit tests for SecurityEvidenceNormaliser."""

import logging

import pytest
from pydantic import ValidationError
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_security_evidence_normaliser.analyser import SecurityEvidenceNormaliser
from waivern_security_evidence_normaliser.types import SecurityEvidenceNormaliserConfig

# =============================================================================
# Contract tests
# =============================================================================


class TestSecurityEvidenceNormaliserConfig:
    """Tests for SecurityEvidenceNormaliserConfig validation."""

    def test_maximum_evidence_items_must_be_at_least_one(self) -> None:
        """maximum_evidence_items=0 raises a validation error."""
        with pytest.raises(ValidationError):
            SecurityEvidenceNormaliserConfig(maximum_evidence_items=0)


class TestSecurityEvidenceNormaliserContract(
    AnalyserContractTests[SecurityEvidenceNormaliser]
):
    """Contract tests for SecurityEvidenceNormaliser.

    Inherits from AnalyserContractTests to verify that SecurityEvidenceNormaliser
    meets the Analyser interface contract.
    """

    @pytest.fixture
    def processor_class(self) -> type[SecurityEvidenceNormaliser]:
        """Provide the processor class for contract testing."""
        return SecurityEvidenceNormaliser


# =============================================================================
# Personal data indicator → security evidence mapping
# =============================================================================


class TestNormalisePersonalData:
    """Tests for personal_data_indicator → security evidence normalisation."""

    @pytest.fixture
    def valid_config(self) -> SecurityEvidenceNormaliserConfig:
        """Return default configuration using local domain mapping ruleset."""
        return SecurityEvidenceNormaliserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def _make_message(
        self, category: str, source: str, require_review: bool | None = None
    ) -> Message:
        """Build a personal_data_indicator message with a single finding."""
        finding: dict[str, object] = {
            "id": f"test-{category}",
            "category": category,
            "evidence": [{"content": f"Detected {category} in {source}"}],
            "matched_patterns": [{"pattern": category, "match_count": 1}],
            "metadata": {"source": source},
        }
        if require_review is not None:
            finding["require_review"] = require_review
        return Message(
            id="test_pd",
            content={
                "findings": [finding],
                "summary": {"total_findings": 1},
                "analysis_metadata": {
                    "ruleset_used": "local/personal_data_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )

    def test_personal_data_category_maps_to_expected_security_domain(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A known category (email) maps to data_protection with neutral polarity."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("email", "user.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "data_protection"
        assert findings[0]["polarity"] == "neutral"
        assert findings[0]["evidence_type"] == "CODE"

    def test_personal_data_findings_with_same_category_and_source_file_are_grouped(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """Multiple findings sharing category+source produce a single grouped evidence item."""
        finding: dict[str, object] = {
            "id": "test-email-1",
            "category": "email",
            "evidence": [{"content": "email@example.com"}],
            "matched_patterns": [{"pattern": "email", "match_count": 2}],
            "metadata": {"source": "user.php"},
        }
        msg = Message(
            id="test_pd_grouped",
            content={
                "findings": [finding, {**finding, "id": "test-email-2"}],
                "summary": {"total_findings": 2},
                "analysis_metadata": {
                    "ruleset_used": "local/personal_data_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(valid_config)
        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert "2 occurrence(s)" in findings[0]["description"]

    def test_sensitive_personal_data_category_produces_secondary_domain_evidence_item(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A sensitive category (health) produces evidence for both data_protection and people_controls."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("health", "health.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        domains = {f["security_domain"] for f in findings}
        assert len(findings) == 2
        assert "data_protection" in domains
        assert "people_controls" in domains

    def test_unknown_personal_data_category_is_skipped_silently(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unmapped category is skipped and a debug message is logged."""
        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        msg = self._make_message("unknown_xyz", "file.php")

        with caplog.at_level(logging.DEBUG):
            result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        assert result.content["findings"] == []
        assert "unknown_xyz" in caplog.text


# =============================================================================
# Processing purpose indicator → security evidence mapping
# =============================================================================


class TestNormaliseProcessingPurpose:
    """Tests for processing_purpose_indicator → security evidence normalisation."""

    @pytest.fixture
    def valid_config(self) -> SecurityEvidenceNormaliserConfig:
        """Return default configuration using local domain mapping ruleset."""
        return SecurityEvidenceNormaliserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def _make_message(self, purpose: str, source: str) -> Message:
        """Build a processing_purpose_indicator message with a single finding."""
        return Message(
            id="test_pp",
            content={
                "findings": [
                    {
                        "id": f"test-{purpose}",
                        "purpose": purpose,
                        "evidence": [{"content": f"Detected {purpose} in {source}"}],
                        "matched_patterns": [{"pattern": purpose, "match_count": 1}],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {
                    "total_findings": 1,
                    "purposes_identified": 1,
                    "purposes": [{"purpose": purpose, "findings_count": 1}],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/processing_purposes/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("processing_purpose_indicator", "1.0.0"),
        )

    def test_processing_purpose_maps_to_expected_security_domain(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A known purpose (user_identity_login) maps to the authentication domain."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("user_identity_login", "auth.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "authentication"
        assert findings[0]["polarity"] == "neutral"

    def test_processing_purpose_findings_with_same_purpose_and_source_file_are_grouped(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """Multiple findings sharing purpose+source produce a single grouped evidence item."""
        finding: dict[str, object] = {
            "id": "test-login-1",
            "purpose": "user_identity_login",
            "evidence": [{"content": "login check"}],
            "matched_patterns": [{"pattern": "user_identity_login", "match_count": 1}],
            "metadata": {"source": "auth.php"},
        }
        msg = Message(
            id="test_pp_grouped",
            content={
                "findings": [finding, {**finding, "id": "test-login-2"}],
                "summary": {
                    "total_findings": 2,
                    "purposes_identified": 1,
                    "purposes": [
                        {"purpose": "user_identity_login", "findings_count": 2}
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/processing_purposes/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("processing_purpose_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(valid_config)
        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert "2 occurrence(s)" in findings[0]["description"]

    def test_unknown_processing_purpose_is_skipped_silently(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unmapped purpose is skipped and a debug message is logged."""
        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        msg = self._make_message("unknown_purpose_xyz", "file.php")

        with caplog.at_level(logging.DEBUG):
            result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        assert result.content["findings"] == []
        assert "unknown_purpose_xyz" in caplog.text


# =============================================================================
# Crypto quality indicator → security evidence mapping
# =============================================================================


class TestNormaliseCryptoQuality:
    """Tests for crypto_quality_indicator → security evidence normalisation."""

    @pytest.fixture
    def valid_config(self) -> SecurityEvidenceNormaliserConfig:
        """Return default configuration using local domain mapping ruleset."""
        return SecurityEvidenceNormaliserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def _make_message(
        self,
        algorithm: str,
        quality_rating: str,
        polarity: str,
        source: str = "crypto.php",
    ) -> Message:
        """Build a crypto_quality_indicator message with a single finding."""
        return Message(
            id="test_cq",
            content={
                "findings": [
                    {
                        "id": f"test-{algorithm}",
                        "algorithm": algorithm,
                        "quality_rating": quality_rating,
                        "polarity": polarity,
                        "evidence": [{"content": f"Found {algorithm} usage"}],
                        "matched_patterns": [{"pattern": algorithm, "match_count": 1}],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {"total_findings": 1},
                "analysis_metadata": {
                    "ruleset_used": "local/crypto_quality_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("crypto_quality_indicator", "1.0.0"),
        )

    def test_strong_crypto_algorithm_produces_positive_polarity_evidence(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A strong algorithm (bcrypt) produces encryption evidence with positive polarity."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("bcrypt", "strong", "positive")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "encryption"
        assert findings[0]["polarity"] == "positive"

    def test_deprecated_crypto_algorithm_produces_negative_polarity_evidence(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A deprecated algorithm (md5) produces encryption evidence with negative polarity."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("md5", "deprecated", "negative")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "encryption"
        assert findings[0]["polarity"] == "negative"

    def test_evidence_items_from_upstream_finding_are_propagated(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A finding's evidence snippet is propagated into the output SecurityEvidenceModel."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("bcrypt", "strong", "positive")

        result = analyser.process([msg], output_schema)

        finding = result.content["findings"][0]
        assert len(finding["evidence"]) == 1
        assert finding["evidence"][0]["content"] == "Found bcrypt usage"

    def test_evidence_items_collected_across_all_findings_in_group(
        self,
        output_schema: Schema,
    ) -> None:
        """Evidence items are collected from all findings in a group, not just the first."""
        finding_base: dict[str, object] = {
            "algorithm": "bcrypt",
            "quality_rating": "strong",
            "polarity": "positive",
            "matched_patterns": [{"pattern": "bcrypt", "match_count": 1}],
            "metadata": {"source": "auth.php"},
        }
        msg = Message(
            id="test_cq_group",
            content={
                "findings": [
                    {
                        **finding_base,
                        "id": "f1",
                        "evidence": [{"content": "bcrypt_hash($pw)"}],
                    },
                    {
                        **finding_base,
                        "id": "f2",
                        "evidence": [{"content": "bcrypt_verify($pw)"}],
                    },
                ],
                "summary": {"total_findings": 2},
                "analysis_metadata": {
                    "ruleset_used": "local/crypto_quality_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("crypto_quality_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg], output_schema)

        finding = result.content["findings"][0]
        contents = [e["content"] for e in finding["evidence"]]
        assert "bcrypt_hash($pw)" in contents
        assert "bcrypt_verify($pw)" in contents

    def test_evidence_items_capped_at_configured_maximum(
        self,
        output_schema: Schema,
    ) -> None:
        """Evidence items are capped at maximum_evidence_items from config."""
        finding_base: dict[str, object] = {
            "algorithm": "bcrypt",
            "quality_rating": "strong",
            "polarity": "positive",
            "matched_patterns": [{"pattern": "bcrypt", "match_count": 1}],
            "metadata": {"source": "auth.php"},
        }
        findings = [
            {**finding_base, "id": f"f{i}", "evidence": [{"content": f"snippet_{i}"}]}
            for i in range(4)
        ]
        msg = Message(
            id="test_cq_cap",
            content={
                "findings": findings,
                "summary": {"total_findings": 4},
                "analysis_metadata": {
                    "ruleset_used": "local/crypto_quality_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("crypto_quality_indicator", "1.0.0"),
        )

        config = SecurityEvidenceNormaliserConfig(maximum_evidence_items=2)
        analyser = SecurityEvidenceNormaliser(config)
        result = analyser.process([msg], output_schema)

        assert len(result.content["findings"][0]["evidence"]) == 2

    def test_unknown_crypto_algorithm_is_skipped_silently(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unmapped algorithm is skipped and a debug message is logged."""
        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        msg = self._make_message("unknown_algo_xyz", "weak", "negative")

        with caplog.at_level(logging.DEBUG):
            result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        assert result.content["findings"] == []
        assert "unknown_algo_xyz" in caplog.text


# =============================================================================
# require_review propagation
# =============================================================================


class TestRequireReviewPropagation:
    """Tests for require_review propagation from indicator findings to evidence items."""

    def test_require_review_true_in_any_finding_propagates_to_evidence_item(
        self,
    ) -> None:
        """A single True in a grouped set propagates require_review=True to the evidence item."""
        finding_base: dict[str, object] = {
            "category": "email",
            "evidence": [{"content": "email@example.com"}],
            "matched_patterns": [{"pattern": "email", "match_count": 1}],
            "metadata": {"source": "user.php"},
        }
        msg = Message(
            id="test_rr",
            content={
                "findings": [
                    {**finding_base, "id": "f1", "require_review": True},
                    {**finding_base, "id": "f2"},
                ],
                "summary": {"total_findings": 2},
                "analysis_metadata": {
                    "ruleset_used": "local/personal_data_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["require_review"] is True


# =============================================================================
# Fan-in (multiple input messages of same schema type)
# =============================================================================


class TestFanIn:
    """Tests for fan-in: multiple input messages of the same schema type."""

    def _make_pd_message(self, msg_id: str, category: str, source: str) -> Message:
        """Build a personal_data_indicator message with a single finding."""
        return Message(
            id=msg_id,
            content={
                "findings": [
                    {
                        "id": f"test-{msg_id}",
                        "category": category,
                        "evidence": [{"content": f"Detected {category}"}],
                        "matched_patterns": [{"pattern": category, "match_count": 1}],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {"total_findings": 1},
                "analysis_metadata": {
                    "ruleset_used": "local/personal_data_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )

    def test_multiple_input_messages_of_same_schema_type_are_merged(self) -> None:
        """Findings from separate input messages are all present in the output."""
        msg1 = self._make_pd_message("msg1", "email", "user.php")
        msg2 = self._make_pd_message("msg2", "phone", "contact.php")

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg1, msg2], Schema("security_evidence", "1.0.0"))

        findings = result.content["findings"]
        source_locations = {f["metadata"]["source"] for f in findings}
        assert "user.php" in source_locations
        assert "contact.php" in source_locations


# =============================================================================
# Output message structure
# =============================================================================


class TestOutputMessageStructure:
    """Tests for the shape and schema compliance of the output message."""

    def test_process_returns_valid_output_message_structure(self) -> None:
        """process() returns a Message with the correct schema and required content keys."""
        msg = Message(
            id="test_struct",
            content={
                "findings": [
                    {
                        "id": "test-email",
                        "category": "email",
                        "evidence": [{"content": "email@example.com"}],
                        "matched_patterns": [{"pattern": "email", "match_count": 1}],
                        "metadata": {"source": "user.php"},
                    }
                ],
                "summary": {"total_findings": 1},
                "analysis_metadata": {
                    "ruleset_used": "local/personal_data_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )
        output_schema = Schema("security_evidence", "1.0.0")

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)
        assert result.content["summary"]["total_findings"] == len(
            result.content["findings"]
        )
        assert "domains_identified" in result.content["summary"]
        assert "domains" in result.content["summary"]


# =============================================================================
# Summary domain breakdown
# =============================================================================


class TestSummaryDomainBreakdown:
    """Tests for the domain breakdown in SecurityEvidenceSummary."""

    def _make_cq_message(
        self, algorithm: str, quality_rating: str, polarity: str, source: str
    ) -> Message:
        """Build a crypto_quality_indicator message with a single finding."""
        return Message(
            id=f"test_{algorithm}",
            content={
                "findings": [
                    {
                        "id": f"test-{algorithm}",
                        "algorithm": algorithm,
                        "quality_rating": quality_rating,
                        "polarity": polarity,
                        "evidence": [{"content": f"Found {algorithm}"}],
                        "matched_patterns": [{"pattern": algorithm, "match_count": 1}],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {"total_findings": 1},
                "analysis_metadata": {
                    "ruleset_used": "local/crypto_quality_indicator/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("crypto_quality_indicator", "1.0.0"),
        )

    def test_summary_domain_breakdown_counts_findings_per_domain(self) -> None:
        """summary.domains has one entry per unique domain with correct findings_count."""
        # Two findings both in the encryption domain (sha256 + bcrypt, same domain)
        msg1 = self._make_cq_message("sha256", "strong", "positive", "file_a.php")
        msg2 = self._make_cq_message("bcrypt", "strong", "positive", "file_b.php")

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg1, msg2], Schema("security_evidence", "1.0.0"))

        summary = result.content["summary"]
        assert summary["domains_identified"] == 1
        assert len(summary["domains"]) == 1
        assert summary["domains"][0]["security_domain"] == "encryption"
        assert summary["domains"][0]["findings_count"] == 2

    def test_summary_domains_sorted_descending_by_findings_count(self) -> None:
        """summary.domains is ordered with the highest findings_count first."""
        # user_identity_login appears in two files → authentication: 2
        # audit_logging appears in one file → logging_monitoring: 1
        msg = Message(
            id="test_sort",
            content={
                "findings": [
                    {
                        "id": "login-1",
                        "purpose": "user_identity_login",
                        "evidence": [{"content": "login"}],
                        "matched_patterns": [
                            {"pattern": "user_identity_login", "match_count": 1}
                        ],
                        "metadata": {"source": "auth1.php"},
                    },
                    {
                        "id": "login-2",
                        "purpose": "user_identity_login",
                        "evidence": [{"content": "login"}],
                        "matched_patterns": [
                            {"pattern": "user_identity_login", "match_count": 1}
                        ],
                        "metadata": {"source": "auth2.php"},
                    },
                    {
                        "id": "audit-1",
                        "purpose": "audit_logging",
                        "evidence": [{"content": "audit"}],
                        "matched_patterns": [
                            {"pattern": "audit_logging", "match_count": 1}
                        ],
                        "metadata": {"source": "logger.php"},
                    },
                ],
                "summary": {
                    "total_findings": 3,
                    "purposes_identified": 2,
                    "purposes": [
                        {"purpose": "user_identity_login", "findings_count": 2},
                        {"purpose": "audit_logging", "findings_count": 1},
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/processing_purposes/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("processing_purpose_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        result = analyser.process([msg], Schema("security_evidence", "1.0.0"))
        domains = result.content["summary"]["domains"]

        # authentication (2 findings) must come before logging_monitoring (1 finding)
        assert domains[0]["security_domain"] == "authentication"
        assert domains[0]["findings_count"] == 2
        assert domains[1]["security_domain"] == "logging_monitoring"
        assert domains[1]["findings_count"] == 1


# =============================================================================
# Service integration indicator → security evidence mapping
# =============================================================================


class TestNormaliseServiceIntegration:
    """Tests for service_integration_indicator → security evidence normalisation."""

    @pytest.fixture
    def valid_config(self) -> SecurityEvidenceNormaliserConfig:
        """Return default configuration using local domain mapping ruleset."""
        return SecurityEvidenceNormaliserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def _make_message(
        self,
        service_category: str,
        purpose_category: str,
        source: str,
    ) -> Message:
        """Build a service_integration_indicator message with a single finding."""
        return Message(
            id="test_si",
            content={
                "findings": [
                    {
                        "id": f"test-{service_category}",
                        "service_category": service_category,
                        "purpose_category": purpose_category,
                        "evidence": [
                            {"content": f"Detected {service_category} in {source}"}
                        ],
                        "matched_patterns": [
                            {"pattern": service_category, "match_count": 1}
                        ],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {
                    "total_findings": 1,
                    "categories_identified": 1,
                    "categories": [
                        {
                            "service_category": service_category,
                            "findings_count": 1,
                        }
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/service_integrations/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("service_integration_indicator", "1.0.0"),
        )

    def test_service_integration_category_maps_to_expected_security_domain(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A known category (cloud_infrastructure) maps to supplier_management with neutral polarity."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("cloud_infrastructure", "operational", "aws.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "supplier_management"
        assert findings[0]["polarity"] == "neutral"
        assert findings[0]["evidence_type"] == "CODE"

    def test_service_integration_findings_with_same_category_and_source_are_grouped(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """Multiple findings sharing service_category+source produce a single grouped evidence item."""
        finding: dict[str, object] = {
            "id": "test-cloud-1",
            "service_category": "cloud_infrastructure",
            "purpose_category": "operational",
            "evidence": [{"content": "AWS SDK usage"}],
            "matched_patterns": [{"pattern": "cloud_infrastructure", "match_count": 1}],
            "metadata": {"source": "aws.php"},
        }
        msg = Message(
            id="test_si_grouped",
            content={
                "findings": [finding, {**finding, "id": "test-cloud-2"}],
                "summary": {
                    "total_findings": 2,
                    "categories_identified": 1,
                    "categories": [
                        {
                            "service_category": "cloud_infrastructure",
                            "findings_count": 2,
                        }
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/service_integrations/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("service_integration_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(valid_config)
        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert "2 occurrence(s)" in findings[0]["description"]

    def test_unknown_service_integration_category_is_skipped_silently(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unmapped service category is skipped and a debug message is logged."""
        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        msg = self._make_message("unknown_service_xyz", "operational", "file.php")

        with caplog.at_level(logging.DEBUG):
            result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        assert result.content["findings"] == []
        assert "unknown_service_xyz" in caplog.text

    def test_service_integration_identity_management_produces_secondary_domain(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """identity_management produces evidence for both supplier_management and authentication."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("identity_management", "operational", "auth.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        domains = {f["security_domain"] for f in findings}
        assert len(findings) == 2
        assert "supplier_management" in domains
        assert "authentication" in domains


# =============================================================================
# Data collection indicator → security evidence mapping
# =============================================================================


class TestNormaliseDataCollection:
    """Tests for data_collection_indicator → security evidence normalisation."""

    @pytest.fixture
    def valid_config(self) -> SecurityEvidenceNormaliserConfig:
        """Return default configuration using local domain mapping ruleset."""
        return SecurityEvidenceNormaliserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def _make_message(
        self,
        collection_type: str,
        data_source: str,
        source: str,
    ) -> Message:
        """Build a data_collection_indicator message with a single finding."""
        return Message(
            id="test_dc",
            content={
                "findings": [
                    {
                        "id": f"test-{collection_type}",
                        "collection_type": collection_type,
                        "data_source": data_source,
                        "evidence": [
                            {"content": f"Detected {collection_type} in {source}"}
                        ],
                        "matched_patterns": [
                            {"pattern": collection_type, "match_count": 1}
                        ],
                        "metadata": {"source": source},
                    }
                ],
                "summary": {
                    "total_findings": 1,
                    "categories_identified": 1,
                    "categories": [
                        {
                            "collection_type": collection_type,
                            "findings_count": 1,
                        }
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/data_collection/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("data_collection_indicator", "1.0.0"),
        )

    def test_data_collection_type_maps_to_expected_security_domain(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """A known collection type (form_data) maps to data_protection with neutral polarity."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("form_data", "http_post", "contact.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "data_protection"
        assert findings[0]["polarity"] == "neutral"
        assert findings[0]["evidence_type"] == "CODE"

    def test_data_collection_findings_with_same_type_and_source_are_grouped(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """Multiple findings sharing collection_type+source produce a single grouped evidence item."""
        finding: dict[str, object] = {
            "id": "test-form-1",
            "collection_type": "form_data",
            "data_source": "http_post",
            "evidence": [{"content": "$_POST usage"}],
            "matched_patterns": [{"pattern": "form_data", "match_count": 1}],
            "metadata": {"source": "contact.php"},
        }
        msg = Message(
            id="test_dc_grouped",
            content={
                "findings": [finding, {**finding, "id": "test-form-2"}],
                "summary": {
                    "total_findings": 2,
                    "categories_identified": 1,
                    "categories": [
                        {"collection_type": "form_data", "findings_count": 2}
                    ],
                },
                "analysis_metadata": {
                    "ruleset_used": "local/data_collection/1.0.0",
                    "llm_validation_enabled": False,
                },
            },
            schema=Schema("data_collection_indicator", "1.0.0"),
        )

        analyser = SecurityEvidenceNormaliser(valid_config)
        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert "2 occurrence(s)" in findings[0]["description"]

    def test_unknown_data_collection_type_is_skipped_silently(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An unmapped collection type is skipped and a debug message is logged."""
        analyser = SecurityEvidenceNormaliser(SecurityEvidenceNormaliserConfig())
        msg = self._make_message("unknown_type_xyz", "unknown", "file.php")

        with caplog.at_level(logging.DEBUG):
            result = analyser.process([msg], Schema("security_evidence", "1.0.0"))

        assert result.content["findings"] == []
        assert "unknown_type_xyz" in caplog.text

    def test_file_upload_collection_maps_to_vulnerability_management(
        self,
        valid_config: SecurityEvidenceNormaliserConfig,
        output_schema: Schema,
    ) -> None:
        """file_upload maps to vulnerability_management, not data_protection."""
        analyser = SecurityEvidenceNormaliser(valid_config)
        msg = self._make_message("file_upload", "uploaded_files", "upload.php")

        result = analyser.process([msg], output_schema)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["security_domain"] == "vulnerability_management"
