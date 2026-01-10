"""Tests for BatchedFilesStrategyBase.

Business behaviour: Provides token-aware batching of findings by file
for efficient LLM validation. Groups findings by file, creates batches
that fit within token limits, and handles oversized files gracefully.
"""

import json
from dataclasses import dataclass
from typing import override
from unittest.mock import Mock

from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.batched_files_strategy import (
    BatchedFilesStrategyBase,
    FileBatch,
)
from waivern_analysers_shared.llm_validation.file_content import FileInfo


@dataclass
class MockFinding:
    """Mock finding for testing."""

    id: str
    file_path: str
    purpose: str


class MockBatchedFilesStrategy(BatchedFilesStrategyBase[MockFinding]):
    """Concrete implementation for testing abstract base class."""

    @override
    def extract_file_path_from_finding(self, finding: MockFinding) -> str | None:
        """Extract file path from mock finding."""
        return finding.file_path

    @override
    def get_batch_validation_prompt(
        self,
        batch: FileBatch[MockFinding],
        findings_by_file: dict[str, list[MockFinding]],
        file_contents: dict[str, str],
    ) -> str:
        """Generate mock validation prompt."""
        file_count = len(batch.files)
        finding_count = sum(len(findings_by_file[f]) for f in batch.files)
        return f"Validate {finding_count} findings across {file_count} files"


class MockFileContentProvider:
    """Mock file content provider for testing."""

    def __init__(self, files: dict[str, str]) -> None:
        """Initialise with file content mapping."""
        self._files = files

    def get_file_content(self, file_path: str) -> str | None:
        """Get content for a file."""
        return self._files.get(file_path)

    def get_all_files(self) -> dict[str, FileInfo]:
        """Get all files with token estimates (metadata only, no content)."""
        return {
            path: FileInfo(
                file_path=path,
                # Rough estimate: 1 token per 4 chars
                estimated_tokens=len(content) // 4,
            )
            for path, content in self._files.items()
        }


class TestValidateFindingsWithFileContent:
    """Tests for the main validation orchestration method."""

    def test_filters_false_positives_from_validation_response(self) -> None:
        """Should filter out findings marked as FALSE_POSITIVE by LLM."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            MockFinding("1", "src/app.py", "Payment"),
            MockFinding("2", "src/app.py", "Documentation"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Real payment processing",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.85,
                    "reasoning": "Just documentation",
                    "recommended_action": "discard",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert success is True
        assert len(result) == 1
        assert result[0].id == "1"

    def test_returns_all_findings_when_all_true_positives(self) -> None:
        """Should keep all findings when LLM marks all as TRUE_POSITIVE."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            MockFinding("1", "src/app.py", "Payment"),
            MockFinding("2", "src/app.py", "Analytics"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Real processing",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.85,
                    "reasoning": "Real analytics",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert success is True
        assert len(result) == 2

    def test_returns_original_findings_on_llm_error(self) -> None:
        """Should return original findings when LLM call fails."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [MockFinding("1", "src/app.py", "Payment")]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.analyse_data.side_effect = Exception("LLM unavailable")

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert success is False
        assert len(result) == 1
        assert result[0].id == "1"

    def test_empty_findings_returns_empty_list(self) -> None:
        """Should return empty list for empty findings."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider({})
        mock_llm = Mock(spec=BaseLLMService)

        result, success = strategy.validate_findings_with_file_content(
            findings=[],
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert success is True
        assert result == []
        mock_llm.analyse_data.assert_not_called()

    def test_includes_findings_omitted_by_llm(self) -> None:
        """Should include findings not mentioned in LLM response (fail-safe)."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            MockFinding("1", "src/app.py", "Payment"),
            MockFinding("2", "src/app.py", "Analytics"),
            MockFinding("3", "src/app.py", "Logging"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM only returns result for finding 0, omits 1 and 2
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Real payment",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        # All 3 findings should be in result (1 validated + 2 unvalidated)
        assert success is True
        assert len(result) == 3
        result_ids = {f.id for f in result}
        assert result_ids == {"1", "2", "3"}

    def test_rejects_invalid_finding_indices(self) -> None:
        """Should reject negative and out-of-range finding indices from LLM."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            MockFinding("1", "src/app.py", "Payment"),
            MockFinding("2", "src/app.py", "Analytics"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM returns invalid indices: -1 (negative) and 99 (out of range)
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": -1,  # Invalid: negative
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Bad",
                    "recommended_action": "discard",
                },
                {
                    "finding_index": 99,  # Invalid: out of range
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Bad",
                    "recommended_action": "discard",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        # Both findings should be included (invalid indices ignored, fail-safe applies)
        assert success is True
        assert len(result) == 2
        result_ids = {f.id for f in result}
        assert result_ids == {"1", "2"}

    def test_includes_findings_from_oversized_files(self) -> None:
        """Should include findings from files too large to batch."""
        strategy = MockBatchedFilesStrategy()
        # One huge file that exceeds token limit, one small file
        file_provider = MockFileContentProvider(
            {
                "src/huge.py": "a" * 40000,  # ~10000 tokens - exceeds limit
                "src/small.py": "b" * 400,  # ~100 tokens - fits
            }
        )
        findings = [
            MockFinding("1", "src/huge.py", "FromHuge"),
            MockFinding("2", "src/small.py", "FromSmall"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Valid",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=500,  # Small limit to force huge file to be oversized
            llm_service=mock_llm,
        )

        # Both findings should be included
        assert success is True
        assert len(result) == 2
        result_ids = {f.id for f in result}
        assert result_ids == {"1", "2"}

    def test_includes_findings_from_missing_files(self) -> None:
        """Should include findings from files not found in provider (fail-safe)."""
        strategy = MockBatchedFilesStrategy()
        # Only one file in provider, but findings reference another file too
        file_provider = MockFileContentProvider(
            {
                "src/exists.py": "content " * 100,
            }
        )
        findings = [
            MockFinding("1", "src/exists.py", "FromExisting"),
            MockFinding("2", "src/missing.py", "FromMissing"),  # File not in provider
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.analyse_data.return_value = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Valid",
                    "recommended_action": "keep",
                },
            ]
        )

        result, success = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=5000,
            llm_service=mock_llm,
        )

        # Both findings should be included (missing file findings included unvalidated)
        assert success is True
        assert len(result) == 2
        result_ids = {f.id for f in result}
        assert result_ids == {"1", "2"}
