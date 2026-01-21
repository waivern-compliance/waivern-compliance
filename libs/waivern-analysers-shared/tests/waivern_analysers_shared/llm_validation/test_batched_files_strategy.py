"""Tests for BatchedFilesStrategyBase.

Business behaviour: Provides token-aware batching of findings by file
for efficient LLM validation. Groups findings by file, creates batches
that fit within token limits, and handles oversized files gracefully.
"""

from typing import override
from unittest.mock import Mock

from pydantic import Field
from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingModel,
    PatternMatchDetail,
)
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.batched_files_strategy import (
    BatchedFilesStrategyBase,
    FileBatch,
)
from waivern_analysers_shared.llm_validation.file_content import FileInfo
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)


class MockFinding(BaseFindingModel):
    """Mock finding for testing."""

    file_path: str = Field(description="File path for testing")
    purpose: str = Field(description="Purpose for testing")

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging."""
        return f"{self.purpose} - {', '.join(p.pattern for p in self.matched_patterns)}"


def _create_finding(purpose: str, file_path: str) -> MockFinding:
    """Create a mock finding with required base fields."""
    return MockFinding(
        file_path=file_path,
        purpose=purpose,
        evidence=[BaseFindingEvidence(content=f"Evidence for {purpose}")],
        matched_patterns=[PatternMatchDetail(pattern=purpose.lower(), match_count=1)],
    )


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
        validation_mode: str,
    ) -> str:
        """Generate mock validation prompt."""
        file_count = len(batch.files)
        finding_count = sum(len(findings_by_file[f]) for f in batch.files)
        return f"Validate {finding_count} findings across {file_count} files (mode: {validation_mode})"


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
            _create_finding("Payment", "src/app.py"),
            _create_finding("Documentation", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real payment processing",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.85,
                        reasoning="Just documentation",
                        recommended_action="discard",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 1
        assert result.validated_findings[0].purpose == "Payment"
        assert len(result.unvalidated_findings) == 0

    def test_returns_all_findings_when_all_true_positives(self) -> None:
        """Should keep all findings when LLM marks all as TRUE_POSITIVE."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real processing",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.85,
                        reasoning="Real analytics",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 2
        assert len(result.unvalidated_findings) == 0

    def test_returns_original_findings_on_llm_error(self) -> None:
        """Should return original findings when LLM call fails."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [_create_finding("Payment", "src/app.py")]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.side_effect = Exception(
            "LLM unavailable"
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert result.all_batches_succeeded is False
        assert len(result.validated_findings) == 0
        # Failed batch findings go to unvalidated
        assert len(result.unvalidated_findings) == 1
        assert result.unvalidated_findings[0].purpose == "Payment"

    def test_empty_findings_returns_empty_list(self) -> None:
        """Should return empty list for empty findings."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider({})
        mock_llm = Mock(spec=BaseLLMService)

        result = strategy.validate_findings_with_file_content(
            findings=[],
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        assert result.all_batches_succeeded is True
        assert result.validated_findings == []
        assert result.unvalidated_findings == []
        mock_llm.invoke_with_structured_output.assert_not_called()

    def test_includes_findings_omitted_by_llm(self) -> None:
        """Should include findings not mentioned in LLM response (fail-safe)."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
            _create_finding("Logging", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM only returns result for finding 0, omits 1 and 2
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real payment",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        # All 3 findings should be validated (1 explicitly + 2 via fail-safe)
        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 3
        result_purposes = {f.purpose for f in result.validated_findings}
        assert result_purposes == {"Payment", "Analytics", "Logging"}
        assert len(result.unvalidated_findings) == 0

    def test_rejects_invalid_finding_ids(self) -> None:
        """Should reject unknown finding IDs from LLM and include findings via fail-safe."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM returns invalid/unknown finding IDs
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id="unknown-id-1",
                        validation_result="FALSE_POSITIVE",
                        confidence=0.9,
                        reasoning="Bad",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id="unknown-id-2",
                        validation_result="FALSE_POSITIVE",
                        confidence=0.9,
                        reasoning="Bad",
                        recommended_action="discard",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        # Both findings should be validated (unknown IDs ignored, fail-safe applies)
        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 2
        result_purposes = {f.purpose for f in result.validated_findings}
        assert result_purposes == {"Payment", "Analytics"}
        assert len(result.unvalidated_findings) == 0

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
            _create_finding("FromHuge", "src/huge.py"),
            _create_finding("FromSmall", "src/small.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # Only the small file is batched, so only that finding is validated
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[1].id,  # FromSmall
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=500,  # Small limit to force huge file to be oversized
            llm_service=mock_llm,
        )

        # FromSmall is validated, FromHuge goes to unvalidated (oversized file)
        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 1
        assert result.validated_findings[0].purpose == "FromSmall"
        assert len(result.unvalidated_findings) == 1
        assert result.unvalidated_findings[0].purpose == "FromHuge"

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
            _create_finding("FromExisting", "src/exists.py"),
            _create_finding("FromMissing", "src/missing.py"),  # File not in provider
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # Only the existing file is batched, so only that finding is validated
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,  # FromExisting
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=5000,
            llm_service=mock_llm,
        )

        # FromExisting is validated, FromMissing goes to unvalidated (missing file)
        assert result.all_batches_succeeded is True
        assert len(result.validated_findings) == 1
        assert result.validated_findings[0].purpose == "FromExisting"
        assert len(result.unvalidated_findings) == 1
        assert result.unvalidated_findings[0].purpose == "FromMissing"

    def test_malformed_llm_response_marks_batch_as_failed(self) -> None:
        """Should mark batch as failed when LLM returns malformed response structure.

        With structured output, a malformed response causes an exception (from
        Pydantic validation or LangChain), so findings should go to unvalidated
        and all_batches_succeeded should be False. This ensures metadata accurately
        reflects validation failures.
        """
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # With structured output, LangChain/Pydantic raises an exception for
        # malformed responses (e.g., missing required finding_id field)
        mock_llm.invoke_with_structured_output.side_effect = Exception(
            "Validation error: missing required field 'finding_id'"
        )

        result = strategy.validate_findings_with_file_content(
            findings=findings,
            file_provider=file_provider,
            max_tokens_per_batch=10000,
            llm_service=mock_llm,
        )

        # Validation failed - batch should be marked as failed
        assert result.all_batches_succeeded is False
        # Findings should be preserved but as unvalidated (not validated!)
        assert len(result.unvalidated_findings) == 2
        assert len(result.validated_findings) == 0
        result_purposes = {f.purpose for f in result.unvalidated_findings}
        assert result_purposes == {"Payment", "Analytics"}
