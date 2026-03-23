"""Prompt builder for source code validation with full file content."""

from collections.abc import Sequence
from typing import override

from waivern_llm import ItemGroup, PromptBuilder
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorModel,
)


class SourceCodePromptBuilder(PromptBuilder[ProcessingPurposeIndicatorModel]):
    """Prompt builder for source code validation with full file content.

    Uses EXTENDED_CONTEXT batching mode — receives one or more groups per
    batch, each containing a source file's content and its findings.
    """

    def __init__(self, validation_mode: str = "standard") -> None:
        """Initialise prompt builder.

        Args:
            validation_mode: Validation mode (e.g., "standard", "strict").

        """
        self._validation_mode = validation_mode

    @override
    def build_prompt(
        self,
        groups: Sequence[ItemGroup[ProcessingPurposeIndicatorModel]],
    ) -> str:
        """Build validation prompt with per-file sections.

        Each group represents a source file with its content and findings.
        Multiple groups are bin-packed into a single batch by the planner.

        Args:
            groups: Groups of findings, each with source file content.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If any group has empty items or None content.

        """
        for group in groups:
            if not group.items:
                raise ValueError("At least one finding is required")
            if group.content is None:
                raise ValueError("content is required for source code validation")

        file_sections = self._build_file_sections(groups)
        total_findings = sum(len(g.items) for g in groups)

        return f"""You are an expert data processing analyst. Validate processing purpose indicators using the full source file context.

**VALIDATION MODE:** {self._validation_mode}

**SOURCE FILES:**
{file_sections}

**VALIDATION CRITERIA:**
- TRUE_POSITIVE: Actual business processing activities affecting real users/customers
- FALSE_POSITIVE: Documentation, examples, tutorials, code comments, test fixtures, configuration templates

**SOURCE CODE CONTEXT GUIDELINES:**
- Test files (`test_*.py`, `*_test.js`, `__tests__/*`): Usually FALSE_POSITIVE (test fixtures)
- Documentation (`README.md`, `docs/*`, `*.md`): Usually FALSE_POSITIVE
- Example/sample files (`*.example.*`, `sample/*`): Usually FALSE_POSITIVE
- Production code (`src/*`, `lib/*`, `app/*`): Requires deeper analysis
- Vendor/dependencies (`node_modules/*`, `vendor/*`): Usually FALSE_POSITIVE (library docs/examples, not application code)

**RESPONSE FORMAT:**
Return a JSON object with a "results" array containing ONLY the FALSE_POSITIVE findings.
Do not include TRUE_POSITIVE findings - they will be kept automatically.
IMPORTANT: Echo back the exact finding_id from each finding entry - do not modify it.

{{
  "results": [
    {{
      "finding_id": "<exact UUID from finding entry>",
      "validation_result": "FALSE_POSITIVE",
      "confidence": 0.85,
      "reasoning": "Brief explanation",
      "recommended_action": "discard"
    }}
  ]
}}

Review all {total_findings} findings. Return ONLY the FALSE_POSITIVE ones (empty array if none):"""

    def _build_file_sections(
        self,
        groups: Sequence[ItemGroup[ProcessingPurposeIndicatorModel]],
    ) -> str:
        """Build per-file sections with content and findings for each group."""
        sections: list[str] = []
        for group in groups:
            content = group.content or ""
            file_header = self._build_source_file_section(group.items, content)
            findings = self._build_findings_section(group.items)
            sections.append(f"{file_header}\n\nFindings:\n{findings}")
        return "\n\n".join(sections)

    def _build_source_file_section(
        self,
        items: Sequence[ProcessingPurposeIndicatorModel],
        content: str,
    ) -> str:
        """Build the source file section with content and finding count."""
        # Get source from first finding (all findings in a group share the same source)
        source = items[0].metadata.source if items[0].metadata else "unknown"
        finding_count = len(items)

        return f"""=== File: {source} ({finding_count} findings) ===
{content}"""

    def _build_findings_section(
        self,
        items: Sequence[ProcessingPurposeIndicatorModel],
    ) -> str:
        """Build the findings section with IDs, purposes, patterns, and line numbers."""
        lines: list[str] = []

        for finding in items:
            line_num = finding.metadata.line_number if finding.metadata else None
            patterns = ", ".join(
                f"{p.pattern} (×{p.match_count})" for p in finding.matched_patterns
            )
            lines.append(
                f"[{finding.id}] Purpose: {finding.purpose}, "
                f"Patterns: {patterns}, Line: L{line_num}"
            )

        return "\n".join(lines)
