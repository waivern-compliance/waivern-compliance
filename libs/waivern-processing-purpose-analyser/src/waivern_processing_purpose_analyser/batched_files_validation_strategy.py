"""Batched-files validation strategy for processing purpose findings.

Implements token-aware file batching for efficient LLM validation of
source code findings.
"""

from pathlib import Path
from typing import override

from waivern_analysers_shared.llm_validation.batched_files_strategy import (
    BatchedFilesStrategyBase,
    FileBatch,
)

from .schemas.types import ProcessingPurposeFindingModel

_PROMPT_PATH = Path(__file__).parent / "prompts" / "batched_files_validation.md"


class ProcessingPurposeBatchedFilesStrategy(
    BatchedFilesStrategyBase[ProcessingPurposeFindingModel]
):
    """Batched-files validation strategy for processing purpose findings.

    Extracts file paths and line numbers from source code findings to enable
    efficient batch validation with full file context.
    """

    @override
    def extract_file_path_from_finding(
        self, finding: ProcessingPurposeFindingModel
    ) -> str | None:
        """Extract the source file path from a finding's metadata.

        Args:
            finding: The finding to extract file path from.

        Returns:
            File path string from metadata.source, or None if not available.

        """
        if finding.metadata is None:
            return None
        return finding.metadata.source

    @override
    def get_batch_validation_prompt(
        self,
        batch: FileBatch[ProcessingPurposeFindingModel],
        findings_by_file: dict[str, list[ProcessingPurposeFindingModel]],
        file_contents: dict[str, str],
        validation_mode: str,
    ) -> str:
        """Generate validation prompt for a batch of files.

        Args:
            batch: The batch of files to validate.
            findings_by_file: Mapping of file paths to their findings.
            file_contents: Mapping of file paths to their full content.
            validation_mode: Validation mode ("standard", "conservative", "aggressive").

        Returns:
            Formatted prompt string for LLM validation.

        """
        # Build source files section
        source_files_section = self._build_source_files_section(
            batch.files, file_contents, findings_by_file
        )

        # Build findings section with global indices
        findings_section = self._build_findings_section(batch.files, findings_by_file)

        # Use replace() instead of format() to avoid issues with curly braces
        # in source code content (e.g., JavaScript objects, Python dicts)
        prompt_template = _PROMPT_PATH.read_text()
        return (
            prompt_template.replace("{validation_mode}", validation_mode)
            .replace("{source_files_section}", source_files_section)
            .replace("{findings_section}", findings_section)
        )

    def _build_source_files_section(
        self,
        files: list[str],
        file_contents: dict[str, str],
        findings_by_file: dict[str, list[ProcessingPurposeFindingModel]],
    ) -> str:
        """Build the source files section of the prompt.

        Output format:
        ```
        === File: src/payments/checkout.py (3 findings) ===
        import stripe

        def process_payment(amount):
            return stripe.Charge.create(amount=amount)

        === File: src/analytics/tracker.py (2 findings) ===
        from mixpanel import Mixpanel

        def track_event(user_id, event):
            mp.track(user_id, event)
        ```
        """
        sections: list[str] = []

        for file_path in files:
            content = file_contents[file_path]
            finding_count = len(findings_by_file.get(file_path, []))
            sections.append(
                f"=== File: {file_path} ({finding_count} findings) ===\n{content}"
            )

        return "\n\n".join(sections)

    def _build_findings_section(
        self,
        files: list[str],
        findings_by_file: dict[str, list[ProcessingPurposeFindingModel]],
    ) -> str:
        """Build the findings section with finding IDs.

        Output format:
        ```
        File: src/payments/checkout.py
          [a1b2c3d4-...] Purpose: Payment Processing, Patterns: stripe, checkout, Line: L42
          [e5f6g7h8-...] Purpose: Transaction Logging, Patterns: log_transaction, Line: L58

        File: src/analytics/tracker.py
          [i9j0k1l2-...] Purpose: User Analytics, Patterns: mixpanel, track, Line: L12
        ```

        The finding ID (UUID) is used by the LLM to reference specific findings
        in its validation response.
        """
        lines: list[str] = []

        for file_path in files:
            findings = findings_by_file[file_path]
            lines.append(f"\nFile: {file_path}")
            for finding in findings:
                line_num = finding.metadata.line_number if finding.metadata else None
                patterns = ", ".join(finding.matched_patterns)
                lines.append(
                    f"  [{finding.id}] Purpose: {finding.purpose}, "
                    f"Patterns: {patterns}, Line: L{line_num}"
                )

        return "\n".join(lines)
