"""Unit tests for SourceCodeSchemaInputHandler."""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig

from waivern_data_subject_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)


class TestSourceCodeSchemaInputHandler:
    """Tests for SourceCodeSchemaInputHandler."""

    def test_analyse_raises_type_error_for_invalid_input(self) -> None:
        """Test that analyse raises TypeError when given non-SourceCodeDataModel."""
        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        invalid_data = {"not": "a SourceCodeDataModel"}

        # Act & Assert
        with pytest.raises(TypeError, match="Expected SourceCodeDataModel"):
            handler.analyse(invalid_data)

    def test_analyse_filters_rules_by_applicable_contexts(self) -> None:
        """Test that only rules with 'source_code' in applicable_contexts are applied.

        employee_hr_system_indicators rule has applicable_contexts: [database, filesystem]
        So patterns like 'salary' should NOT match in source_code context.

        employee_direct_role_fields rule has applicable_contexts: [database, source_code]
        So patterns like 'employee' SHOULD match.
        """
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        file_data = SourceCodeFileDataModel(
            file_path="/src/PayrollService.php",
            language="php",
            raw_content="""<?php
class PayrollService {
    public function calculateSalary($amount) {
        // This mentions salary but should NOT match (rule is database/filesystem only)
        return $amount * 1.1;
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=200, line_count=8, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Context filter test",
            description="Test context filtering",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=8, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert - 'salary' is in employee_hr_system_indicators which excludes source_code
        salary_findings = [
            f for f in findings if "salary" in [p.lower() for p in f.matched_patterns]
        ]
        assert len(salary_findings) == 0, (
            "salary pattern should not match - rule excludes source_code context"
        )

    def test_analyse_groups_findings_by_category(self) -> None:
        """Test that findings are grouped by subject category (one per category per file).

        Multiple matches of the same category in the same file should produce
        ONE indicator, not multiple.
        """
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        # This file has multiple employee patterns - should produce ONE employee indicator
        file_data = SourceCodeFileDataModel(
            file_path="/src/EmployeeService.php",
            language="php",
            raw_content="""<?php
class EmployeeService {
    private $employee;
    private $staff;
    private $worker;

    public function getEmployee() {
        return $this->employee;
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=200, line_count=10, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Grouping test",
            description="Test category grouping",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=10, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert - should have exactly ONE employee indicator, not multiple
        employee_findings = [f for f in findings if f.subject_category == "employee"]
        assert len(employee_findings) == 1, (
            f"Expected 1 employee indicator (grouped), got {len(employee_findings)}"
        )
        # The grouped indicator should have multiple matched patterns
        assert len(employee_findings[0].matched_patterns) >= 2, (
            "Grouped indicator should contain multiple matched patterns"
        )

    def test_analyse_calculates_confidence(self) -> None:
        """Test that confidence scores are calculated using the confidence scorer."""
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        file_data = SourceCodeFileDataModel(
            file_path="/src/CustomerService.php",
            language="php",
            raw_content="""<?php
class CustomerService {
    private $customer;

    public function getCustomer() {
        return $this->customer;
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=150, line_count=8, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Confidence test",
            description="Test confidence scoring",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=8, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"
        for finding in findings:
            assert isinstance(finding.confidence_score, int)
            assert 0 <= finding.confidence_score <= 100

    def test_analyse_deduplicates_matched_patterns(self) -> None:
        """Test that matched_patterns contains unique patterns only.

        When the same pattern (e.g., 'employee') matches multiple times
        across different lines, it should appear only once in matched_patterns.
        """
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        # This file has 'employee' appearing 4 times - should appear once in patterns
        file_data = SourceCodeFileDataModel(
            file_path="/src/EmployeeService.php",
            language="php",
            raw_content="""<?php
class EmployeeService {
    private $employee;

    public function getEmployee() {
        return $this->employee;
    }

    public function setEmployee($employee) {
        $this->employee = $employee;
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=250, line_count=12, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Deduplication test",
            description="Test pattern deduplication",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=12, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        employee_findings = [f for f in findings if f.subject_category == "employee"]
        assert len(employee_findings) == 1, "Expected exactly one employee indicator"

        # Check that patterns are deduplicated
        patterns = employee_findings[0].matched_patterns
        assert len(patterns) == len(set(patterns)), (
            f"matched_patterns contains duplicates: {patterns}"
        )

        # Verify 'employee' appears exactly once despite multiple occurrences in code
        employee_count = sum(1 for p in patterns if p.lower() == "employee")
        assert employee_count == 1, (
            f"'employee' should appear once, found {employee_count} times in {patterns}"
        )

    def test_metadata_includes_file_path_and_line_number(self) -> None:
        """Test that metadata contains file path and line number."""
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = SourceCodeSchemaInputHandler(config)
        file_data = SourceCodeFileDataModel(
            file_path="/src/PatientRecord.php",
            language="php",
            raw_content="""<?php
class PatientRecord {
    private $patient;
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=50, line_count=4, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Metadata test",
            description="Test metadata",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=4, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"
        finding = findings[0]
        assert finding.metadata is not None
        assert finding.metadata.source == "/src/PatientRecord.php"
        assert finding.metadata.line_number is not None
        assert finding.metadata.line_number > 0
