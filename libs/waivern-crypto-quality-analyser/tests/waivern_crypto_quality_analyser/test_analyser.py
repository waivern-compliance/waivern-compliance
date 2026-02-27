"""Unit tests for CryptoQualityAnalyser.

Tests are grouped by concern:
  B - Polarity and algorithm field derivation
  C - Output message structure
  D - Fan-in (multiple input messages)
"""

import pytest
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_crypto_quality_analyser.analyser import CryptoQualityAnalyser
from waivern_crypto_quality_analyser.types import CryptoQualityAnalyserConfig


class TestCryptoQualityAnalyserContract(AnalyserContractTests[CryptoQualityAnalyser]):
    """Contract tests for CryptoQualityAnalyser.

    Inherits from AnalyserContractTests to verify that CryptoQualityAnalyser
    meets the Analyser interface contract.
    """

    @pytest.fixture
    def processor_class(self) -> type[CryptoQualityAnalyser]:
        """Provide the processor class for contract testing."""
        return CryptoQualityAnalyser


class TestCryptoQualityAnalyser:
    """Behavioural tests for CryptoQualityAnalyser."""

    @pytest.fixture
    def valid_config(self) -> CryptoQualityAnalyserConfig:
        """Return default configuration using local crypto_quality_indicator ruleset."""
        return CryptoQualityAnalyserConfig()

    @pytest.fixture
    def deprecated_input_message(self) -> Message:
        """Input message containing a deprecated algorithm reference."""
        return Message(
            id="test_deprecated",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "password_hash = md5(password)",
                        "metadata": {
                            "source": "auth.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

    @pytest.fixture
    def strong_input_message(self) -> Message:
        """Input message containing a strong algorithm reference."""
        return Message(
            id="test_strong",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "hashed = bcrypt.hashpw(password, bcrypt.gensalt())",
                        "metadata": {
                            "source": "auth.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

    @pytest.fixture
    def weak_input_message(self) -> Message:
        """Input message containing a weak algorithm reference."""
        return Message(
            id="test_weak",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "cipher = blowfish.new(key)",
                        "metadata": {
                            "source": "crypto.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for crypto_quality_indicator."""
        return Schema("crypto_quality_indicator", "1.0.0")

    # ─── Group B: Polarity and algorithm field derivation ────────────────────

    def test_deprecated_algorithm_produces_negative_polarity(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        deprecated_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """A deprecated algorithm (md5) yields polarity=negative."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([deprecated_input_message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        md5_finding = next(f for f in findings if f["algorithm"] == "md5")
        assert md5_finding["polarity"] == "negative"
        assert md5_finding["quality_rating"] == "deprecated"

    def test_strong_algorithm_produces_positive_polarity(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        strong_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """A strong algorithm (bcrypt) yields polarity=positive."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([strong_input_message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        bcrypt_finding = next(f for f in findings if f["algorithm"] == "bcrypt")
        assert bcrypt_finding["polarity"] == "positive"
        assert bcrypt_finding["quality_rating"] == "strong"

    def test_weak_algorithm_produces_negative_polarity(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        weak_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """A weak algorithm (blowfish) yields polarity=negative."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([weak_input_message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        blowfish_finding = next(f for f in findings if f["algorithm"] == "blowfish")
        assert blowfish_finding["polarity"] == "negative"
        assert blowfish_finding["quality_rating"] == "weak"

    def test_algorithm_field_matches_rule_algorithm(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        deprecated_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """Finding.algorithm matches the canonical name from the ruleset."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([deprecated_input_message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        # The ruleset YAML defines algorithm="md5" for the md5 rule;
        # the pattern "md5" in content triggers it.
        assert any(f["algorithm"] == "md5" for f in findings)

    def test_no_crypto_patterns_produces_no_findings(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """Content with no recognised algorithm patterns produces zero findings."""
        analyser = CryptoQualityAnalyser(valid_config)
        message = Message(
            id="test_no_patterns",
            content={
                "schemaVersion": "1.0.0",
                "name": "Clean source",
                "data": [
                    {
                        "content": "x = a + b",
                        "metadata": {
                            "source": "math.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        assert result.content["findings"] == []
        assert result.content["summary"]["total_findings"] == 0

    # ─── Group C: Output message structure ──────────────────────────────────

    def test_process_returns_valid_output_message_structure(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        deprecated_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """process() returns a Message with the correct schema and content keys."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([deprecated_input_message], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_summary_total_findings_matches_findings_count(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        deprecated_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """summary.total_findings equals len(findings)."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process([deprecated_input_message], output_schema)

        findings = result.content["findings"]
        summary = result.content["summary"]
        assert summary["total_findings"] == len(findings)

    # ─── Group D: Fan-in ────────────────────────────────────────────────────

    def test_process_merges_findings_from_multiple_inputs(
        self,
        valid_config: CryptoQualityAnalyserConfig,
        deprecated_input_message: Message,
        strong_input_message: Message,
        output_schema: Schema,
    ) -> None:
        """Findings from multiple input messages are all present in the output."""
        analyser = CryptoQualityAnalyser(valid_config)
        result = analyser.process(
            [deprecated_input_message, strong_input_message], output_schema
        )

        findings = result.content["findings"]
        algorithms = {f["algorithm"] for f in findings}
        assert "md5" in algorithms, (
            "Findings from deprecated_input_message should be present"
        )
        assert "bcrypt" in algorithms, (
            "Findings from strong_input_message should be present"
        )
