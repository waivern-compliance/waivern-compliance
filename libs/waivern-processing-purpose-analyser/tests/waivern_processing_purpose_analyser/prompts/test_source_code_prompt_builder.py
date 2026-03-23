"""Tests for SourceCodePromptBuilder.

Tests verify the PromptBuilder protocol implementation for source code validation
with full file content (EXTENDED_CONTEXT mode with bin-packing).
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_llm import ItemGroup
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorMetadata,
    ProcessingPurposeIndicatorModel,
)

from waivern_processing_purpose_analyser.prompts import SourceCodePromptBuilder


def _make_finding(
    purpose: str = "Payment Processing",
    pattern: str = "payment",
    source: str = "/src/payments.php",
    line_number: int = 42,
) -> ProcessingPurposeIndicatorModel:
    """Create a finding for testing."""
    return ProcessingPurposeIndicatorModel(
        purpose=purpose,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=ProcessingPurposeIndicatorMetadata(
            source=source, line_number=line_number
        ),
    )


class TestSourceCodePromptBuilder:
    """Test suite for SourceCodePromptBuilder."""

    def test_build_prompt_includes_file_content(self) -> None:
        """Prompt includes the file content for context-aware validation."""
        finding = _make_finding("Payment Processing", "payment")
        file_content = """<?php
class PaymentService {
    public function processPayment($amount) {
        return $this->gateway->charge($amount);
    }
}
"""
        builder = SourceCodePromptBuilder()

        prompt = builder.build_prompt(
            [ItemGroup(items=[finding], content=file_content)]
        )

        # File content must appear in prompt for context-aware validation
        assert "PaymentService" in prompt
        assert "processPayment" in prompt
        assert "gateway->charge" in prompt

    def test_build_prompt_raises_when_content_missing(self) -> None:
        """ValueError raised when content is None (required for source code validation)."""
        finding = _make_finding("Payment Processing", "payment")
        builder = SourceCodePromptBuilder()

        with pytest.raises(ValueError, match="content is required"):
            builder.build_prompt([ItemGroup(items=[finding], content=None)])

    def test_build_prompt_raises_when_items_empty(self) -> None:
        """ValueError raised when items list is empty."""
        builder = SourceCodePromptBuilder()

        with pytest.raises(ValueError, match="At least one finding"):
            builder.build_prompt([ItemGroup(items=[], content="some content")])

    def test_build_prompt_includes_finding_ids(self) -> None:
        """Prompt includes finding IDs for response matching."""
        findings = [
            _make_finding("Payment Processing", "payment"),
            _make_finding("User Analytics", "analytics"),
        ]
        builder = SourceCodePromptBuilder()

        prompt = builder.build_prompt(
            [ItemGroup(items=findings, content="file content here")]
        )

        # Finding IDs must be in prompt for LLM response matching
        assert findings[0].id in prompt
        assert findings[1].id in prompt

    def test_build_prompt_includes_validation_mode(self) -> None:
        """Prompt includes the validation mode from constructor."""
        finding = _make_finding("Payment Processing", "payment")
        builder = SourceCodePromptBuilder(validation_mode="strict")

        prompt = builder.build_prompt(
            [ItemGroup(items=[finding], content="file content")]
        )

        assert "strict" in prompt

    def test_build_prompt_with_multiple_groups_includes_all_files(self) -> None:
        """Multiple groups produce per-file sections with all file contents and findings."""
        payment_finding = _make_finding(
            "Payment Processing", "payment", source="/src/Payment.php", line_number=10
        )
        auth_finding = _make_finding(
            "User Authentication", "auth", source="/src/Auth.php", line_number=25
        )
        builder = SourceCodePromptBuilder()

        prompt = builder.build_prompt(
            [
                ItemGroup(
                    items=[payment_finding],
                    content="class PaymentService { }",
                ),
                ItemGroup(
                    items=[auth_finding],
                    content="class AuthService { }",
                ),
            ]
        )

        # Both file sections present
        assert "Payment.php" in prompt
        assert "Auth.php" in prompt
        assert "PaymentService" in prompt
        assert "AuthService" in prompt
        # Both finding IDs present
        assert payment_finding.id in prompt
        assert auth_finding.id in prompt

    def test_build_prompt_with_multiple_groups_includes_total_finding_count(
        self,
    ) -> None:
        """Summary line reflects total findings across all groups."""
        findings_a = [
            _make_finding("Payment", "pay", source="/src/A.php"),
            _make_finding("Analytics", "analytics", source="/src/A.php"),
        ]
        findings_b = [
            _make_finding("Auth", "auth", source="/src/B.php"),
        ]
        builder = SourceCodePromptBuilder()

        prompt = builder.build_prompt(
            [
                ItemGroup(items=findings_a, content="file A"),
                ItemGroup(items=findings_b, content="file B"),
            ]
        )

        # Total is 3 findings (2 + 1)
        assert "3 findings" in prompt
