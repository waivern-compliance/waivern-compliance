"""Analysis result data classes for WCT."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wct.organisation import OrganisationConfig, OrganisationLoader
from wct.runbook import RunbookLoader


class AnalysisMetadata(BaseModel):
    """Metadata for analysis results.

    This model provides a extensible structure for metadata that can be
    extended in the future for specific metadata types.
    """

    model_config = ConfigDict(extra="allow")


class AnalysisResult(BaseModel):
    """Result from an analyser analysis."""

    analysis_name: str = Field(description="Name of the analysis")
    analysis_description: str = Field(description="Description of the analysis")
    input_schema: str = Field(description="Input schema name")
    output_schema: str = Field(description="Output schema name")
    data: dict[str, Any] = Field(description="Analysis result data")
    metadata: AnalysisMetadata | None = Field(
        default=None, description="Optional metadata for the analysis"
    )
    success: bool = Field(description="Whether the analysis was successful")
    contact: str | None = Field(
        default=None, description="Contact information for the analysis"
    )
    error_message: str | None = Field(
        default=None, description="Error message if analysis failed"
    )


class AnalysisResultsExporter:
    """Handles exporting analysis results to various formats."""

    @staticmethod
    def save_to_json(
        results: list[AnalysisResult],
        output_path: Path,
        runbook_path: Path | None = None,
        organisation_config: OrganisationConfig | None = None,
    ) -> None:
        """Save analysis results to a JSON file.

        Args:
            results: List of analysis results to save
            output_path: Path where the JSON file should be saved
            runbook_path: Optional path to the runbook file for metadata
            organisation_config: Optional organisation config for GDPR Article 30(1)(a) compliance

        Raises:
            IOError: If the file cannot be written

        """
        # Extract runbook contact if runbook_path is provided
        runbook_contact = AnalysisResultsExporter._extract_runbook_contact(runbook_path)

        # Create comprehensive output structure
        export_metadata = {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "successful_results": sum(1 for r in results if r.success),
            "failed_results": sum(1 for r in results if not r.success),
            "runbook_path": str(runbook_path) if runbook_path else None,
            "runbook_contact": runbook_contact,
            "export_format_version": "1.0.0",
        }

        # Add organisation metadata for GDPR Article 30(1)(a) compliance
        AnalysisResultsExporter._add_organisation_metadata(
            export_metadata, organisation_config
        )

        output_data = {
            "export_metadata": export_metadata,
            "results": [
                result.model_dump(exclude_defaults=True, exclude_none=True)
                for result in results
            ],
        }

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON file with pretty formatting
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def _add_organisation_metadata(
        cls,
        export_metadata: dict[str, Any],
        organisation_config: OrganisationConfig | None,
    ) -> None:
        """Add organisation metadata to export for GDPR Article 30(1)(a) compliance.

        Args:
            export_metadata: Export metadata dictionary to update
            organisation_config: Organisation config, or None to load from project

        """
        logger = logging.getLogger(__name__)

        # Load organisation config if not provided
        if organisation_config is None:
            organisation_config = OrganisationLoader.load()

        # Add organisation information for GDPR Article 30(1)(a) compliance
        if organisation_config:
            export_metadata["organisation"] = organisation_config.to_export_metadata()
            logger.info(
                f"Including organisation metadata for GDPR Article 30(1)(a) compliance: "
                f"{organisation_config.data_controller.name}"
            )
        else:
            logger.warning(
                "No organisation configuration found. Analysis export will not include "
                "data controller information required for GDPR Article 30(1)(a) compliance. "
                "Consider adding config/organisation.yaml to your project."
            )

    @staticmethod
    def _extract_runbook_contact(runbook_path: Path | None) -> str | None:
        """Extract contact information from runbook file.

        Args:
            runbook_path: Path to runbook file, or None

        Returns:
            Contact string if found in runbook, None otherwise

        """
        if not runbook_path:
            return None

        try:
            runbook = RunbookLoader.load(runbook_path)
            return runbook.contact
        except Exception:
            # If runbook can't be loaded, contact remains None
            return None

    @staticmethod
    def get_summary_stats(results: list[AnalysisResult]) -> dict[str, Any]:
        """Get summary statistics from analysis results.

        Args:
            results: List of analysis results

        Returns:
            Dictionary containing summary statistics

        """
        if not results:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "analysers": [],
                "schemas": {"input": [], "output": []},
            }

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        return {
            "total": len(results),
            "successful": len(successful_results),
            "failed": len(failed_results),
            "success_rate": len(successful_results) / len(results) * 100,
            "analysers": list(set(r.analysis_name for r in results)),
            "schemas": {
                "input": list(set(r.input_schema for r in results)),
                "output": list(set(r.output_schema for r in results)),
            },
            "error_summary": [
                {"analyser": r.analysis_name, "error": r.error_message}
                for r in failed_results
            ]
            if failed_results
            else [],
        }
