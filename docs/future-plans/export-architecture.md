# Export Architecture Design

- **Status:** Partially Implemented (Core infrastructure complete, framework-specific exporters pending)
- **Last Updated:** 2025-12-30
- **Related:** [Multi-Schema Fan-In](./multi-schema-fan-in.md), [Artifact-Centric Runbook](./artifact-centric-runbook.md), [Export Re-Export Command](./export-re-export-command.md), [Regulatory Framework Architecture](./regulatory-framework-architecture.md)

## Overview

This document describes the export architecture for WCF, enabling regulation-specific output formats with organisation metadata. Exporters transform execution results into compliance-ready documents.

## Problem

The current system produces generic JSON output with execution results. Compliance use cases require:

1. **Regulation-specific formatting** - GDPR RoPA has different structure than CCPA disclosures
2. **Organisation metadata** - Controller info, DPO details, jurisdiction data
3. **Multiple output formats** - Same analysis, different regulatory presentations
4. **Re-export capability** - Generate new formats without re-running analysis

## Design Principles

1. **Exporters are presentation layer** - They format, not analyse
2. **Runbooks declare framework** - The regulatory framework is declared at the runbook root level via the `framework` field
3. **Framework-based exporter selection** - Exporter is selected based on `runbook.framework`
4. **CLI can override** - Flexibility for one-off needs
5. **Separation of concerns** - Framework produces findings, app formats output

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION (waivern-orchestration)            │
│                                                                 │
│  Planner → DAGExecutor → ExecutionResult                        │
│                              │                                  │
│                              │ Contains:                        │
│                              │ - Artifact results (Messages)    │
│                              │ - Success/failure status         │
│                              │ - Timing information             │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EXPORT (apps/wct)                          │
│                                                                 │
│  ExporterRegistry                                               │
│    ├── JsonExporter (default)                                   │
│    ├── GdprExporter                                             │
│    └── CcpaExporter (future)                                    │
│                                                                 │
│  Each exporter:                                                 │
│    1. Validates result contains required schemas                │
│    2. Formats output according to regulation                    │
│    3. Merges organisation metadata                              │
│    4. Produces final document                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Runbook Framework Declaration

The regulatory framework is declared at the runbook root level:

```yaml
name: "GDPR Compliance Analysis"
description: "Personal data and processing purpose analysis"
framework: "GDPR"  # Declares the regulatory context

artifacts:
  # ... artifact definitions
```

### Exporter Selection

The exporter is selected based on the runbook's `framework` field:

```
Runbook parsed
       │
       ▼
Read runbook.framework
       │
       ▼
Select matching exporter (or JSON if not set)
```

**Selection logic:**
- Framework declared → use matching exporter (e.g., `GDPR` → `gdpr` exporter)
- No framework declared → use JSON exporter
- CLI `--exporter` flag → overrides automatic selection

## Exporter Protocol

```python
# apps/wct/src/wct/exporters/protocol.py

from typing import Any, Protocol
from waivern_orchestration import ExecutionPlan, ExecutionResult
from wct.organisation import OrganisationConfig

class Exporter(Protocol):
    """Protocol for compliance exporters."""

    @property
    def name(self) -> str:
        """Exporter identifier (e.g., 'json', 'gdpr', 'ccpa')."""
        ...

    @property
    def supported_frameworks(self) -> list[str]:
        """Compliance frameworks this exporter handles.

        Returns:
            Empty list: Generic exporter (handles any framework)
            Non-empty: Only these frameworks (e.g., ["GDPR", "UK_GDPR"])
        """
        ...

    def validate(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> list[str]:
        """Validate that result meets exporter requirements.

        Each exporter implements its own validation logic to check
        that the ExecutionResult contains the necessary data.

        Args:
            result: Execution result to validate
            plan: Execution plan with artifact definitions

        Returns:
            List of validation errors (empty if valid)
        """
        ...

    def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Export execution results to structured format.

        Args:
            result: Execution results with artifact data
            plan: Execution plan with runbook metadata

        Returns:
            Export dictionary ready for JSON serialisation

        Note:
            Organisation configuration is passed at exporter initialization
            for framework-specific exporters (e.g., GdprExporter), not at
            export time. This enables proper dependency injection and cleaner
            exporter design.
        """
        ...
```

## Exporter Registry

```python
# apps/wct/src/wct/exporters/registry.py

class ExporterRegistry:
    """Registry for exporters."""

    _exporters: dict[str, Exporter] = {}

    @classmethod
    def register(cls, exporter: Exporter) -> None:
        """Register an exporter."""
        cls._exporters[exporter.name] = exporter

    @classmethod
    def get(cls, name: str) -> Exporter:
        """Get exporter by name."""
        if name not in cls._exporters:
            available = list(cls._exporters.keys())
            raise ValueError(
                f"Unknown exporter '{name}'. Available: {available}"
            )
        return cls._exporters[name]

    @classmethod
    def list_exporters(cls) -> list[str]:
        """List available exporter names."""
        return list(cls._exporters.keys())
```

