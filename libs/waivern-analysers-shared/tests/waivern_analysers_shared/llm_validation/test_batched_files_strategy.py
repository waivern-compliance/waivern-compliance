"""Tests for BatchedFilesStrategyBase.

Business behaviour: Provides token-aware batching of findings by file
for efficient LLM validation. Groups findings by file, creates batches
that fit within token limits, and handles oversized files gracefully.
"""

from dataclasses import dataclass
from typing import override

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
        """Get all files with token estimates."""
        return {
            path: FileInfo(
                file_path=path,
                content=content,
                # Rough estimate: 1 token per 4 chars
                estimated_tokens=len(content) // 4,
            )
            for path, content in self._files.items()
        }


class TestGroupFindingsByFile:
    """Tests for grouping findings by their source file."""

    def test_groups_findings_by_file_path(self) -> None:
        """Should group findings by their extracted file path."""
        strategy = MockBatchedFilesStrategy()
        findings = [
            MockFinding(id="1", file_path="src/app.py", purpose="Analytics"),
            MockFinding(id="2", file_path="src/app.py", purpose="Payment"),
            MockFinding(id="3", file_path="src/utils.py", purpose="Logging"),
        ]

        grouped = strategy.group_findings_by_file(findings)

        assert len(grouped) == 2
        assert len(grouped["src/app.py"]) == 2
        assert len(grouped["src/utils.py"]) == 1

    def test_excludes_findings_with_no_file_path(self) -> None:
        """Should exclude findings where file path cannot be extracted."""

        class NullPathStrategy(BatchedFilesStrategyBase[MockFinding]):
            @override
            def extract_file_path_from_finding(
                self, finding: MockFinding
            ) -> str | None:
                # Return None for findings with empty path
                return finding.file_path if finding.file_path else None

            @override
            def get_batch_validation_prompt(
                self,
                batch: FileBatch[MockFinding],
                findings_by_file: dict[str, list[MockFinding]],
            ) -> str:
                return "prompt"

        strategy = NullPathStrategy()
        findings = [
            MockFinding(id="1", file_path="src/app.py", purpose="Analytics"),
            MockFinding(id="2", file_path="", purpose="Unknown"),  # No path
        ]

        grouped = strategy.group_findings_by_file(findings)

        assert len(grouped) == 1
        assert "src/app.py" in grouped

    def test_empty_findings_returns_empty_dict(self) -> None:
        """Should return empty dict for empty findings list."""
        strategy = MockBatchedFilesStrategy()

        grouped = strategy.group_findings_by_file([])

        assert grouped == {}


class TestCreateTokenAwareBatches:
    """Tests for token-aware batch creation."""

    def test_creates_single_batch_when_all_files_fit(self) -> None:
        """Should create single batch when total tokens are under limit."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {
                "src/app.py": "a" * 400,  # ~100 tokens
                "src/utils.py": "b" * 400,  # ~100 tokens
            }
        )
        findings_by_file = {
            "src/app.py": [MockFinding("1", "src/app.py", "A")],
            "src/utils.py": [MockFinding("2", "src/utils.py", "B")],
        }

        result = strategy.create_token_aware_batches(
            findings_by_file=findings_by_file,
            file_provider=file_provider,
            max_tokens_per_batch=1000,
        )

        assert len(result.batches) == 1
        assert len(result.batches[0].files) == 2
        assert len(result.oversized_files) == 0

    def test_creates_multiple_batches_when_exceeding_limit(self) -> None:
        """Should create multiple batches when files exceed token limit."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {
                "src/app.py": "a" * 2000,  # ~500 tokens
                "src/utils.py": "b" * 2000,  # ~500 tokens
                "src/db.py": "c" * 2000,  # ~500 tokens
            }
        )
        findings_by_file = {
            "src/app.py": [MockFinding("1", "src/app.py", "A")],
            "src/utils.py": [MockFinding("2", "src/utils.py", "B")],
            "src/db.py": [MockFinding("3", "src/db.py", "C")],
        }

        result = strategy.create_token_aware_batches(
            findings_by_file=findings_by_file,
            file_provider=file_provider,
            max_tokens_per_batch=800,  # Can fit ~1-2 files per batch
        )

        assert len(result.batches) >= 2
        # All files should be distributed across batches
        all_files = [f for batch in result.batches for f in batch.files]
        assert set(all_files) == {"src/app.py", "src/utils.py", "src/db.py"}

    def test_handles_oversized_single_file(self) -> None:
        """Should mark files that exceed limit on their own as oversized."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {
                "src/huge.py": "a" * 8000,  # ~2000 tokens - exceeds limit
                "src/small.py": "b" * 400,  # ~100 tokens - fits
            }
        )
        findings_by_file = {
            "src/huge.py": [MockFinding("1", "src/huge.py", "A")],
            "src/small.py": [MockFinding("2", "src/small.py", "B")],
        }

        result = strategy.create_token_aware_batches(
            findings_by_file=findings_by_file,
            file_provider=file_provider,
            max_tokens_per_batch=500,
        )

        assert "src/huge.py" in result.oversized_files
        assert any("src/small.py" in batch.files for batch in result.batches)

    def test_batch_tracks_estimated_tokens(self) -> None:
        """Should track estimated tokens for each batch."""
        strategy = MockBatchedFilesStrategy()
        file_provider = MockFileContentProvider(
            {
                "src/app.py": "a" * 400,  # ~100 tokens
            }
        )
        findings_by_file = {
            "src/app.py": [MockFinding("1", "src/app.py", "A")],
        }

        result = strategy.create_token_aware_batches(
            findings_by_file=findings_by_file,
            file_provider=file_provider,
            max_tokens_per_batch=1000,
        )

        assert result.batches[0].estimated_tokens > 0
        assert result.batches[0].estimated_tokens == 100  # 400 chars / 4
