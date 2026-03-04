"""Security evidence normaliser analyser."""

import importlib
import logging
from collections.abc import Callable
from typing import Literal, Protocol, TypedDict, override

from waivern_analysers_shared import SchemaReader
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import Analyser, InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_core.schemas.finding_types import BaseFindingEvidence
from waivern_crypto_quality_analyser.schemas.types import (
    CryptoQualityIndicatorModel,
    CryptoQualityIndicatorOutput,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorModel,
    PersonalDataIndicatorOutput,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeIndicatorModel,
    ProcessingPurposeIndicatorOutput,
)
from waivern_rulesets.security_evidence_domain_mapping import (
    SecurityEvidenceDomainMappingRule,
)
from waivern_security_evidence.schemas.types import (
    SecurityDomain,
    SecurityEvidenceMetadata,
    SecurityEvidenceModel,
)

from .result_builder import SecurityEvidenceResultBuilder
from .types import SecurityEvidenceNormaliserConfig

logger = logging.getLogger(__name__)

_Polarity = Literal["positive", "negative", "neutral"]


class _HasFindings[M](Protocol):
    """Structural protocol for output containers that expose a findings list."""

    findings: list[M]


class _FindingValues(TypedDict):
    """Extracted per-finding values needed to build one evidence group."""

    group_key: tuple[str, str]
    source_type: Literal["purpose", "category", "algorithm"]
    indicator_value: str
    description_label: str
    polarity: _Polarity
    require_review: bool | None
    evidence_items: list[BaseFindingEvidence]


class _EvidenceItemSpec(TypedDict):
    """Resolved attributes for a single SecurityEvidenceModel to be built."""

    source_file: str
    description: str
    polarity: _Polarity
    require_review: bool | None
    evidence_snippets: list[BaseFindingEvidence]