## Core JSON Exporter

```python
# apps/wct/src/wct/exporters/json_exporter.py

from wct.exporters.core import build_core_export

class JsonExporter:
    """Generic JSON exporter - formats any framework."""

    @property
    def name(self) -> str:
        return "json"

    @property
    def supported_frameworks(self) -> list[str]:
        return []  # Any framework (generic)

    def validate(self, result: ExecutionResult, plan: ExecutionPlan) -> list[str]:
        return []  # Always valid

    def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Export to generic JSON format.

        Returns CoreExport model as dictionary for JSON serialization.
        """
        core_export = build_core_export(result, plan)
        return core_export.model_dump()  # Pydantic model → dict
```

```python
# apps/wct/src/wct/exporters/core.py

def build_core_export(result: ExecutionResult, plan: ExecutionPlan) -> CoreExport:
    """Build core export format shared by all exporters.

    This is the base format that regulation-specific exporters extend.
    Returns a validated Pydantic model for runtime validation.

    Args:
        result: ExecutionResult with run_id and start_timestamp already populated
        plan: ExecutionPlan with runbook metadata

    Returns:
        CoreExport Pydantic model (convert to dict via .model_dump())

    Note:
        ExecutionResult now contains run_id and start_timestamp (generated
        at execution time by DAGExecutor), so they don't need to be passed
        separately. This was an architectural improvement to move metadata
        generation upstream in the execution pipeline.
    """
    return CoreExport(
        format_version="2.0.0",
        run=RunInfo(
            id=result.run_id,
            timestamp=result.start_timestamp,
            duration_seconds=result.total_duration_seconds,
            status=_calculate_status(result),
        ),
        runbook=RunbookInfo(
            name=plan.runbook.name,
            description=plan.runbook.description,
            contact=plan.runbook.contact,
        ),
        summary=_calculate_summary(result),
        outputs=_build_output_entries(result, plan),
        errors=_build_error_entries(result),
        skipped=_build_skipped_list(result),
    )
```

## GDPR Exporter

```python
# apps/wct/src/wct/exporters/gdpr/exporter.py

class GdprExporter:
    """GDPR-compliant exporter with Article 30 support.

    Organisation configuration is passed at initialization for proper
    dependency injection, not at export time.
    """

    # Schema this exporter requires (internal implementation detail)
    _REQUIRED_SCHEMA = "gdpr_article_30_finding"

    def __init__(self, organisation: OrganisationConfig | None = None) -> None:
        """Initialize GDPR exporter with organisation configuration.

        Args:
            organisation: Organisation metadata for GDPR compliance exports
        """
        self._organisation = organisation

    @property
    def name(self) -> str:
        return "gdpr"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["GDPR", "UK_GDPR"]

    def validate(self, result: ExecutionResult, plan: ExecutionPlan) -> list[str]:
        """Validate GDPR export requirements."""
        errors = []

        # Check for required schema in output artifacts
        has_required_schema = False
        for artifact_id, artifact_result in result.artifacts.items():
            if not artifact_result.success:
                continue
            _, output_schema = plan.artifact_schemas.get(artifact_id, (None, None))
            if output_schema and output_schema.name == self._REQUIRED_SCHEMA:
                has_required_schema = True
                break

        if not has_required_schema:
            errors.append(
                f"GDPR export requires {self._REQUIRED_SCHEMA} schema. "
                "Add a gdpr_article_30 analyser to your runbook pipeline."
            )

        return errors

    def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """Export to GDPR Article 30 format.

        Uses organisation config provided at initialization.
        """
        # Start with core format
        core_export = build_core_export(result, plan)
        output = core_export.model_dump()

        # Add GDPR section
        output["gdpr"] = {
            "article_30_1_a": self._build_article_30(result, plan)
        }

        return output

    def _build_article_30(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        section: dict[str, Any] = {}

        # Organisation metadata from initialization
        if self._organisation:
            section["data_controller"] = {
                "name": self._organisation.data_controller.name,
                "address": self._organisation.data_controller.address,
                "contact_email": self._organisation.data_controller.contact_email,
            }
            if self._organisation.data_controller.company_nr:
                section["data_controller"]["company_nr"] = self._organisation.data_controller.company_nr
            if self._organisation.data_controller.jurisdictions:
                section["data_controller"]["jurisdictions"] = self._organisation.data_controller.jurisdictions

            if self._organisation.dpo:
                section["dpo"] = self._organisation.dpo.model_dump(exclude_none=True)

            if self._organisation.representatives:
                section["representatives"] = [
                    r.model_dump(exclude_none=True) for r in self._organisation.representatives
                ]

            if self._organisation.data_retention:
                section["data_retention"] = self._organisation.data_retention.model_dump(exclude_none=True)
        else:
            section["_warning"] = "Organisation configuration not provided"

        # Extract GDPR findings from result
        for artifact_id, artifact_result in result.artifacts.items():
            if not artifact_result.success or not artifact_result.message:
                continue

            _, output_schema = plan.artifact_schemas.get(artifact_id, (None, None))
            if output_schema and output_schema.name == self._REQUIRED_SCHEMA:
                section["processing_record"] = artifact_result.message.content

        return section
```

