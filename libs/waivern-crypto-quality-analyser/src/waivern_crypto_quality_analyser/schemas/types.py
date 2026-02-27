"""Schema data models for crypto quality indicator findings."""

from typing import ClassVar, Literal, override

from pydantic import BaseModel, Field
from waivern_core.schemas import (
    BaseAnalysisOutputMetadata,
    BaseFindingMetadata,
    BaseFindingModel,
    BaseSchemaOutput,
)


class CryptoQualityIndicatorMetadata(BaseFindingMetadata):
    """Metadata for crypto quality indicator findings.

    Extends BaseFindingMetadata which provides:
    - source: str - Source file or location where the algorithm was found
    - context: dict[str, object] - Extensible context for pipeline metadata
    """

    pass


class CryptoQualityIndicatorModel(BaseFindingModel[CryptoQualityIndicatorMetadata]):
    """Crypto quality indicator finding structure.

    Captures a single cryptographic algorithm usage in source code and
    assigns a quality rating and polarity. Polarity is set by the pattern
    matcher at construction time based on quality_rating:
        strong     → positive
        weak       → negative
        deprecated → negative

    Inherits from BaseFindingModel[CryptoQualityIndicatorMetadata] which provides:
    - id: str - Unique identifier (auto-generated UUID)
    - evidence: list[BaseFindingEvidence] - Evidence items with context
    - matched_patterns: list[PatternMatchDetail] - Patterns that matched
    - metadata: CryptoQualityIndicatorMetadata - Required metadata with source
    - require_review: bool | None - Whether this finding requires human review
    """

    algorithm: str = Field(
        description="Canonical algorithm name (e.g., 'md5', 'bcrypt')"
    )
    quality_rating: Literal["strong", "weak", "deprecated"] = Field(
        description="Cryptographic quality rating of the detected algorithm"
    )
    polarity: Literal["positive", "negative"] = Field(
        description=(
            "Evidence polarity derived from quality_rating: "
            "strong → positive, weak/deprecated → negative"
        )
    )

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging and debugging."""
        return f"{self.algorithm} ({self.quality_rating}/{self.polarity})"


class CryptoQualityIndicatorSummary(BaseModel):
    """Summary statistics for crypto quality indicator findings."""

    total_findings: int = Field(
        ge=0, description="Total number of crypto quality indicators found"
    )


class CryptoQualityIndicatorOutput(BaseSchemaOutput):
    """Complete output structure for crypto_quality_indicator schema.

    Represents the full wire format for crypto quality indicator results.
    These indicators feed directly into SecurityEvidenceNormaliser, which
    maps them to security_evidence items with polarity for gap analysis.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    findings: list[CryptoQualityIndicatorModel] = Field(
        description="List of cryptographic algorithm quality indicators found"
    )
    summary: CryptoQualityIndicatorSummary = Field(
        description="Summary statistics of the crypto quality analysis"
    )
    analysis_metadata: BaseAnalysisOutputMetadata = Field(
        description="Metadata about the analysis process"
    )