class SecurityEvidenceNormaliser(Analyser):
    """Normalises indicator findings into framework-agnostic security evidence.

    Consumes one indicator schema per invocation and maps each finding to a
    security domain via the security_evidence_domain_mapping ruleset. No LLM
    is required — the mapping is fully deterministic and the output is cacheable.

    Designed for multiple invocations in the runbook — once per indicator type.
    This keeps the output artifact maximally reusable via reuse: and avoids
    fan-in coupling when new indicator schemas are added in future.

    Supported input schemas (one per invocation):
    - personal_data_indicator/1.0.0
    - processing_purpose_indicator/1.0.0
    - crypto_quality_indicator/1.0.0
    """

    def __init__(self, config: SecurityEvidenceNormaliserConfig) -> None:
        """Initialise the normaliser with configuration and domain mapping rules.

        Args:
            config: Validated configuration including domain_ruleset URI.

        """
        self._config = config
        self._result_builder = SecurityEvidenceResultBuilder(config)
        self._domain_mapping_rules: tuple[SecurityEvidenceDomainMappingRule, ...] = (
            RulesetManager.get_rules(
                config.domain_ruleset, SecurityEvidenceDomainMappingRule
            )
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "security_evidence_normaliser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema alternatives.

        Each alternative is a single indicator schema — the normaliser is called
        once per indicator type in the runbook. Adding support for a new indicator
        type only requires adding a new alternative here and a corresponding
        schema reader.
        """
        return [
            [InputRequirement("personal_data_indicator", "1.0.0")],
            [InputRequirement("processing_purpose_indicator", "1.0.0")],
            [InputRequirement("crypto_quality_indicator", "1.0.0")],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this analyser can produce."""
        return [Schema("security_evidence", "1.0.0")]

    def _load_reader[T](self, schema: Schema, _output_type: type[T]) -> SchemaReader[T]:
        """Dynamically load the reader module for the given input schema version.

        The module name is derived from schema.name and schema.version at runtime,
        following the established WCF pattern. Python's import system caches modules
        in sys.modules, so repeated loads are fast without manual caching.

        Args:
            schema: Input schema to load reader for.
            _output_type: Expected output type; used only for type inference by
                the type checker — not used at runtime.

        Returns:
            Reader module with a typed read() method.

        Raises:
            ModuleNotFoundError: If no reader exists for this schema version.

        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(  # type: ignore[return-value]
            f"waivern_security_evidence_normaliser.schema_readers.{module_name}"
        )

    def _find_domain_rule(
        self,
        source_type: Literal["purpose", "category", "algorithm"],
        value: str,
    ) -> SecurityEvidenceDomainMappingRule | None:
        """Find the domain mapping rule for a given source type and indicator value.

        Args:
            source_type: Indicator schema type to match against.
            value: The indicator value to look up (purpose slug, category, or algorithm).

        Returns:
            The matching rule, or None if no rule covers this value.

        """
        for rule in self._domain_mapping_rules:
            if rule.source_type == source_type and value in rule.indicator_values:
                return rule
        return None

    def _propagate_require_review(
        self, require_review_values: list[bool | None]
    ) -> bool | None:
        """Propagate require_review from a group of findings to a single evidence item.

        Any True in the group propagates as True (per design note [8]).
        All None (no upstream flag) yields None.

        Args:
            require_review_values: require_review values from all findings in the group.

        Returns:
            True if any upstream finding requires review, else None.

        """
        if any(v is True for v in require_review_values):
            return True
        return None

    def _build_evidence_items(
        self,
        rule: SecurityEvidenceDomainMappingRule,
        spec: _EvidenceItemSpec,
    ) -> list[SecurityEvidenceModel]:
        """Build evidence items for a single rule group.

        Always produces one item for the primary domain. Produces a second item
        for the secondary_domain when the rule specifies one (e.g. sensitive
        personal data spans both data_protection and people_controls).

        Args:
            rule: Matched domain mapping rule.
            spec: Resolved attributes for the evidence item(s) to build.

        Returns:
            One or two SecurityEvidenceModel instances.

        """
        item = SecurityEvidenceModel(
            metadata=SecurityEvidenceMetadata(source=spec["source_file"]),
            evidence_type="CODE",
            security_domain=SecurityDomain(rule.security_domain),
            polarity=spec["polarity"],
            confidence=1.0,
            description=spec["description"],
            evidence=spec["evidence_snippets"],
            require_review=spec["require_review"],
        )
        items = [item]

        if rule.secondary_domain is not None:
            items.append(
                SecurityEvidenceModel(
                    metadata=SecurityEvidenceMetadata(source=spec["source_file"]),
                    evidence_type="CODE",
                    security_domain=SecurityDomain(rule.secondary_domain),
                    polarity=spec["polarity"],
                    confidence=1.0,
                    description=spec["description"],
                    evidence=spec["evidence_snippets"],
                    require_review=spec["require_review"],
                )
            )

        return items

    def _normalise[M](
        self,
        inputs: list[Message],
        output_type: type[_HasFindings[M]],
        extract: Callable[[M], _FindingValues],
    ) -> list[SecurityEvidenceModel]:
        """Normalise findings from any indicator type into security evidence items.

        Orchestrates the normalisation flow:
        1. Load and parse each input message into typed finding models
        2. Group findings by (indicator_value, source_file)
        3. For each group, find the matching domain mapping rule
        4. Build one or two evidence items per group (primary + optional secondary domain)

        Args:
            inputs: Input messages of a single indicator schema type.
            output_type: Output container type used to parse each message.
            extract: Callable that extracts normalisation values from a single finding.

        Returns:
            Normalised security evidence items.

        """
        all_findings: list[M] = []
        for msg in inputs:
            reader = self._load_reader(msg.schema, output_type)
            output = reader.read(msg.content)
            all_findings.extend(output.findings)

        groups: dict[tuple[str, str], list[_FindingValues]] = {}
        for finding in all_findings:
            values = extract(finding)
            groups.setdefault(values["group_key"], []).append(values)

        evidence_items: list[SecurityEvidenceModel] = []
        for group_key, group in groups.items():
            first = group[0]
            rule = self._find_domain_rule(
                first["source_type"], first["indicator_value"]
            )
            if rule is None:
                _, source_file = group_key
                logger.debug(
                    f"No domain mapping rule for {first['source_type']} "
                    f"'{first['indicator_value']}' "
                    f"— skipping {len(group)} finding(s) from {source_file}"
                )
                continue

            _, source_file = group_key
            require_review = self._propagate_require_review(
                [v["require_review"] for v in group]
            )
            snippets: list[BaseFindingEvidence] = []
            for v in group:
                snippets.extend(v["evidence_items"])
                if len(snippets) >= self._config.maximum_evidence_items:
                    break
            evidence_items.extend(
                self._build_evidence_items(
                    rule=rule,
                    spec=_EvidenceItemSpec(
                        source_file=source_file,
                        description=first["description_label"].format(count=len(group)),
                        polarity=first["polarity"],
                        require_review=require_review,
                        evidence_snippets=snippets[
                            : self._config.maximum_evidence_items
                        ],
                    ),
                )
            )

        return evidence_items

    def _normalise_personal_data(
        self, inputs: list[Message]
    ) -> list[SecurityEvidenceModel]:
        """Normalise personal_data_indicator findings to security evidence items.

        Groups findings by (category, source_file). Special-category data (health,
        biometric, government_id etc.) produces a second evidence item for the
        secondary_domain (people_controls) when the mapping rule specifies one.

        Args:
            inputs: personal_data_indicator messages (fan-in supported).

        Returns:
            Normalised security evidence items.

        """

        def extract(finding: PersonalDataIndicatorModel) -> _FindingValues:
            category = finding.category
            source = finding.metadata.source
            return _FindingValues(
                group_key=(category, source),
                source_type="category",
                indicator_value=category,
                description_label="{count} occurrence(s) of '"
                + category
                + "' personal data detected",
                polarity="neutral",
                require_review=finding.require_review,
                evidence_items=list(finding.evidence),
            )

        return self._normalise(inputs, PersonalDataIndicatorOutput, extract)

    def _normalise_processing_purpose(
        self, inputs: list[Message]
    ) -> list[SecurityEvidenceModel]:
        """Normalise processing_purpose_indicator findings to security evidence items.

        Groups findings by (purpose, source_file).

        Args:
            inputs: processing_purpose_indicator messages (fan-in supported).

        Returns:
            Normalised security evidence items.

        """

        def extract(finding: ProcessingPurposeIndicatorModel) -> _FindingValues:
            purpose = finding.purpose
            source = finding.metadata.source
            return _FindingValues(
                group_key=(purpose, source),
                source_type="purpose",
                indicator_value=purpose,
                description_label="{count} occurrence(s) of '"
                + purpose
                + "' processing purpose detected",
                polarity="neutral",
                require_review=finding.require_review,
                evidence_items=list(finding.evidence),
            )

        return self._normalise(inputs, ProcessingPurposeIndicatorOutput, extract)

    def _normalise_crypto_quality(
        self, inputs: list[Message]
    ) -> list[SecurityEvidenceModel]:
        """Normalise crypto_quality_indicator findings to security evidence items.

        Groups findings by (algorithm, source_file). Polarity is passed through
        directly from the finding (positive/negative — already computed by
        CryptoQualityAnalyser based on quality_rating).

        Args:
            inputs: crypto_quality_indicator messages (fan-in supported).

        Returns:
            Normalised security evidence items.

        """

        def extract(finding: CryptoQualityIndicatorModel) -> _FindingValues:
            algorithm = finding.algorithm
            source = finding.metadata.source
            return _FindingValues(
                group_key=(algorithm, source),
                source_type="algorithm",
                indicator_value=algorithm,
                description_label="{count} occurrence(s) of '"
                + algorithm
                + "' ("
                + finding.quality_rating
                + ") detected",
                polarity=finding.polarity,
                require_review=finding.require_review,
                evidence_items=list(finding.evidence),
            )

        return self._normalise(inputs, CryptoQualityIndicatorOutput, extract)

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Normalise indicator findings into security evidence items.

        Dispatches to the appropriate handler based on the input schema name.
        All inputs must share the same schema (single alternative per invocation).

        Args:
            inputs: One or more messages of the same indicator schema (fan-in).
            output_schema: Expected output schema (security_evidence/1.0.0).

        Returns:
            Output message with normalised security evidence items.

        Raises:
            ValueError: If the input schema is not supported.

        """
        input_schema_name = inputs[0].schema.name

        match input_schema_name:
            case "personal_data_indicator":
                findings = self._normalise_personal_data(inputs)
            case "processing_purpose_indicator":
                findings = self._normalise_processing_purpose(inputs)
            case "crypto_quality_indicator":
                findings = self._normalise_crypto_quality(inputs)
            case _:
                msg = (
                    f"Unsupported input schema '{input_schema_name}'. "
                    "Expected one of: personal_data_indicator, "
                    "processing_purpose_indicator, crypto_quality_indicator"
                )
                raise ValueError(msg)

        return self._result_builder.build_output_message(findings, output_schema)
