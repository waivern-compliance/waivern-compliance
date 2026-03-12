"""Security document evidence extractor processor."""

import asyncio
import importlib
import logging
from typing import override

from waivern_analysers_shared import SchemaReader
from waivern_core import InputRequirement, Processor
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BatchingMode, ItemGroup, LLMService

from .prompts.prompt_builder import DomainClassificationPromptBuilder
from .result_builder import build_output_message
from .schemas.types import SecurityDocumentContextMetadata
from .types import (
    DocumentItem,
    DomainClassificationResponse,
    SecurityDocumentEvidenceExtractorConfig,
)

logger = logging.getLogger(__name__)


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
            llm_service: LLM service for domain classification (injected by factory).

        """
        self._config = config
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

    def _load_reader(
        self, schema: Schema
    ) -> SchemaReader[StandardInputDataModel[BaseMetadata]]:
        """Dynamically import reader module.

        Args:
            schema: Input schema to load reader for.

        Returns:
            Reader module with typed read() function.

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(  # type: ignore[return-value]
            f"waivern_security_document_evidence_extractor.schema_readers.{module_name}"
        )

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process policy documents and classify by security domain.

        Orchestrates the complete flow:
        1. Parse input messages via schema reader (merge fan-in)
        2. Create DocumentItem + ItemGroup per document
        3. If LLM enabled: classify via LLMService.complete()
        4. If LLM disabled: assign [] to all documents
        5. Build output message via result builder

        Args:
            inputs: Input messages containing document text (standard_input/1.0.0).
            output_schema: Output schema for validation.

        Returns:
            Message with security_document_context/1.0.0 content.

        """
        # 1. Parse and merge inputs
        data_items = self._merge_input_data_items(inputs)
        logger.info(f"Processing {len(data_items)} documents for domain classification")

        # 2. Create DocumentItem + content pairs
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

        # 3/4. Classify
        if self._config.enable_llm_classification and self._llm_service:
            responses = self._classify_with_llm(document_items, document_contents)
        else:
            responses = [
                DomainClassificationResponse(security_domains=[])
                for _ in document_items
            ]

        # 5. Build output
        return build_output_message(
            document_items=document_items,
            document_contents=document_contents,
            responses=responses,
            output_schema=output_schema,
            llm_classification_enabled=self._config.enable_llm_classification,
        )

    def _merge_input_data_items(
        self,
        inputs: list[Message],
    ) -> list[StandardInputDataItemModel[BaseMetadata]]:
        """Merge data items from multiple input messages (fan-in).

        Args:
            inputs: List of input messages with same schema.

        Returns:
            Flattened list of all data items from all inputs.

        """
        all_data_items: list[StandardInputDataItemModel[BaseMetadata]] = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            input_data = reader.read(message.content)
            all_data_items.extend(input_data.data)
        return all_data_items

    def _classify_with_llm(
        self,
        document_items: list[DocumentItem],
        document_contents: list[str],
    ) -> list[DomainClassificationResponse]:
        """Classify documents using LLM service.

        Args:
            document_items: Document items for LLM grouping.
            document_contents: Full text of each document.

        Returns:
            List of classification responses (one per document).

        """
        assert self._llm_service is not None  # noqa: S101

        groups = [
            ItemGroup(items=[item], content=content, group_id=item.metadata.source)
            for item, content in zip(document_items, document_contents, strict=True)
        ]

        run_id = "domain-classification"
        prompt_builder = DomainClassificationPromptBuilder()

        result = asyncio.run(
            self._llm_service.complete(
                groups,
                prompt_builder=prompt_builder,
                response_model=DomainClassificationResponse,
                batching_mode=BatchingMode.INDEPENDENT,
                run_id=run_id,
            )
        )

        return result.responses