## Organisation Configuration Enhancement

### Multi-Jurisdiction Support

```yaml
# apps/wct/config/organisation.yaml

# Simple (existing - single jurisdiction)
data_controller:
  name: "Company Ltd"
  address: "London, UK"
  contact_email: "privacy@company.com"
  jurisdictions:
    - "UK"
    - "EU"

# Enhanced (new - per-jurisdiction controllers)
jurisdictions:
  EU:
    data_controller:
      name: "Company EU GmbH"
      address: "Berlin, Germany"
      contact_email: "privacy-eu@company.com"
    representatives:
      - company_name: "UK Rep Ltd"
        representative_jurisdiction: "UK"
        contact_email: "uk-rep@company.com"
  UK:
    data_controller:
      name: "Company UK Ltd"
      address: "London, UK"
      contact_email: "privacy-uk@company.com"

# Common fields (apply to all jurisdictions)
dpo:
  name: "Jane Doe"
  contact_email: "dpo@company.com"

data_retention:
  general_rule: "18 months from creation"
  exceptions:
    financial_records: "6 years (legal obligation)"
```

### Loader Enhancement

```python
class OrganisationLoader:
    @classmethod
    def load(cls, jurisdiction: str | None = None) -> OrganisationConfig | None:
        """Load organisation config, optionally for specific jurisdiction.

        Args:
            jurisdiction: If provided, load jurisdiction-specific config

        Returns:
            OrganisationConfig or None if not found
        """
        # ... load YAML ...

        if jurisdiction and "jurisdictions" in data:
            if jurisdiction not in data["jurisdictions"]:
                logger.warning(f"Jurisdiction '{jurisdiction}' not found")
                return None
            # Merge jurisdiction-specific with common fields
            return cls._build_for_jurisdiction(data, jurisdiction)

        return OrganisationConfig.model_validate(data)
```

## CLI Integration

### Updated `wct run`

```python
@app.command()
def run(
    runbook_path: Path,
    output_dir: Path = typer.Option("./output", help="Output directory"),
    output: Path = typer.Option("results.json", help="Output filename"),
    exporter: str | None = typer.Option(
        None,
        help="Export format (overrides auto-detection). Available: json, gdpr"
    ),
    jurisdiction: str | None = typer.Option(
        None,
        help="Jurisdiction for organisation config (e.g., EU, UK)"
    ),
    verbose: bool = typer.Option(False, "-v"),
    log_level: str = typer.Option("INFO"),
):
    """Execute a runbook and export results."""
    # ... execution logic ...

    # Determine export format from CLI override or runbook framework
    export_format = exporter or _detect_exporter(plan)

    # Get exporter
    exp = ExporterRegistry.get(export_format)

    # Validate
    errors = exp.validate(result, plan)
    if errors:
        for error in errors:
            console.print(f"[red]Export validation error: {error}[/red]")
        raise typer.Exit(1)

    # Load organisation if needed
    org = None
    if export_format != "json":
        org = OrganisationLoader.load(jurisdiction)
        if org is None and export_format == "gdpr":
            console.print("[yellow]Warning: No organisation config found[/yellow]")

    # Export
    output_data = exp.export(result, plan, org)
    _save_json(output_path, output_data)


def _detect_exporter(plan: ExecutionPlan) -> str:
    """Select exporter based on runbook framework declaration.

    Args:
        plan: Execution plan with runbook definitions.

    Returns:
        Exporter name based on runbook framework.
    """
    framework = plan.runbook.framework
    if framework is None:
        return "json"

    return _framework_to_exporter(framework)


def _framework_to_exporter(framework: str) -> str:
    """Map compliance framework to exporter name."""
    mapping = {
        "GDPR": "gdpr",
        "UK_GDPR": "gdpr",  # UK GDPR uses same format as EU GDPR
        "CCPA": "ccpa",
        # Add more as needed
    }
    return mapping.get(framework, "json")
```

