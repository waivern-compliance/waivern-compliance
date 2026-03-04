"""Unit tests for SecurityControlAnalyser."""

import pytest
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema

from waivern_security_control_analyser.analyser import SecurityControlAnalyser
from waivern_security_control_analyser.types import SecurityControlAnalyserConfig

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

    @pytest.fixture
    def valid_config(self) -> SecurityControlAnalyserConfig:
        """Return default configuration using local security_control_indicator ruleset."""
        return SecurityControlAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def test_positive_pattern_produces_positive_polarity(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """A positive-polarity rule match yields polarity=positive in the finding."""
        analyser = SecurityControlAnalyser(valid_config)
        message = Message(
            id="test_positive",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "db.prepared_statement($query, [$id])",
                        "metadata": {
                            "source": "db.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        assert any(f["polarity"] == "positive" for f in findings)

    def test_negative_pattern_produces_negative_polarity(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """A negative-polarity rule match yields polarity=negative in the finding."""
        analyser = SecurityControlAnalyser(valid_config)
        message = Message(
            id="test_negative",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "shell_exec($user_command)",
                        "metadata": {
                            "source": "exec.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        assert any(f["polarity"] == "negative" for f in findings)

    def test_security_domain_taken_from_rule(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """The security_domain in the finding matches the matched rule's domain."""
        analyser = SecurityControlAnalyser(valid_config)
        # audit_log is in the logging_monitoring domain (positive)
        message = Message(
            id="test_domain",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "audit_log($user, $action)",
                        "metadata": {
                            "source": "audit.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        findings = result.content["findings"]
        assert len(findings) >= 1
        assert any(f["security_domain"] == "logging_monitoring" for f in findings)

    def test_no_matching_patterns_produces_no_findings(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """Content with no ruleset patterns produces zero findings."""
        analyser = SecurityControlAnalyser(valid_config)
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


# =============================================================================
# Output message structure
# =============================================================================


class TestSecurityControlOutputStructure:
    """Tests for the shape and schema compliance of the output message."""

    @pytest.fixture
    def valid_config(self) -> SecurityControlAnalyserConfig:
        """Return default configuration using local security_control_indicator ruleset."""
        return SecurityControlAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def test_process_returns_valid_security_evidence_message(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """process() returns a Message with security_evidence/1.0.0 schema and required keys."""
        analyser = SecurityControlAnalyser(valid_config)
        message = Message(
            id="test_structure",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "bcrypt_hash($password)",
                        "metadata": {
                            "source": "auth.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)

    def test_summary_counts_domains_correctly(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """summary.domains reflects the actual security domains found."""
        analyser = SecurityControlAnalyser(valid_config)
        # bcrypt → authentication; audit_log → logging_monitoring
        message = Message(
            id="test_summary",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test source",
                "data": [
                    {
                        "content": "bcrypt_hash($pw); audit_log($user, $action)",
                        "metadata": {
                            "source": "app.php",
                            "connector_type": "filesystem",
                        },
                    }
                ],
            },
            schema=Schema("standard_input", "1.0.0"),
        )

        result = analyser.process([message], output_schema)

        summary = result.content["summary"]
        domain_names = {d["security_domain"] for d in summary["domains"]}
        assert "authentication" in domain_names
        assert "logging_monitoring" in domain_names
        assert summary["domains_identified"] == len(summary["domains"])


# =============================================================================
# Input schema support
# =============================================================================


class TestSecurityControlInputSchemas:
    """Tests for different input schema types."""

    @pytest.fixture
    def valid_config(self) -> SecurityControlAnalyserConfig:
        """Return default configuration using local security_control_indicator ruleset."""
        return SecurityControlAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Return the standard output schema for security_evidence."""
        return Schema("security_evidence", "1.0.0")

    def test_accepts_source_code_schema_input(
        self,
        valid_config: SecurityControlAnalyserConfig,
        output_schema: Schema,
    ) -> None:
        """A source_code/1.0.0 input message is processed successfully."""
        analyser = SecurityControlAnalyser(valid_config)
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
                        "raw_content": "bcrypt_hash($password)",
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

        result = analyser.process([message], output_schema)

        assert isinstance(result, Message)
        assert result.schema == output_schema
        findings = result.content["findings"]
        assert len(findings) >= 1
        assert findings[0]["metadata"]["source"] == "auth/login.php"
