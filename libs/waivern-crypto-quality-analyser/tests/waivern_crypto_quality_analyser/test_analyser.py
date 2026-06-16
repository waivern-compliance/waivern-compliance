"""Unit tests for CryptoQualityAnalyser.

Uses synthetic rules via monkeypatched RulesetManager to decouple from
production ruleset data.
"""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRule

from waivern_crypto_quality_analyser.analyser import CryptoQualityAnalyser
from waivern_crypto_quality_analyser.types import CryptoQualityAnalyserConfig

# =============================================================================
# Synthetic rules
# =============================================================================

RULE_STRONG = CryptoQualityIndicatorRule(
    name="Test Strong Algo",
    description="Strong algorithm detection",
    category="strong_algo",
    algorithm="test_strong",
    quality_rating="strong",
    patterns=("test_strong_pattern",),
)

RULE_WEAK = CryptoQualityIndicatorRule(
    name="Test Weak Algo",
    description="Weak algorithm detection",
    category="weak_algo",
    algorithm="test_weak",
    quality_rating="weak",
    patterns=("test_weak_pattern",),
)

RULE_DEPRECATED = CryptoQualityIndicatorRule(
    name="Test Deprecated Algo",
    description="Deprecated algorithm detection",
    category="deprecated_algo",
    algorithm="test_deprecated",
    quality_rating="deprecated",
    patterns=("test_deprecated_pattern",),
)

SYNTHETIC_RULES = (RULE_STRONG, RULE_WEAK, RULE_DEPRECATED)

_UNUSED_RULESET_URI = "unused/test/1.0.0"


def _mock_get_rules(
    uri: str, rule_type: type[CryptoQualityIndicatorRule]
) -> tuple[CryptoQualityIndicatorRule, ...]:
    return SYNTHETIC_RULES


# =============================================================================
# Helpers
# =============================================================================

OUTPUT_SCHEMA = Schema("crypto_quality_indicator", "1.0.0")
INPUT_SCHEMA = Schema("standard_input", "1.0.0")


def _make_config() -> CryptoQualityAnalyserConfig:
    """Build a CryptoQualityAnalyserConfig with synthetic ruleset URI."""
    return CryptoQualityAnalyserConfig(
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
                        "source": "test.txt",
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


class TestCryptoQualityAnalyserContract(AnalyserContractTests[CryptoQualityAnalyser]):
    """Contract tests for CryptoQualityAnalyser."""

    @pytest.fixture
    def processor_class(self) -> type[CryptoQualityAnalyser]:
        """Provide the processor class for contract testing."""
        return CryptoQualityAnalyser


# =============================================================================
# Polarity and algorithm field derivation
# =============================================================================


class TestCryptoQualityPolarity:
    """Tests for polarity assignment based on quality_rating."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_deprecated_algorithm_produces_negative_polarity(self) -> None:
        """A deprecated algorithm yields polarity=negative."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("Using test_deprecated_pattern for hashing")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["algorithm"] == "test_deprecated"
        assert findings[0]["polarity"] == "negative"
        assert findings[0]["quality_rating"] == "deprecated"

    def test_strong_algorithm_produces_positive_polarity(self) -> None:
        """A strong algorithm yields polarity=positive."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("Using test_strong_pattern for hashing")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["algorithm"] == "test_strong"
        assert findings[0]["polarity"] == "positive"
        assert findings[0]["quality_rating"] == "strong"

    def test_weak_algorithm_produces_negative_polarity(self) -> None:
        """A weak algorithm yields polarity=negative."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("Using test_weak_pattern for encryption")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        assert len(findings) == 1
        assert findings[0]["algorithm"] == "test_weak"
        assert findings[0]["polarity"] == "negative"
        assert findings[0]["quality_rating"] == "weak"

    def test_no_crypto_patterns_produces_no_findings(self) -> None:
        """Content with no recognised algorithm patterns produces zero findings."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("x = a + b")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0


# =============================================================================
# Output message structure
# =============================================================================


class TestCryptoQualityOutputStructure:
    """Tests for the shape and schema compliance of the output message."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_process_returns_valid_output_message_structure(self) -> None:
        """process() returns a Message with the correct schema and content keys."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("Using test_strong_pattern for hashing")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        assert isinstance(result, Message)
        assert result.schema == OUTPUT_SCHEMA
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_summary_total_findings_matches_findings_count(self) -> None:
        """summary.total_findings equals len(findings)."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        message = _make_message("Using test_strong_pattern for hashing")

        result, _ = analyser.process([message], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        summary = result.content["summary"]
        assert summary["total_findings"] == len(findings)


# =============================================================================
# Fan-in (multiple input messages)
# =============================================================================


class TestCryptoQualityFanIn:
    """Tests for fan-in: multiple input messages produce merged findings."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_process_merges_findings_from_multiple_inputs(self) -> None:
        """Findings from multiple input messages are all present in the output."""
        analyser = CryptoQualityAnalyser(config=_make_config())
        msg_deprecated = _make_message("Using test_deprecated_pattern for hashing")
        msg_strong = _make_message("Using test_strong_pattern for encryption")

        result, _ = analyser.process([msg_deprecated, msg_strong], OUTPUT_SCHEMA)

        findings = result.content["findings"]
        algorithms = {f["algorithm"] for f in findings}
        assert "test_deprecated" in algorithms
        assert "test_strong" in algorithms
