"""Tests for ISO27001PromptBuilder — prompt content verification."""

from waivern_llm import ItemGroup
from waivern_security_evidence import SecurityEvidenceModel

from waivern_iso27001_control_assessor.prompts.prompt_builder import (
    ControlContext,
    ISO27001PromptBuilder,
)

GUIDANCE_TEXT = (
    "A.8.24 Use of cryptography. Rules for the effective use of cryptography, "
    "including cryptographic key management, shall be defined and implemented."
)


def _make_builder(guidance_text: str = GUIDANCE_TEXT) -> ISO27001PromptBuilder:
    """Build a prompt builder with default A.8.24 attributes."""
    return ISO27001PromptBuilder(
        ControlContext(
            guidance_text=guidance_text,
            control_type="preventive",
            cia=["confidentiality", "integrity"],
            cybersecurity_concept="protect",
            operational_capability="system_and_network_protection",
            iso_security_domain="protection",
        )
    )


def _make_evidence(
    description: str = "AES-256 encryption used for data at rest",
    polarity: str = "positive",
    security_domain: str = "encryption",
    evidence_type: str = "CODE",
) -> SecurityEvidenceModel:
    """Build a minimal SecurityEvidenceModel for prompt testing."""
    return SecurityEvidenceModel(
        metadata={"source": "crypto.py"},
        evidence_type=evidence_type,
        security_domain=security_domain,
        polarity=polarity,
        confidence=0.9,
        description=description,
    )


def _make_group(
    items: list[SecurityEvidenceModel] | None = None,
    content: str | None = None,
) -> ItemGroup[SecurityEvidenceModel]:
    """Build an ItemGroup for prompt builder tests."""
    return ItemGroup(items=items or [], content=content)


# =============================================================================
# Prompt Content
# =============================================================================


class TestPromptContent:
    """Tests for prompt content produced by ISO27001PromptBuilder."""

    def test_prompt_includes_guidance_text(self) -> None:
        """The rule's guidance_text appears in the prompt output.

        Without guidance text the LLM does not know what the control
        requires, making verdicts meaningless.
        """
        builder = _make_builder()

        prompt = builder.build_prompt([_make_group(items=[_make_evidence()])])

        assert GUIDANCE_TEXT in prompt

    def test_prompt_includes_evidence_items(self) -> None:
        """Evidence descriptions and snippets appear in the prompt.

        Without evidence the LLM makes uninformed assessments.
        """
        builder = _make_builder()
        evidence = _make_evidence(description="bcrypt hash with cost factor 12")

        prompt = builder.build_prompt([_make_group(items=[evidence])])

        assert "bcrypt hash with cost factor 12" in prompt

    def test_prompt_includes_document_content(self) -> None:
        """Document content string appears in the prompt.

        Document evidence is the primary input for governance and
        physical controls.
        """
        builder = _make_builder()
        doc_content = "All data at rest must be encrypted using AES-256."

        prompt = builder.build_prompt([_make_group(content=doc_content)])

        assert doc_content in prompt

    def test_prompt_handles_empty_evidence_with_documents(self) -> None:
        """items=[] with content produces a valid prompt (no crash).

        Document-only controls (e.g. A.5.1) have no SecurityEvidenceModel
        items after filtering. The prompt builder must handle this gracefully
        unlike existing builders that raise ValueError on empty items.
        """
        builder = _make_builder()
        doc_content = "Information security policy document content."

        prompt = builder.build_prompt([_make_group(content=doc_content)])

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert GUIDANCE_TEXT in prompt

    def test_prompt_includes_risk_assessment_priority(self) -> None:
        """The prompt includes guidance on risk assessment prioritisation.

        Risk assessments and treatment plans have outsized impact on
        ISO 27001 control effectiveness evaluation.
        """
        builder = _make_builder()

        prompt = builder.build_prompt([_make_group()])

        assert "RISK ASSESSMENT PRIORITY" in prompt
        assert "risk treatment plan" in prompt

    def test_prompt_includes_recommended_actions_instruction(self) -> None:
        """The prompt instructs the LLM to produce recommended actions.

        Non-compliant controls need actionable remediation steps.
        """
        builder = _make_builder()

        prompt = builder.build_prompt([_make_group()])

        assert "RECOMMENDED ACTIONS" in prompt
        assert "recommended_actions" in prompt
