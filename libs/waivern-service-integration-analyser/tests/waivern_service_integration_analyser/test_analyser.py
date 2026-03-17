"""Tests for ServiceIntegrationAnalyser."""

import pytest
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.services import ServiceContainer
from waivern_rulesets.service_integrations import ServiceIntegrationRule
from waivern_source_code_analyser.schemas.source_code import SourceCodeDataModel

from waivern_service_integration_analyser.analyser import ServiceIntegrationAnalyser
from waivern_service_integration_analyser.factory import (
    ServiceIntegrationAnalyserFactory,
)
from waivern_service_integration_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)
from waivern_service_integration_analyser.types import (
    ServiceIntegrationAnalyserConfig,
)

# =============================================================================
# Contract tests
# =============================================================================


class TestServiceIntegrationAnalyserContract(
    AnalyserContractTests[ServiceIntegrationAnalyser]
):
    """Contract tests for ServiceIntegrationAnalyser."""

    @pytest.fixture
    def processor_class(self) -> type[ServiceIntegrationAnalyser]:
        """Provide the processor class for contract testing."""
        return ServiceIntegrationAnalyser


# =============================================================================
# Synthetic rules for detection tests
# =============================================================================

RULE_PAYMENTS = ServiceIntegrationRule(
    name="Payment Processors",
    description="Payment processing services",
    patterns=("pay_gateway", "checkout_sdk"),
    service_category="payment_processing",
    purpose_category="operational",
)

RULE_ANALYTICS = ServiceIntegrationRule(
    name="Analytics Trackers",
    description="User analytics services",
    patterns=("track_event", "analytics_sdk"),
    service_category="user_analytics",
    purpose_category="analytics",
)

# Shares (communication, operational) with RULE_MESSAGING — tests composite key merging
RULE_EMAIL = ServiceIntegrationRule(
    name="Email Services",
    description="Email delivery services",
    patterns=("send_email",),
    service_category="communication",
    purpose_category="operational",
)

RULE_MESSAGING = ServiceIntegrationRule(
    name="Messaging Platforms",
    description="Messaging platform integrations",
    patterns=("send_sms",),
    service_category="communication",
    purpose_category="operational",
)

SYNTHETIC_RULES = (RULE_PAYMENTS, RULE_ANALYTICS, RULE_EMAIL, RULE_MESSAGING)


def _make_source_code_data(file_path: str, raw_content: str) -> SourceCodeDataModel:
    """Build a minimal SourceCodeDataModel for testing."""
    return SourceCodeDataModel(
        schemaVersion="1.0.0",
        name="Test",
        description="Test",
        source="test_repo",
        metadata={
            "total_files": 1,
            "total_lines": raw_content.count("\n") + 1,
            "analysis_timestamp": "2025-01-01T00:00:00Z",
        },
        data=[
            {
                "file_path": file_path,
                "language": "php",
                "raw_content": raw_content,
                "metadata": {
                    "file_size": len(raw_content),
                    "line_count": raw_content.count("\n") + 1,
                    "last_modified": None,
                },
            }
        ],
    )


# =============================================================================
# Detection and grouping
# =============================================================================


