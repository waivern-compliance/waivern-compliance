"""Unit tests for SecurityControlAnalyser.

Uses synthetic rules via monkeypatched RulesetManager to decouple from
production ruleset data.
"""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_rulesets.security_control_indicator import SecurityControlIndicatorRule
from waivern_schemas.security_domain import SecurityDomain

from waivern_security_control_analyser.analyser import SecurityControlAnalyser
from waivern_security_control_analyser.types import SecurityControlAnalyserConfig

# =============================================================================
# Synthetic rules
# =============================================================================

RULE_POSITIVE = SecurityControlIndicatorRule(
    name="Test Positive Auth",
    description="Positive authentication control detection",
    category="positive_auth",
    security_domain=SecurityDomain.AUTHENTICATION,
    polarity="positive",
    patterns=("test_positive_auth_pattern",),
)

RULE_NEGATIVE = SecurityControlIndicatorRule(
    name="Test Negative Network",
    description="Negative network security control detection",
    category="negative_network",
    security_domain=SecurityDomain.NETWORK_SECURITY,
    polarity="negative",
    patterns=("test_negative_network_pattern",),
)

SYNTHETIC_RULES = (RULE_POSITIVE, RULE_NEGATIVE)

_UNUSED_RULESET_URI = "unused/test/1.0.0"


def _mock_get_rules(
    uri: str, rule_type: type[SecurityControlIndicatorRule]
) -> tuple[SecurityControlIndicatorRule, ...]:
    return SYNTHETIC_RULES


# =============================================================================
# Helpers
# =============================================================================

OUTPUT_SCHEMA = Schema("security_evidence", "1.0.0")
INPUT_SCHEMA = Schema("standard_input", "1.0.0")


def _make_config() -> SecurityControlAnalyserConfig:
    """Build a SecurityControlAnalyserConfig with synthetic ruleset URI."""
    return SecurityControlAnalyserConfig(
        pattern_matching=PatternMatchingConfig(ruleset=_UNUSED_RULESET_URI),
    )


def _make_message(content: str) -> Message:
    """Build a standard_input message carrying a single data item."""
    return Message(
        id="test-message",
        content={
            "schemaVersion": "1.0.0",
            "name": "Test source",
            "data": [
                {
                    "content": content,
                    "metadata": {
                        "source": "test.php",
                        "connector_type": "test",
                    },
                }
            ],
        },
        schema=INPUT_SCHEMA,
    )


# =============================================================================
# Contract tests
# =============================================================================


class TestSecurityControlAnalyserContract(
    AnalyserContractTests[SecurityControlAnalyser]
):
    """Contract tests for SecurityControlAnalyser."""

    @pytest.fixture
    def processor_class(self) -> type[SecurityControlAnalyser]:
        """Provide the processor class for contract testing."""
        return SecurityControlAnalyser


# =============================================================================
# Polarity and security domain field derivation
# =============================================================================


class TestSecurityControlPolarity:
    """Tests for polarity and security_domain assignment."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_positive_pattern_produces_positive_polarity(self) -> None:
        """A positive-polarity rule match yields polarity=positive in the finding."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = _make_message("Using test_positive_auth_pattern for login")

        result = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["polarity"] == "positive"
        assert findings[0]["security_domain"] == "authentication"

    def test_negative_pattern_produces_negative_polarity(self) -> None:
        """A negative-polarity rule match yields polarity=negative in the finding."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = _make_message("Using test_negative_network_pattern in firewall")

        result = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["polarity"] == "negative"
        assert findings[0]["security_domain"] == "network_security"

    def test_no_matching_patterns_produces_no_findings(self) -> None:
        """Content with no recognised patterns produces zero findings."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = _make_message("x = a + b")

        result = analyser.process([message], OUTPUT_SCHEMA)

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0


# =============================================================================
# Output message structure
# =============================================================================


class TestSecurityControlOutputStructure:
    """Tests for the shape and schema compliance of the output message."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_process_returns_valid_security_evidence_message(self) -> None:
        """process() returns a Message with security_evidence/1.0.0 schema and required keys."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = _make_message("Using test_positive_auth_pattern for login")

        result = analyser.process([message], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        assert result.schema == OUTPUT_SCHEMA
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_summary_counts_domains_correctly(self) -> None:
        """summary.domains reflects the actual security domains found."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = _make_message(
            "test_positive_auth_pattern and test_negative_network_pattern"
        )

        result = analyser.process([message], OUTPUT_SCHEMA)

        summary = result.content["summary"]
        domain_names = {d["security_domain"] for d in summary["domains"]}
        assert "authentication" in domain_names
        assert "network_security" in domain_names
        assert summary["domains_identified"] == len(summary["domains"])


# =============================================================================
# Input schema support
# =============================================================================


class TestSecurityControlInputSchemas:
    """Tests for different input schema types."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_accepts_source_code_schema_input(self) -> None:
        """A source_code/1.0.0 input message is processed successfully."""
        analyser = SecurityControlAnalyser(config=_make_config())
        message = Message(
            id="test_source_code",
            content={
                "schemaVersion": "1.0.0",
                "name": "My App",
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
                        "raw_content": "test_positive_auth_pattern here",
                        "metadata": {
                            "file_size": 100,
                            "line_count": 1,
                            "last_modified": None,
                        },
                    }
                ],
            },
            schema=Schema("source_code", "1.0.0"),
        )

        result = analyser.process([message], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        assert result.schema == OUTPUT_SCHEMA
        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["metadata"]["source"] == "auth/login.php"


# =============================================================================
# Fan-in (multiple input messages)
# =============================================================================


class TestSecurityControlFanIn:
    """Tests for fan-in: multiple input messages produce merged findings."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_process_merges_findings_from_multiple_inputs(self) -> None:
        """Findings from multiple input messages are all present in the output."""
        analyser = SecurityControlAnalyser(config=_make_config())
        msg_positive = _make_message("Using test_positive_auth_pattern for login")
        msg_negative = _make_message("Using test_negative_network_pattern in firewall")

        result = analyser.process([msg_positive, msg_negative], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        polarities = {f["polarity"] for f in findings}
        assert "positive" in polarities
        assert "negative" in polarities
