"""ISO 27001 control assessor."""

import logging
from collections.abc import Sequence
from typing import Any, override

from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import Analyser, InputRequirement
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BatchingMode, ItemGroup, LLMService
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_rulesets.iso27001_domains import ISO27001DomainsRule
from waivern_schemas.iso27001_assessment import (
    AssessmentVerdict,
    ControlStatus,
    EvidenceStatus,
)
from waivern_schemas.security_document_context import SecurityDocumentContextModel
from waivern_schemas.security_evidence import SecurityEvidenceModel

from .prompts.prompt_builder import ControlContext, ISO27001PromptBuilder
from .prompts.response_model import ISO27001LLMResponse
from .result_builder import ISO27001ResultBuilder
from .types import ISO27001AssessorConfig, ISO27001PrepareState

logger = logging.getLogger(__name__)


class ISO27001Assessor(Analyser):
    """Assessor for individual ISO 27001 controls.

    Each instance assesses exactly one control (identified by control_ref).
    Receives security evidence and optional document context as inputs,
    filters by security domain, derives evidence_status, and calls the
    LLM to produce a structured assessment verdict.

    Two input alternatives are supported:
    1. security_evidence + security_document_context (full assessment)
    2. security_evidence only (attestation-required controls emit not_assessed)
    """

    def __init__(
        self,
        config: ISO27001AssessorConfig,
        llm_service: LLMService | None = None,
    ) -> None:
        """Initialise the assessor with dependency injection.

        Args:
            config: Validated configuration with control_ref and ruleset URI.
            llm_service: LLM service for standalone ``process()`` fallback.
                Pass ``None`` for LLM-disabled mode (degraded output only).

        """
        self._config = config
        self._llm_service = llm_service
        self._result_builder = ISO27001ResultBuilder(config.domain_ruleset)

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the assessor."""
        return "iso27001_assessor"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        Two alternatives:
        1. Both security_evidence and security_document_context (full pipeline)
        2. security_evidence only (no document context available yet)

        The first alternative is preferred when document context is available.
        The second allows technical-only assessment where evidence-required
        controls emit requires_attestation status.
        """
        return [
            [
                InputRequirement("security_evidence", "1.0.0"),
                InputRequirement("security_document_context", "1.0.0"),
            ],
            [InputRequirement("security_evidence", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this assessor can produce."""
        return [Schema("iso27001_assessment", "1.0.0")]

    # ── DistributedProcessor ────────���────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[ISO27001PrepareState]:
        """Analyse inputs and declare LLM dispatch needs.

        1. Validate inputs and extract run_id
        2. Load matching rule and filter evidence by domain/evidence_source
        3. Derive evidence_status from filtered evidence
        4. If AUTOMATED and LLM enabled, build LLMRequest; otherwise empty requests

        """
        if not inputs:
            raise ValueError("No input messages provided")
        run_id = inputs[0].run_id
        if not run_id:
            raise ValueError(
                f"Missing run_id on input for control '{self._config.control_ref}'"
            )

        rule = self._load_rule()
        evidence, documents = self._partition_and_filter(inputs, rule)
        evidence_status = self._derive_evidence_status(rule, evidence, documents)
        llm_enabled = self._llm_service is not None

        requests: list[DispatchRequest] = []
        if evidence_status == EvidenceStatus.AUTOMATED and llm_enabled:
            requests.append(self._build_llm_request(rule, evidence, documents, run_id))

        return PrepareResult(
            state=ISO27001PrepareState(
                rule=rule,
                evidence_status=evidence_status,
                evidence=evidence,
                documents=documents,
                run_id=run_id,
                llm_enabled=llm_enabled,
            ),
            requests=requests,
        )

    def _build_llm_request(
        self,
        rule: ISO27001DomainsRule,
        evidence: list[SecurityEvidenceModel],
        documents: list[SecurityDocumentContextModel],
        run_id: str,
    ) -> LLMRequest[SecurityEvidenceModel]:
        """Build an LLMRequest for automated assessment."""
        doc_content = self._format_document_content(documents)
        control = ControlContext(
            guidance_text=rule.guidance_text,
            control_type=rule.control_type,
            cia=list(rule.cia),
            cybersecurity_concept=rule.cybersecurity_concept,
            operational_capability=rule.operational_capability,
            iso_security_domain=rule.iso_security_domain,
        )

        return LLMRequest(
            name=f"assessment:{rule.control_ref}",
            groups=[
                ItemGroup(
                    items=evidence,
                    content=doc_content,
                    group_id=rule.control_ref,
                )
            ],
            prompt_builder=ISO27001PromptBuilder(control),
            response_model=ISO27001LLMResponse,
            batching_mode=BatchingMode.INDEPENDENT,
            run_id=run_id,
        )

    def finalise(
        self,
        state: ISO27001PrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> Message:
        """Produce assessment verdict from state and dispatch results.

        1. Short-circuit paths (empty results): build NOT_ASSESSED from evidence_status
        2. AUTOMATED + LLM result: parse response and build verdict
        3. AUTOMATED + empty LLM responses: evidence exceeded context window

        """
        rule = state.rule

        match state.evidence_status:
            case EvidenceStatus.INSUFFICIENT_EVIDENCE:
                return self._result_builder.build_output_message(
                    rule,
                    verdict=AssessmentVerdict(
                        status=ControlStatus.NOT_ASSESSED,
                        evidence_status=state.evidence_status,
                        rationale=(
                            "No relevant evidence found. Neither technical findings "
                            "nor document context matched this control's security "
                            "domains."
                        ),
                        gap_description=None,
                    ),
                    llm_enabled=False,
                    output_schema=output_schema,
                )
            case EvidenceStatus.REQUIRES_ATTESTATION:
                return self._result_builder.build_output_message(
                    rule,
                    verdict=AssessmentVerdict(
                        status=ControlStatus.NOT_ASSESSED,
                        evidence_status=state.evidence_status,
                        rationale=(
                            "Awaiting document evidence. This control requires "
                            "human-produced documentation (e.g. policy, procedure, "
                            "inspection report) that has not yet been provided."
                        ),
                        gap_description=None,
                    ),
                    llm_enabled=False,
                    output_schema=output_schema,
                )
            case EvidenceStatus.AUTOMATED if not state.llm_enabled:
                return self._result_builder.build_output_message(
                    rule,
                    verdict=AssessmentVerdict(
                        status=ControlStatus.NOT_ASSESSED,
                        evidence_status=state.evidence_status,
                        rationale=(
                            "LLM assessment not available. Evidence was sufficient "
                            "for automated assessment but LLM service is not "
                            "configured."
                        ),
                        gap_description=None,
                    ),
                    llm_enabled=False,
                    output_schema=output_schema,
                )
            case EvidenceStatus.AUTOMATED:
                return self._finalise_llm_result(rule, results, output_schema)

    def _finalise_llm_result(
        self,
        rule: ISO27001DomainsRule,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> Message:
        """Interpret LLM dispatch results into an assessment verdict."""
        for result in results:
            match result:
                case LLMDispatchResult() as llm_result:
                    if not llm_result.responses:
                        return self._result_builder.build_output_message(
                            rule,
                            verdict=AssessmentVerdict(
                                status=ControlStatus.NOT_ASSESSED,
                                evidence_status=EvidenceStatus.AUTOMATED,
                                rationale=(
                                    "LLM assessment skipped — evidence "
                                    "exceeded context window."
                                ),
                                gap_description=None,
                            ),
                            llm_enabled=False,
                            output_schema=output_schema,
                        )

                    llm_response = ISO27001LLMResponse.model_validate(
                        llm_result.responses[0]
                    )
                    return self._result_builder.build_output_message(
                        rule,
                        verdict=AssessmentVerdict(
                            status=ControlStatus(llm_response.status),
                            evidence_status=EvidenceStatus.AUTOMATED,
                            rationale=llm_response.rationale,
                            gap_description=llm_response.gap_description,
                            recommended_actions=llm_response.recommended_actions,
                        ),
                        llm_enabled=True,
                        output_schema=output_schema,
                    )
                case _:
                    continue

        # No LLMDispatchResult found — unexpected but handle gracefully
        return self._result_builder.build_output_message(
            rule,
            verdict=AssessmentVerdict(
                status=ControlStatus.NOT_ASSESSED,
                evidence_status=EvidenceStatus.AUTOMATED,
                rationale="No LLM dispatch result received.",
                gap_description=None,
            ),
            llm_enabled=False,
            output_schema=output_schema,
        )

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[ISO27001PrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. Handles LLMRequest reconstruction with correct field types.

        """
        state = ISO27001PrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[SecurityEvidenceModel].model_validate(r)
            for r in raw.get("requests", [])
        ]
        return PrepareResult(state=state, requests=requests)

    # ── Processor (standalone fallback) ──────────────────────────────────

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Standalone fallback producing degraded (LLM-disabled) output.

        Delegates to prepare/finalise with LLM forced off. In the executor,
        the DistributedProcessor path is always used instead. This method
        exists to satisfy the Processor abstract contract.

        """
        prepare_result = self.prepare(inputs, output_schema)
        state = prepare_result.state.model_copy(update={"llm_enabled": False})
        result = self.finalise(state, [], output_schema)
        # finalise() with llm_enabled=False always returns Message (no multi-round)
        return result  # pyright: ignore[reportReturnType]

    # ── Private helpers ─────────────────────────────────────────────────

    def _load_rule(self) -> ISO27001DomainsRule:
        """Load the matching rule from the iso27001_domains ruleset."""
        ruleset = RulesetManager.get_ruleset(
            self._config.domain_ruleset, ISO27001DomainsRule
        )
        for rule in ruleset.get_rules():
            if rule.control_ref == self._config.control_ref:
                return rule
        raise ValueError(
            f"No rule found for control_ref '{self._config.control_ref}' "
            f"in ruleset '{self._config.domain_ruleset}'"
        )

    def _partition_and_filter(
        self,
        inputs: list[Message],
        rule: ISO27001DomainsRule,
    ) -> tuple[list[SecurityEvidenceModel], list[SecurityDocumentContextModel]]:
        """Partition inputs by schema, extract findings, and apply filters.

        1. Separate messages into security_evidence and document_context groups
        2. Extract typed findings from each group
        3. Filter security_evidence by domain intersection
        4. Apply evidence_source filter (drop technical if not accepted, etc.)
        5. Filter document_context by domain intersection (cross-cutting always pass)

        """
        raw_evidence: list[SecurityEvidenceModel] = []
        raw_documents: list[SecurityDocumentContextModel] = []

        for message in inputs:
            match message.schema.name:
                case "security_evidence":
                    for item in message.content["findings"]:
                        raw_evidence.append(SecurityEvidenceModel.model_validate(item))
                case "security_document_context":
                    for item in message.content["findings"]:
                        raw_documents.append(
                            SecurityDocumentContextModel.model_validate(item)
                        )
                case _:
                    logger.warning(
                        "Unexpected input schema '%s' — skipping",
                        message.schema.name,
                    )

        rule_domains = set(rule.security_domains)

        # Domain filter on security_evidence
        evidence = [e for e in raw_evidence if e.security_domain in rule_domains]

        # Evidence source filter
        if "TECHNICAL" not in rule.evidence_source:
            evidence = []
        if "DOCUMENT" not in rule.evidence_source:
            raw_documents = [d for d in raw_documents if not d.security_domains]

        # Domain filter on document_context (cross-cutting always passes)
        documents = [
            d
            for d in raw_documents
            if not d.security_domains or set(d.security_domains) & rule_domains
        ]

        return evidence, documents

    def _derive_evidence_status(
        self,
        rule: ISO27001DomainsRule,
        evidence: list[SecurityEvidenceModel],
        documents: list[SecurityDocumentContextModel],
    ) -> EvidenceStatus:
        """Derive evidence_status from the filtered evidence.

        Decision tree:
        1. evidence_required set and any required type missing → requires_attestation
        2. Any evidence item has require_review=True → requires_attestation
        3. No evidence and no documents → insufficient_evidence
        4. Otherwise → automated

        """
        if rule.evidence_required:
            has_technical = len(evidence) > 0
            has_document = len(documents) > 0
            type_present = {"TECHNICAL": has_technical, "DOCUMENT": has_document}
            for required_type in rule.evidence_required:
                if not type_present.get(required_type, False):
                    return EvidenceStatus.REQUIRES_ATTESTATION

        if any(e.require_review is True for e in evidence):
            return EvidenceStatus.REQUIRES_ATTESTATION

        if not evidence and not documents:
            return EvidenceStatus.INSUFFICIENT_EVIDENCE

        return EvidenceStatus.AUTOMATED

    def _format_document_content(
        self,
        documents: list[SecurityDocumentContextModel],
    ) -> str:
        """Format document context items into a single content string.

        Concatenates document text with filename headers for the LLM prompt.
        Always returns a non-empty string (includes a placeholder when no
        documents are available) so the ItemGroup.content is never None.

        Args:
            documents: Filtered document context items.

        Returns:
            Formatted document content string.

        """
        if not documents:
            return "No document context available for this control."

        parts: list[str] = []
        for doc in documents:
            parts.append(f"--- {doc.filename} ---\n{doc.summary}")
        return "\n\n".join(parts)
