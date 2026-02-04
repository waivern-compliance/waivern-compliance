"""Tests for PersonalDataPromptBuilder.

Tests verify the PromptBuilder protocol implementation for personal data validation.
"""

import pytest
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail

from waivern_personal_data_analyser.prompts import PersonalDataPromptBuilder
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
)


def _make_finding(
    category: str = "email",
    pattern: str = "test@example.com",
) -> PersonalDataIndicatorModel:
    """Create a finding for testing."""
    return PersonalDataIndicatorModel(
        category=category,
        matched_patterns=[PatternMatchDetail(pattern=pattern, match_count=1)],
        evidence=[BaseFindingEvidence(content=f"Content: {pattern}")],
        metadata=PersonalDataIndicatorMetadata(source="test"),
    )


class TestPersonalDataPromptBuilder:
    """Test suite for PersonalDataPromptBuilder."""

    def test_build_prompt_includes_finding_ids_and_categories(self) -> None:
        """Prompt includes finding IDs and categories for response matching."""
        findings = [
            _make_finding("email", "test@example.com"),
            _make_finding("phone", "123-456-7890"),
        ]
        builder = PersonalDataPromptBuilder()

        prompt = builder.build_prompt(findings)

        # Finding IDs must be in prompt for response matching
        assert findings[0].id in prompt
        assert findings[1].id in prompt
        # Categories should be present
        assert "email" in prompt
        assert "phone" in prompt

    def test_build_prompt_empty_findings_raises_error(self) -> None:
        """Empty findings list raises ValueError."""
        builder = PersonalDataPromptBuilder()

        with pytest.raises(ValueError, match="At least one finding"):
            builder.build_prompt([])

    def test_build_prompt_ignores_content_parameter(self) -> None:
        """Content parameter doesn't affect output (COUNT_BASED mode)."""
        finding = _make_finding("email", "test@example.com")
        builder = PersonalDataPromptBuilder()

        prompt_without_content = builder.build_prompt([finding])
        prompt_with_content = builder.build_prompt(
            [finding], content="Some file content"
        )

        assert prompt_without_content == prompt_with_content
