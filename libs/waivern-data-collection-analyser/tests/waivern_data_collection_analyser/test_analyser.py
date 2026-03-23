"""Tests for DataCollectionAnalyser."""

import pytest
from waivern_core import AnalyserContractTests
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.services import ServiceContainer
from waivern_rulesets.data_collection import DataCollectionRule
from waivern_schemas.source_code import SourceCodeDataModel

from waivern_data_collection_analyser.analyser import DataCollectionAnalyser
from waivern_data_collection_analyser.factory import DataCollectionAnalyserFactory
from waivern_data_collection_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)
from waivern_data_collection_analyser.types import DataCollectionAnalyserConfig

# =============================================================================
# Contract tests
# =============================================================================


class TestDataCollectionAnalyserContract(AnalyserContractTests[DataCollectionAnalyser]):
    """Contract tests for DataCollectionAnalyser."""

    @pytest.fixture
    def processor_class(self) -> type[DataCollectionAnalyser]:
        """Provide the processor class for contract testing."""
        return DataCollectionAnalyser


# =============================================================================
# Synthetic rules for detection tests
# =============================================================================

RULE_FORM_POST = DataCollectionRule(
    name="Form POST Data",
    description="Form POST data collection",
    patterns=("post_data(", "form_submit("),
    collection_type="form_data",
    data_source="http_post",
)

RULE_URL_PARAMS = DataCollectionRule(
    name="URL Parameters",
    description="URL parameter collection",
    patterns=("get_param(", "query_string("),
    collection_type="url_parameters",
    data_source="http_get",
)

RULE_COOKIES = DataCollectionRule(
    name="Cookie Access",
    description="Browser cookie access",
    patterns=("read_cookie(",),
    collection_type="cookies",
    data_source="browser_cookies",
)

RULE_SESSION = DataCollectionRule(
    name="Session Data",
    description="Session data access",
    patterns=("read_session(",),
    collection_type="session_data",
    data_source="browser_cookies",
)

# Shares composite key (session_data, browser_cookies) with RULE_SESSION — tests merging
RULE_SESSION_ALT = DataCollectionRule(
    name="Session Data Alt",
    description="Alternative session data access",
    patterns=("session_get(",),
    collection_type="session_data",
    data_source="browser_cookies",
)

SYNTHETIC_RULES = (
    RULE_FORM_POST,
    RULE_URL_PARAMS,
    RULE_COOKIES,
    RULE_SESSION,
    RULE_SESSION_ALT,
)


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


