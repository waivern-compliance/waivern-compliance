"""Unit tests for SourceCodeSchemaInputHandler.

Uses synthetic rules injected via constructor to decouple from
production ruleset data.
"""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)

from waivern_data_subject_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)

# =============================================================================
# Synthetic rules
# =============================================================================

RULE_EMPLOYEE_A = DataSubjectIndicatorRule(
    name="Test Employee A",
    description="Employee indicator A",
    subject_category="test_employee",
    indicator_type="primary",
    confidence_weight=45,
    patterns=("test_employee_a_kw",),
)

RULE_EMPLOYEE_B = DataSubjectIndicatorRule(
    name="Test Employee B",
    description="Employee indicator B",
    subject_category="test_employee",
    indicator_type="secondary",
    confidence_weight=25,
    patterns=("test_employee_b_kw",),
)

RULE_CUSTOMER = DataSubjectIndicatorRule(
    name="Test Customer",
    description="Customer indicator",
    subject_category="test_customer",
    indicator_type="primary",
    confidence_weight=50,
    patterns=("test_customer_kw",),
)

SYNTHETIC_RULES = (RULE_EMPLOYEE_A, RULE_EMPLOYEE_B, RULE_CUSTOMER)

_UNUSED_RULESET_URI = "unused/test/1.0.0"

_DEFAULT_FILE_METADATA = SourceCodeFileMetadataModel(
    file_size=200, line_count=10, last_modified="2024-01-01T00:00:00Z"
)

_DEFAULT_ANALYSIS_METADATA = SourceCodeAnalysisMetadataModel(
    total_files=1, total_lines=10, analysis_timestamp="2024-01-01T00:00:00Z"
)


def _make_handler() -> SourceCodeSchemaInputHandler:
    """Create a handler with synthetic rules and default config."""
    config = PatternMatchingConfig(ruleset=_UNUSED_RULESET_URI)
    return SourceCodeSchemaInputHandler(SYNTHETIC_RULES, config)


def _make_source_data(file_path: str, raw_content: str) -> SourceCodeDataModel:
    """Create a SourceCodeDataModel with a single file."""
    return SourceCodeDataModel(
        schemaVersion="1.0.0",
        name="Test source",
        description="Test",
        source="source_code",
        metadata=_DEFAULT_ANALYSIS_METADATA,
        data=[
            SourceCodeFileDataModel(
                file_path=file_path,
                language="php",
                raw_content=raw_content,
                metadata=_DEFAULT_FILE_METADATA,
            )
        ],
    )


# =============================================================================
# Tests
# =============================================================================


class TestSourceCodeSchemaInputHandler:
    """Tests for SourceCodeSchemaInputHandler."""

    def test_analyse_raises_type_error_for_invalid_input(self) -> None:
        """Test that analyse raises TypeError when given non-SourceCodeDataModel."""
        handler = _make_handler()
        invalid_data = {"not": "a SourceCodeDataModel"}

        with pytest.raises(TypeError, match="Expected SourceCodeDataModel"):
            handler.analyse(invalid_data)

    def test_analyse_groups_findings_by_category(self) -> None:
        """Multiple matches of the same category in a file produce one indicator."""
        handler = _make_handler()
        source_data = _make_source_data(
            "/src/Service.php",
            "line with test_employee_a_kw\nline with test_employee_b_kw\n",
        )

        findings = handler.analyse(source_data)

        employee_findings = [
            f for f in findings if f.subject_category == "test_employee"
        ]
        assert len(employee_findings) == 1
        assert len(employee_findings[0].matched_patterns) == 2

    def test_analyse_calculates_confidence(self) -> None:
        """Confidence scores are calculated from matched rule weights."""
        handler = _make_handler()
        source_data = _make_source_data(
            "/src/Service.php",
            "test_employee_a_kw found here\n",
        )

        findings = handler.analyse(source_data)

        assert len(findings) == 1
        assert findings[0].confidence_score == 45

    def test_analyse_deduplicates_matched_patterns(self) -> None:
        """Same pattern on multiple lines appears once in matched_patterns."""
        handler = _make_handler()
        source_data = _make_source_data(
            "/src/Service.php",
            "test_employee_a_kw on line 1\ntest_employee_a_kw on line 2\ntest_employee_a_kw on line 3\n",
        )

        findings = handler.analyse(source_data)

        employee_findings = [
            f for f in findings if f.subject_category == "test_employee"
        ]
        assert len(employee_findings) == 1
        pattern_strs = [p.pattern for p in employee_findings[0].matched_patterns]
        assert len(pattern_strs) == len(set(pattern_strs))

    def test_metadata_includes_file_path_and_line_number(self) -> None:
        """Finding metadata contains the file path and first match line number."""
        handler = _make_handler()
        source_data = _make_source_data(
            "/src/Record.php",
            "nothing here\ntest_customer_kw on line 2\n",
        )

        findings = handler.analyse(source_data)

        assert len(findings) == 1
        assert findings[0].metadata is not None
        assert findings[0].metadata.source == "/src/Record.php"
        assert findings[0].metadata.line_number == 2