class TestServiceIntegrationDetection:
    """Tests for pattern matching, field population, and grouping logic.

    Uses synthetic rules injected into the handler to decouple from
    production ruleset data. This tests the handler's behaviour (grouping,
    merging, evidence extraction) independently of any specific ruleset.
    """

    @pytest.fixture
    def handler(self) -> SourceCodeSchemaInputHandler:
        return SourceCodeSchemaInputHandler(
            rules=SYNTHETIC_RULES,
            context_window="small",
        )

    def test_detects_service_integration_patterns(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Source code with known patterns produces findings with correct service_category and purpose_category."""
        data = _make_source_code_data(
            "billing/checkout.php",
            "result = pay_gateway(amount)",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        assert findings[0].service_category == "payment_processing"
        assert findings[0].purpose_category == "operational"

    def test_multiple_categories_produce_separate_findings(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Patterns from different categories produce distinct findings."""
        data = _make_source_code_data(
            "app/main.php",
            "pay_gateway(100)\ntrack_event('click')",
        )

        findings = handler.analyse(data)

        categories = {f.service_category for f in findings}
        assert categories == {"payment_processing", "user_analytics"}

    def test_same_composite_key_merges_into_single_finding(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Rules sharing (service_category, purpose_category) merge into one finding per file."""
        # RULE_EMAIL and RULE_MESSAGING both have (communication, operational)
        data = _make_source_code_data(
            "comms/notify.php",
            "send_email(to, body)\nsend_sms(phone, text)",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        assert findings[0].service_category == "communication"
        assert findings[0].purpose_category == "operational"

    def test_merged_finding_aggregates_patterns_from_all_rules(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Merged finding's matched_patterns contains patterns from all contributing rules."""
        data = _make_source_code_data(
            "comms/notify.php",
            "send_email(to, body)\nsend_sms(phone, text)",
        )

        findings = handler.analyse(data)

        patterns = {p.pattern for p in findings[0].matched_patterns}
        assert patterns == {"send_email", "send_sms"}

    def test_no_matching_patterns_produces_empty_findings(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Clean code produces zero findings."""
        data = _make_source_code_data(
            "utils/math.php",
            "x = a + b",
        )

        findings = handler.analyse(data)

        assert findings == []

    def test_finding_includes_evidence_with_context(
        self, handler: SourceCodeSchemaInputHandler
    ) -> None:
        """Finding evidence contains source code context around the match."""
        data = _make_source_code_data(
            "billing/charge.php",
            "line1\nline2\npay_gateway(100)\nline4\nline5",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        evidence_content = findings[0].evidence[0].content
        # Context window "small" = ±3 lines, so all 5 lines should be included
        assert "pay_gateway" in evidence_content
        # Line numbers are included in evidence
        assert "3" in evidence_content


# =============================================================================
# Output structure
# =============================================================================


class TestServiceIntegrationOutputStructure:
    """Tests for output message shape and validation."""

    @pytest.fixture
    def config(self) -> ServiceIntegrationAnalyserConfig:
        return ServiceIntegrationAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        return Schema("service_integration_indicator", "1.0.0")

    def test_output_message_has_valid_schema(self, config, output_schema) -> None:
        """process() returns a Message with service_integration_indicator/1.0.0 schema and required keys."""
        analyser = ServiceIntegrationAnalyser(config)
        message = Message(
            id="test_structure",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test App",
                "description": "Test",
                "source": "test_repo",
                "metadata": {
                    "total_files": 1,
                    "total_lines": 1,
                    "analysis_timestamp": "2025-01-01T00:00:00Z",
                },
                "data": [
                    {
                        "file_path": "app.php",
                        "language": "php",
                        "raw_content": "stripe_charge($amount)",
                        "metadata": {
                            "file_size": 50,
                            "line_count": 1,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_summary_counts_categories_correctly(self, config, output_schema) -> None:
        """Summary total_findings, categories_identified, and per-category breakdown match actual findings."""
        analyser = ServiceIntegrationAnalyser(config)
        # stripe → payment_processing; mixpanel → user_analytics
        message = Message(
            id="test_summary",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test App",
                "description": "Test",
                "source": "test_repo",
                "metadata": {
                    "total_files": 1,
                    "total_lines": 2,
                    "analysis_timestamp": "2025-01-01T00:00:00Z",
                },
                "data": [
                    {
                        "file_path": "app.php",
                        "language": "php",
                        "raw_content": "stripe_charge($amount)\nmixpanel_track($event)",
                        "metadata": {
                            "file_size": 100,
                            "line_count": 2,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        summary = result.content["summary"]
        category_names = {c["service_category"] for c in summary["categories"]}
        assert "payment_processing" in category_names
        assert "user_analytics" in category_names
        assert summary["categories_identified"] == len(summary["categories"])


# =============================================================================
# Source code input
# =============================================================================


class TestServiceIntegrationSourceCodeInput:
    """Tests for source code schema input handling."""

    @pytest.fixture
    def config(self) -> ServiceIntegrationAnalyserConfig:
        return ServiceIntegrationAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        return Schema("service_integration_indicator", "1.0.0")

    def test_accepts_source_code_schema_input(self, config, output_schema) -> None:
        """A source_code/1.0.0 input message is processed and findings carry correct metadata.source."""
        analyser = ServiceIntegrationAnalyser(config)
        message = Message(
            id="test_source_code",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test App",
                "description": "Test",
                "source": "test_repo",
                "metadata": {
                    "total_files": 1,
                    "total_lines": 1,
                    "analysis_timestamp": "2025-01-01T00:00:00Z",
                },
                "data": [
                    {
                        "file_path": "auth/login.php",
                        "language": "php",
                        "raw_content": "auth0_login($user)",
                        "metadata": {
                            "file_size": 50,
                            "line_count": 1,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        findings = result.content["findings"]
        assert len(findings) >= 1
        assert findings[0]["metadata"]["source"] == "auth/login.php"

    def test_fan_in_merges_multiple_source_code_messages(
        self, config, output_schema
    ) -> None:
        """Two source_code messages produce findings from both."""
        analyser = ServiceIntegrationAnalyser(config)
        message_a = Message(
            id="test_fan_in_a",
            content={
                "schemaVersion": "1.0.0",
                "name": "Repo A",
                "description": "Test",
                "source": "repo_a",
                "metadata": {
                    "total_files": 1,
                    "total_lines": 1,
                    "analysis_timestamp": "2025-01-01T00:00:00Z",
                },
                "data": [
                    {
                        "file_path": "a/billing.php",
                        "language": "php",
                        "raw_content": "stripe_charge($amount)",
                        "metadata": {
                            "file_size": 50,
                            "line_count": 1,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )
        message_b = Message(
            id="test_fan_in_b",
            content={
                "schemaVersion": "1.0.0",
                "name": "Repo B",
                "description": "Test",
                "source": "repo_b",
                "metadata": {
                    "total_files": 1,
                    "total_lines": 1,
                    "analysis_timestamp": "2025-01-01T00:00:00Z",
                },
                "data": [
                    {
                        "file_path": "b/track.php",
                        "language": "php",
                        "raw_content": "mixpanel_track($event)",
                        "metadata": {
                            "file_size": 50,
                            "line_count": 1,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )

        result = analyser.process([message_a, message_b], output_schema)

        sources = {f["metadata"]["source"] for f in result.content["findings"]}
        assert "a/billing.php" in sources
        assert "b/track.php" in sources


# =============================================================================
# Factory
# =============================================================================


class TestServiceIntegrationFactory:
    """Tests for factory validation."""

    def test_factory_creates_analyser_with_valid_config(self) -> None:
        """Factory creates an analyser that can process input."""
        container = ServiceContainer()
        factory = ServiceIntegrationAnalyserFactory(container)
        properties = {}
        assert factory.can_create(properties) is True

        analyser = factory.create(properties)
        assert isinstance(analyser, ServiceIntegrationAnalyser)

    def test_factory_rejects_invalid_ruleset(self) -> None:
        """can_create returns False for a non-existent ruleset."""
        container = ServiceContainer()
        factory = ServiceIntegrationAnalyserFactory(container)
        properties = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
        }
        assert factory.can_create(properties) is False