class TestDataCollectionDetection:
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

    def test_detects_data_collection_patterns(self, handler) -> None:
        """Source code with known patterns produces findings with correct collection_type and data_source."""
        data = _make_source_code_data(
            "app/form.php",
            "result = post_data('value')",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        assert findings[0].collection_type == "form_data"
        assert findings[0].data_source == "http_post"

    def test_multiple_categories_produce_separate_findings(self, handler) -> None:
        """Patterns from different categories produce distinct findings."""
        data = _make_source_code_data(
            "app/main.php",
            "post_data('value')\nget_param('id')",
        )

        findings = handler.analyse(data)

        collection_types = {f.collection_type for f in findings}
        assert collection_types == {"form_data", "url_parameters"}

    def test_same_composite_key_merges_into_single_finding(self, handler) -> None:
        """Rules sharing (collection_type, data_source) merge into one finding per file."""
        # RULE_SESSION and RULE_SESSION_ALT both have (session_data, browser_cookies)
        data = _make_source_code_data(
            "app/session.php",
            "read_session('key')\nsession_get('key')",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        assert findings[0].collection_type == "session_data"
        assert findings[0].data_source == "browser_cookies"

    def test_merged_finding_aggregates_patterns_from_all_rules(self, handler) -> None:
        """Merged finding's matched_patterns contains patterns from all contributing rules."""
        data = _make_source_code_data(
            "app/session.php",
            "read_session('key')\nsession_get('key')",
        )

        findings = handler.analyse(data)

        patterns = {p.pattern for p in findings[0].matched_patterns}
        assert patterns == {"read_session(", "session_get("}

    def test_no_matching_patterns_produces_empty_findings(self, handler) -> None:
        """Clean code produces zero findings."""
        data = _make_source_code_data(
            "utils/math.php",
            "x = a + b",
        )

        findings = handler.analyse(data)

        assert findings == []

    def test_finding_includes_evidence_with_context(self, handler) -> None:
        """Finding evidence contains source code context around the match."""
        data = _make_source_code_data(
            "app/form.php",
            "line1\nline2\npost_data('value')\nline4\nline5",
        )

        findings = handler.analyse(data)

        assert len(findings) == 1
        evidence_content = findings[0].evidence[0].content
        # Context window "small" = ±3 lines, so all 5 lines should be included
        assert "post_data" in evidence_content
        # Line numbers are included in evidence
        assert "3" in evidence_content


# =============================================================================
# Output structure
# =============================================================================


class TestDataCollectionOutputStructure:
    """Tests for output message shape and validation."""

    @pytest.fixture
    def config(self) -> DataCollectionAnalyserConfig:
        return DataCollectionAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        return Schema("data_collection_indicator", "1.0.0")

    def test_output_message_has_valid_schema(self, config, output_schema) -> None:
        """process() returns a Message with data_collection_indicator/1.0.0 schema and required keys."""
        analyser = DataCollectionAnalyser(config)
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
                        "raw_content": "$_POST['name']",
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
        analyser = DataCollectionAnalyser(config)
        # $_POST → form_data; $_GET → url_parameters
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
                        "raw_content": "$_POST['name']\n$_GET['id']",
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
        category_names = {c["collection_type"] for c in summary["categories"]}
        assert "form_data" in category_names
        assert "url_parameters" in category_names
        assert summary["categories_identified"] == len(summary["categories"])


# =============================================================================
# Source code input
# =============================================================================


class TestDataCollectionSourceCodeInput:
    """Tests for source code schema input handling."""

    @pytest.fixture
    def config(self) -> DataCollectionAnalyserConfig:
        return DataCollectionAnalyserConfig()

    @pytest.fixture
    def output_schema(self) -> Schema:
        return Schema("data_collection_indicator", "1.0.0")

    def test_accepts_source_code_schema_input(self, config, output_schema) -> None:
        """A source_code/1.0.0 input message is processed and findings carry correct metadata.source."""
        analyser = DataCollectionAnalyser(config)
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
                        "file_path": "app/form.php",
                        "language": "php",
                        "raw_content": "$_POST['name']",
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
        assert findings[0]["metadata"]["source"] == "app/form.php"

    def test_fan_in_merges_multiple_source_code_messages(
        self, config, output_schema
    ) -> None:
        """Two source_code messages produce findings from both."""
        analyser = DataCollectionAnalyser(config)
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
                        "file_path": "a/form.php",
                        "language": "php",
                        "raw_content": "$_POST['name']",
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
                        "file_path": "b/search.php",
                        "language": "php",
                        "raw_content": "$_GET['query']",
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
        assert "a/form.php" in sources
        assert "b/search.php" in sources


# =============================================================================
# Factory
# =============================================================================


class TestDataCollectionFactory:
    """Tests for factory validation."""

    def test_factory_creates_analyser_with_valid_config(self) -> None:
        """Factory creates an analyser that can process input."""
        container = ServiceContainer()
        factory = DataCollectionAnalyserFactory(container)
        properties = {}
        assert factory.can_create(properties) is True

        analyser = factory.create(properties)
        assert isinstance(analyser, DataCollectionAnalyser)

    def test_factory_rejects_invalid_ruleset(self) -> None:
        """can_create returns False for a non-existent ruleset."""
        container = ServiceContainer()
        factory = DataCollectionAnalyserFactory(container)
        properties = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
        }
        assert factory.can_create(properties) is False
