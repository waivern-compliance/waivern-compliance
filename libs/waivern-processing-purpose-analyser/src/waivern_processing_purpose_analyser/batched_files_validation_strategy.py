"""Batched-files validation strategy for processing purpose findings.

Implements token-aware file batching for efficient LLM validation of
source code findings.
"""

import re
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
        """Extract the source file path from a finding's evidence.

        The evidence content format from source code handler is:
        ```
        file/path.py
           1  line content
           2→ matched line
           3  line content
        ```

        Args:
            finding: The finding to extract file path from.

        Returns:
            File path string (first line of evidence content).

        """
        # File path is the first line of evidence content
        return finding.evidence[0].content.split("\n")[0]

    @override
    def get_batch_validation_prompt(
        self,
        batch: FileBatch[ProcessingPurposeFindingModel],
        findings_by_file: dict[str, list[ProcessingPurposeFindingModel]],
        file_contents: dict[str, str] | None = None,
    ) -> str:
        """Generate validation prompt for a batch of files.

        Args:
            batch: The batch of files to validate.
            findings_by_file: Mapping of file paths to their findings.
            file_contents: Mapping of file paths to their full content.

        Returns:
            Formatted prompt string for LLM validation.

        """
        file_contents = file_contents or {}

        # Build source files section
        source_files_section = self._build_source_files_section(
            batch.files, file_contents, findings_by_file
        )

        # Build findings section with global indices
        findings_section = self._build_findings_section(batch.files, findings_by_file)

        prompt_template = _PROMPT_PATH.read_text()
        return prompt_template.format(
            source_files_section=source_files_section,
            findings_section=findings_section,
        )

    def _build_source_files_section(
        self,
        files: list[str],
        file_contents: dict[str, str],
        findings_by_file: dict[str, list[ProcessingPurposeFindingModel]],
    ) -> str:
        """Build the source files section of the prompt."""
        sections: list[str] = []

        for file_path in files:
            content = file_contents.get(file_path, "[Content unavailable]")
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
        """Build the findings section with global indices."""
        lines: list[str] = []
        global_index = 0

        for file_path in files:
            findings = findings_by_file.get(file_path, [])
            if not findings:
                continue

            lines.append(f"\nFile: {file_path}")
            for finding in findings:
                line_num = self._extract_line_number(finding)
                patterns = ", ".join(finding.matched_patterns)
                lines.append(
                    f"  [{global_index}] Purpose: {finding.purpose}, "
                    f"Patterns: {patterns}, Line: L{line_num}"
                )
                global_index += 1

        return "\n".join(lines)

    def _extract_line_number(self, finding: ProcessingPurposeFindingModel) -> int:
        """Extract the matched line number from a finding's evidence.

        The evidence contains lines formatted as:
        ```
           42→ matched line content
        ```

        Args:
            finding: The finding to extract line number from.

        Returns:
            Line number as integer.

        """
        content = finding.evidence[0].content

        # Find line with arrow indicator (e.g., "  42→ content")
        for line in content.split("\n"):
            if "→" in line:
                match = re.match(r"\s*(\d+)→", line)
                if match:
                    return int(match.group(1))

        # Source code handler always includes arrow indicator
        raise ValueError("Evidence missing line number indicator")