### New `wct export` Command

```python
@app.command()
def export(
    results_path: Path = typer.Argument(..., help="Path to existing results JSON"),
    exporter: str = typer.Option(..., "--exporter", "-e", help="Export format"),
    output: Path | None = typer.Option(None, "-o", help="Output path"),
    jurisdiction: str | None = typer.Option(None, help="Jurisdiction for organisation"),
):
    """Re-export existing results with a different exporter.

    This allows generating multiple compliance formats from a single analysis run.

    Examples:
        wct export output/results.json -e gdpr -o gdpr_ropa.json
        wct export output/results.json -e ccpa --jurisdiction US-CA
    """
    # Load existing results
    with results_path.open() as f:
        existing = json.load(f)

    # Reconstruct minimal plan from results
    # (This is a simplified re-export - full plan not available)

    # Get exporter and export
    exp = ExporterRegistry.get(exporter)
    org = OrganisationLoader.load(jurisdiction)

    # ... export logic ...
```

### New `wct ls-exporters` Command

```python
@app.command()
def ls_exporters():
    """List available exporters."""
    exporters = ExporterRegistry.list_exporters()

    table = Table(title="Available Exporters")
    table.add_column("Name")
    table.add_column("Supported Frameworks")

    for name in exporters:
        exp = ExporterRegistry.get(name)
        frameworks = exp.supported_frameworks or ["(any)"]
        table.add_row(name, ", ".join(frameworks))

    console.print(table)
```

## Package Structure

```
apps/wct/src/wct/
├── exporters/
│   ├── __init__.py           # Export Exporter, ExporterRegistry, JsonExporter, GdprExporter
│   ├── protocol.py           # Exporter protocol
│   ├── registry.py           # ExporterRegistry
│   ├── core.py               # build_core_export() shared logic
│   ├── json_exporter.py      # JsonExporter
│   └── gdpr/
│       ├── __init__.py
│       └── exporter.py       # GdprExporter
├── organisation.py           # OrganisationConfig, OrganisationLoader (existing, enhanced)
└── cli.py                    # Updated with export support
```

## Implementation Status

### Task C: Export Foundation ✅ COMPLETE

1. ✅ Add `framework` field to Runbook model
2. ✅ Create `wct/exporters/` module structure
3. ✅ Implement `Exporter` protocol
4. ✅ Implement `ExporterRegistry`
5. ✅ Implement `_detect_exporter()` based on `runbook.framework`
6. ✅ Extract `build_core_export()` from current CLI
7. ✅ Implement `JsonExporter`
8. ✅ Add `--exporter` flag to `wct run`
9. ⏸️ Add `wct export` command - **DEFERRED** (see [Export Re-Export Command](./export-re-export-command.md))
10. ✅ Add `wct ls-exporters` command
11. ✅ Register exporters at app startup

### Task D: Organisation Config Enhancement

1. Update `OrganisationConfig` for multi-jurisdiction
2. Update `OrganisationLoader.load()` with jurisdiction parameter
3. Add `--jurisdiction` flag to CLI
4. Update sample organisation.yaml

### Task F: GDPR Exporter

1. Implement `GdprExporter`
2. Implement `validate()` for schema checking
3. Implement `_build_article_30()` for GDPR formatting
4. Register in `ExporterRegistry`
5. Add tests

## Future Extensions

### Additional Exporters

- **CcpaExporter** - California Consumer Privacy Act format
- **Nis2Exporter** - NIS2 Directive format
- **DorAExporter** - Digital Operational Resilience Act format

### Output Formats

Current design produces JSON. Future versions could support:

- **PDF** - Human-readable compliance documents
- **XML** - Machine-readable regulatory submissions
- **HTML** - Web-viewable reports

```python
class Exporter(Protocol):
    def export(self, ...) -> dict[str, Any]: ...
    def export_pdf(self, ...) -> bytes: ...  # Future
    def export_xml(self, ...) -> str: ...    # Future
```

### Compliance Gap Flagging

GDPR exporter could flag missing compliance fields:

```json
{
  "gdpr": {
    "article_30_1_a": {
      "processing_record": { ... },
      "compliance_gaps": [
        {
          "field": "legal_basis",
          "activity": "user_authentication",
          "severity": "critical",
          "message": "Legal basis not determined - requires human review"
        }
      ],
      "requires_human_review": true
    }
  }
}
```

This is already supported by the `gdpr_article_30_finding` schema from the GDPR analyser.

## Related Documents

- [Multi-Schema Fan-In](./multi-schema-fan-in.md)
- [Artifact-Centric Runbook](./artifact-centric-runbook.md)
- [DAG Orchestration Layer](./dag-orchestration-layer.md)
