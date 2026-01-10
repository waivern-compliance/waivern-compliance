"""Tests for ProcessingPurposeBatchedFilesStrategy.

Business behaviour: Extracts file paths from source code findings and
generates batched validation prompts with full file content.
"""

from waivern_core.schemas import BaseFindingEvidence

from waivern_processing_purpose_analyser.batched_files_validation_strategy import (
    ProcessingPurposeBatchedFilesStrategy,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)


def _create_source_code_finding(
    purpose: str,
    file_path: str,
    line_content: str,
    matched_patterns: list[str] | None = None,
    line_number: int = 42,
) -> ProcessingPurposeFindingModel:
    """Create a source code finding with metadata.source set to file path."""
    evidence_content = f"{file_path}\n  {line_number}→ {line_content}"
    return ProcessingPurposeFindingModel(
        purpose=purpose,
        purpose_category="operational",
        matched_patterns=matched_patterns or [purpose.lower()],
        evidence=[BaseFindingEvidence(content=evidence_content)],
        metadata=ProcessingPurposeFindingMetadata(source=file_path),
    )


class TestExtractFilePathFromFinding:
    """Tests for extracting file paths from source code findings."""

    def test_extracts_file_path_from_source_code_finding(self) -> None:
        """Should extract file path from a source code finding."""
        strategy = ProcessingPurposeBatchedFilesStrategy()
        finding = _create_source_code_finding(
            purpose="Analytics",
            file_path="src/services/analytics.py",
            line_content="track_event(user_id, event)",
        )

        result = strategy.extract_file_path_from_finding(finding)

        assert result == "src/services/analytics.py"

    def test_extracts_file_paths_with_spaces(self) -> None:
        """Should extract file paths containing spaces."""
        strategy = ProcessingPurposeBatchedFilesStrategy()
        finding = _create_source_code_finding(
            purpose="Analytics",
            file_path="src/My Project/analytics service.py",
            line_content="track_event()",
        )

        result = strategy.extract_file_path_from_finding(finding)

        assert result == "src/My Project/analytics service.py"
