"""Prompt builder for source code validation with full file content."""

from collections.abc import Sequence
from typing import override

from waivern_llm.v2 import PromptBuilder

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
)


class SourceCodePromptBuilder(PromptBuilder[ProcessingPurposeIndicatorModel]):
    """Prompt builder for source code validation with full file content.

    Uses EXTENDED_CONTEXT batching mode — the `content` parameter contains
    the full source file content for context-aware validation.
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
        items: Sequence[ProcessingPurposeIndicatorModel],
        content: str | None = None,
    ) -> str:
        """Build validation prompt with full file content.

        Args:
            items: Findings from this source file.
            content: Full source file content (required for EXTENDED_CONTEXT mode).

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If items is empty or content is None.

        """
        if not items:
            raise ValueError("At least one finding is required")
        if content is None:
            raise ValueError("content is required for EXTENDED_CONTEXT batching")

        source_file_section = self._build_source_file_section(items, content)
        findings_section = self._build_findings_section(items)

        return f"""You are an expert data processing analyst. Validate processing purpose indicators using the full source file context.

**VALIDATION MODE:** {self._validation_mode}

**SOURCE FILE:**
{source_file_section}

**FINDINGS TO VALIDATE:**
{findings_section}

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

Review all {len(items)} findings. Return ONLY the FALSE_POSITIVE ones (empty array if none):"""

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
