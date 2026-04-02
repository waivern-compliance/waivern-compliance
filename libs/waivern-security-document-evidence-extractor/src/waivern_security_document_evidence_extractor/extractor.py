"""Security document evidence extractor processor."""

import importlib
from collections.abc import Sequence
from typing import Any, override

from waivern_analysers_shared import SchemaReader
from waivern_core import InputRequirement, Processor
from waivern_core.dispatch import DispatchRequest, DispatchResult, PrepareResult
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_llm import BatchingMode, ItemGroup, LLMService
from waivern_llm.types import LLMDispatchResult, LLMRequest
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.security_document_context import SecurityDocumentContextMetadata
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from .prompts.prompt_builder import DomainClassificationPromptBuilder
from .result_builder import build_output_message
from .types import (
    DocumentItem,
    DomainClassificationResponse,
    SecurityDocEvidencePrepareState,
    SecurityDocumentEvidenceExtractorConfig,
)


class SecurityDocumentEvidenceExtractor(Processor):
    """Classifies policy documents by security domain using LLM analysis.

    Receives standard_input/1.0.0 (from filesystem connector) containing
    policy document text, calls the LLM to classify which SecurityDomain
    values apply, and emits security_document_context/1.0.0.
    """

    def __init__(
        self,
        config: SecurityDocumentEvidenceExtractorConfig,
        llm_service: LLMService | None = None,
    ) -> None:
        """Initialise the extractor with dependency injection.

        Args:
            config: Validated configuration object.
            llm_service: LLM service for domain classification.
                Pass ``None`` for LLM-disabled mode (degraded output only).

        """
        self._llm_service = llm_service

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the processor."""
        return "security_document_evidence_extractor"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations."""
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this processor can produce."""
        return [Schema("security_document_context", "1.0.0")]

    # ── DistributedProcessor ─────────────────────────────────────────────

    def prepare(
        self, inputs: list[Message], output_schema: Schema
    ) -> PrepareResult[SecurityDocEvidencePrepareState]:
        """Analyse inputs and declare LLM dispatch needs.

        1. Validate inputs and extract run_id
        2. Parse and merge input data items (fan-in)
        3. Create DocumentItem + content pairs
        4. If LLM enabled, build LLMRequest; otherwise empty requests

        """
        if not inputs:
            raise ValueError("No input messages provided")
        run_id = inputs[0].run_id
        if not run_id:
            raise ValueError("run_id is required but not set on input messages")

        data_items = self._merge_input_data_items(inputs)
        document_items, document_contents = self._build_document_pairs(data_items)
        llm_enabled = self._llm_service is not None

        requests: list[DispatchRequest] = []
        if llm_enabled:
            requests.append(
                self._build_llm_request(document_items, document_contents, run_id)
            )

        return PrepareResult(
            state=SecurityDocEvidencePrepareState(
                document_items=document_items,
                document_contents=document_contents,
                llm_enabled=llm_enabled,
                run_id=run_id,
            ),
            requests=requests,
        )

    def _build_llm_request(
        self,
        document_items: list[DocumentItem],
        document_contents: list[str],
        run_id: str,
    ) -> LLMRequest[DocumentItem]:
        """Build an LLMRequest for domain classification."""
        groups = [
            ItemGroup(items=[item], content=content, group_id=item.metadata.source)
            for item, content in zip(document_items, document_contents, strict=True)
        ]
        return LLMRequest(
            name="classification",
            groups=groups,
            prompt_builder=DomainClassificationPromptBuilder(),
            response_model=DomainClassificationResponse,
            batching_mode=BatchingMode.INDEPENDENT,
            run_id=run_id,
        )

    def finalise(
        self,
        state: SecurityDocEvidencePrepareState,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> Message:
        """Produce classified document output from state and dispatch results.

        1. If LLM disabled: generate default responses (empty domains, content as summary)
        2. If LLM result with responses: validate as DomainClassificationResponse
        3. If LLM result with empty responses: fall back to defaults

        """
        if not state.llm_enabled:
            responses = self._build_default_responses(state.document_contents)
        else:
            responses = self._extract_llm_responses(state, results)

        return build_output_message(
            document_items=state.document_items,
            document_contents=state.document_contents,
            responses=responses,
            output_schema=output_schema,
            llm_classification_enabled=state.llm_enabled,
        )

    def _extract_llm_responses(
        self,
        state: SecurityDocEvidencePrepareState,
        results: Sequence[DispatchResult],
    ) -> list[DomainClassificationResponse]:
        """Extract classification responses from LLM dispatch results."""
        for result in results:
            match result:
                case LLMDispatchResult() as llm_result:
                    if not llm_result.responses:
                        return self._build_default_responses(state.document_contents)
                    return [
                        DomainClassificationResponse.model_validate(r)
                        for r in llm_result.responses
                    ]
                case _:
                    continue

        return self._build_default_responses(state.document_contents)

    def _build_default_responses(
        self,
        document_contents: list[str],
    ) -> list[DomainClassificationResponse]:
        """Build default responses for degraded mode (no LLM)."""
        return [
            DomainClassificationResponse(security_domains=[], summary=content)
            for content in document_contents
        ]

    def deserialise_prepare_result(
        self, raw: dict[str, Any]
    ) -> PrepareResult[SecurityDocEvidencePrepareState]:
        """Reconstruct a typed PrepareResult from a raw dict.

        Called on the resume path where a persisted PrepareResult must be
        restored. Handles LLMRequest reconstruction with correct field types.

        """
        state = SecurityDocEvidencePrepareState.model_validate(raw["state"])
        requests: list[DispatchRequest] = [
            LLMRequest[DocumentItem].model_validate(r) for r in raw.get("requests", [])
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
        the DistributedProcessor path is always used instead.

        """
        prepare_result = self.prepare(inputs, output_schema)
        state = prepare_result.state.model_copy(update={"llm_enabled": False})
        return self.finalise(state, [], output_schema)

    # ── Private helpers ──────────────────────────────────────────────────

    def _load_reader(
        self, schema: Schema
    ) -> SchemaReader[StandardInputDataModel[BaseMetadata]]:
        """Dynamically import reader module."""
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(  # type: ignore[return-value]
            f"waivern_security_document_evidence_extractor.schema_readers.{module_name}"
        )

    def _merge_input_data_items(
        self,
        inputs: list[Message],
    ) -> list[StandardInputDataItemModel[BaseMetadata]]:
        """Merge data items from multiple input messages (fan-in)."""
        all_data_items: list[StandardInputDataItemModel[BaseMetadata]] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            input_data = reader.read(message.content)
            all_data_items.extend(input_data.data)
        return all_data_items

    def _build_document_pairs(
        self,
        data_items: list[StandardInputDataItemModel[BaseMetadata]],
    ) -> tuple[list[DocumentItem], list[str]]:
        """Create DocumentItem and content pairs from input data items."""
        document_items: list[DocumentItem] = []
        document_contents: list[str] = []
        for item in data_items:
            document_items.append(
                DocumentItem(
                    metadata=SecurityDocumentContextMetadata(
                        source=item.metadata.source,
                    ),
                )
            )
            document_contents.append(item.content)
        return document_items, document_contents
