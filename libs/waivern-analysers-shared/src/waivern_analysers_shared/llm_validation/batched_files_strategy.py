"""Abstract base class for batched-files LLM validation strategy.

Provides token-aware batching of findings by file for efficient LLM validation.
Concrete implementations define how to extract file paths from findings and
how to generate validation prompts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .file_content import FileContentProvider


@dataclass
class FileBatch[T]:
    """A batch of files to validate together.

    Type parameter T is the finding type.
    """

    files: list[str]
    """List of file paths in this batch."""

    estimated_tokens: int
    """Estimated total tokens for files in this batch."""


@dataclass
class BatchingResult[T]:
    """Result of creating token-aware batches.

    Type parameter T is the finding type.
    """

    batches: list[FileBatch[T]]
    """Batches that fit within token limits."""

    oversized_files: list[str] = field(default_factory=list)
    """Files that exceed the token limit on their own."""


class BatchedFilesStrategyBase[T](ABC):
    """Abstract base class for batched-files validation strategies.

    Provides token-aware batching infrastructure. Concrete implementations
    define analyser-specific behaviour (file path extraction, prompt generation).

    Type parameter T is the finding type (e.g., ProcessingPurposeFindingModel).
    """

    @abstractmethod
    def extract_file_path_from_finding(self, finding: T) -> str | None:
        """Extract the source file path from a finding.

        Args:
            finding: The finding to extract file path from.

        Returns:
            File path string, or None if path cannot be extracted.

        """
        ...

    @abstractmethod
    def get_batch_validation_prompt(
        self,
        batch: FileBatch[T],
        findings_by_file: dict[str, list[T]],
    ) -> str:
        """Generate the LLM validation prompt for a batch.

        Args:
            batch: The batch of files to validate.
            findings_by_file: Mapping of file paths to their findings.

        Returns:
            Formatted prompt string for LLM validation.

        """
        ...

    def group_findings_by_file(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by their source file.

        Args:
            findings: List of findings to group.

        Returns:
            Dictionary mapping file paths to their findings.
            Findings with no extractable file path are excluded.

        """
        grouped: dict[str, list[T]] = {}

        for finding in findings:
            file_path = self.extract_file_path_from_finding(finding)
            if file_path:
                if file_path not in grouped:
                    grouped[file_path] = []
                grouped[file_path].append(finding)

        return grouped

    def create_token_aware_batches(
        self,
        findings_by_file: dict[str, list[T]],
        file_provider: FileContentProvider,
        max_tokens_per_batch: int,
    ) -> BatchingResult[T]:
        """Create batches of files that fit within token limits.

        Uses greedy bin-packing: adds files to current batch until limit
        is reached, then starts a new batch.

        Args:
            findings_by_file: Mapping of file paths to their findings.
            file_provider: Provider for file content and token estimates.
            max_tokens_per_batch: Maximum tokens allowed per batch.

        Returns:
            BatchingResult with batches and any oversized files.

        """
        all_files = file_provider.get_all_files()
        batches: list[FileBatch[T]] = []
        oversized_files: list[str] = []

        # Current batch being built
        current_files: list[str] = []
        current_tokens = 0

        # Sort files by token count (largest first) for better packing
        file_paths = sorted(
            findings_by_file.keys(),
            key=lambda p: all_files[p].estimated_tokens if p in all_files else 0,
            reverse=True,
        )

        for file_path in file_paths:
            if file_path not in all_files:
                # File not found in provider - skip
                continue

            file_info = all_files[file_path]
            file_tokens = file_info.estimated_tokens

            # Check if file exceeds limit on its own
            if file_tokens > max_tokens_per_batch:
                oversized_files.append(file_path)
                continue

            # Check if file fits in current batch
            if current_tokens + file_tokens <= max_tokens_per_batch:
                current_files.append(file_path)
                current_tokens += file_tokens
            else:
                # Finalize current batch and start new one
                if current_files:
                    batches.append(
                        FileBatch(
                            files=current_files,
                            estimated_tokens=current_tokens,
                        )
                    )
                current_files = [file_path]
                current_tokens = file_tokens

        # Don't forget the last batch
        if current_files:
            batches.append(
                FileBatch(
                    files=current_files,
                    estimated_tokens=current_tokens,
                )
            )

        return BatchingResult(batches=batches, oversized_files=oversized_files)
