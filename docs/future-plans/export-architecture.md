# Export Architecture Design

- **Status:** Design Proposal
- **Last Updated:** 2025-12-03
- **Related:** [Multi-Schema Fan-In](./multi-schema-fan-in.md), [Artifact-Centric Runbook](./artifact-centric-runbook.md)

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
2. **Analysers declare compliance frameworks** - ComponentFactory declares which frameworks its output supports
3. **Schema-based discovery** - Exporter auto-selected based on analyser framework declarations
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

## Component Compliance Framework Declaration

### Component Classmethods

Components (Analysers, Connectors) declare which compliance frameworks their output supports via classmethods. Factories only handle instantiation.

```python
# waivern-core/base_analyser.py

class Analyser(ABC):
    """Base class for analysers."""

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this component's output supports.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic components.
        """
        return []  # Default: generic component

    # ... other methods (get_input_requirements, process, etc.)
```

```python
# waivern-core/base_connector.py

class Connector(ABC):
    """Base class for connectors."""

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this component's output supports.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic components.
        """
        return []  # Default: generic component

    # ... other methods (extract, etc.)
```

### Examples

```python
# Generic analyser - usable across any framework
class PersonalDataAnalyser(Analyser):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return []  # Generic building block


# GDPR-specific analyser
class GdprArticle30Analyser(Analyser):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR"]


# Multi-framework analyser
class CrossBorderTransferAnalyser(Analyser):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR", "UK_GDPR", "SWISS_DPA"]


# GDPR-specific connector
class GdprConsentConnector(Connector):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR"]
```

### Discovery Flow

The compliance framework is discovered from the analysers used in the runbook, not declared in the runbook itself:

```
Execution completes
       │
       ▼
For each successful artifact with transform:
       │
       ▼
Get analyser factory from registry
       │
       ▼
Call factory.get_compliance_frameworks()
       │
       ▼
Collect all declared frameworks
       │
       ▼
Select exporter based on frameworks found
```

**Selection logic:**
- Single framework found → use matching exporter
- Multiple frameworks → user must specify or use generic JSON
- No frameworks (all generic) → use JSON exporter

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
        organisation: OrganisationConfig | None = None,
    ) -> dict[str, Any]:
        """Export execution results to structured format.

        Args:
            result: Execution results with artifact data
            plan: Execution plan with runbook metadata
            organisation: Optional organisation config for compliance exports

        Returns:
            Export dictionary ready for JSON serialisation
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
        organisation: OrganisationConfig | None = None,
    ) -> dict[str, Any]:
        return build_core_export(result, plan)


def build_core_export(result: ExecutionResult, plan: ExecutionPlan) -> dict[str, Any]:
    """Build core export format shared by all exporters.

    This is the base format that regulation-specific exporters extend.
    """
    runbook = plan.runbook

    return {
        "format_version": "2.0.0",
        "run": {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": result.total_duration_seconds,
            "status": _determine_status(result),
        },
        "runbook": {
            "name": runbook.name,
            "description": runbook.description,
            "contact": runbook.contact,
        },
        "summary": {
            "total": len(result.artifacts) + len(result.skipped),
            "succeeded": sum(1 for a in result.artifacts.values() if a.success),
            "failed": sum(1 for a in result.artifacts.values() if not a.success),
            "skipped": len(result.skipped),
        },
        "outputs": _build_outputs(result, plan),
        "errors": _build_errors(result),
        "skipped": list(result.skipped),
    }
```

## GDPR Exporter

```python
# apps/wct/src/wct/exporters/gdpr/exporter.py

class GdprExporter:
    """GDPR-compliant exporter with Article 30 support."""

    # Schema this exporter requires (internal implementation detail)
    _REQUIRED_SCHEMA = "gdpr_article_30_finding"

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
        organisation: OrganisationConfig | None = None,
    ) -> dict[str, Any]:
        # Start with core format
        output = build_core_export(result, plan)

        # Add GDPR section
        output["gdpr"] = {
            "article_30_1_a": self._build_article_30(result, plan, organisation)
        }

        return output

    def _build_article_30(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
        organisation: OrganisationConfig | None,
    ) -> dict[str, Any]:
        section: dict[str, Any] = {}

        # Organisation metadata
        if organisation:
            section["data_controller"] = {
                "name": organisation.data_controller.name,
                "address": organisation.data_controller.address,
                "contact_email": organisation.data_controller.contact_email,
            }
            if organisation.data_controller.company_nr:
                section["data_controller"]["company_nr"] = organisation.data_controller.company_nr
            if organisation.data_controller.jurisdictions:
                section["data_controller"]["jurisdictions"] = organisation.data_controller.jurisdictions

            if organisation.dpo:
                section["dpo"] = organisation.dpo.model_dump(exclude_none=True)

            if organisation.representatives:
                section["representatives"] = [
                    r.model_dump(exclude_none=True) for r in organisation.representatives
                ]

            if organisation.data_retention:
                section["data_retention"] = organisation.data_retention.model_dump(exclude_none=True)
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

    # Determine export format from CLI override or auto-detect from analysers
    export_format = exporter or _detect_exporter(result, plan, registry)

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


def _detect_exporter(
    result: ExecutionResult,
    plan: ExecutionPlan,
    registry: ComponentRegistry,
) -> str:
    """Auto-detect exporter based on component compliance frameworks.

    Args:
        result: Execution result with artifact outcomes.
        plan: Execution plan with runbook definitions.
        registry: Component registry for factory lookup.

    Returns:
        Exporter name based on detected frameworks.
    """
    frameworks: set[str] = set()

    for artifact_id, artifact_result in result.artifacts.items():
        if not artifact_result.success:
            continue

        definition = plan.runbook.artifacts.get(artifact_id)
        if definition is None:
            continue

        # Check connector compliance frameworks
        if definition.source is not None:
            connector_type = definition.source.type
            if connector_type in registry.connector_factories:
                factory = registry.connector_factories[connector_type]
                frameworks.update(factory.component_class.get_compliance_frameworks())

        # Check analyser compliance frameworks
        if definition.transform is not None:
            analyser_type = definition.transform.type
            if analyser_type in registry.analyser_factories:
                factory = registry.analyser_factories[analyser_type]
                frameworks.update(factory.component_class.get_compliance_frameworks())

    # Map frameworks to exporter
    if len(frameworks) == 1:
        return _framework_to_exporter(frameworks.pop())
    elif len(frameworks) > 1:
        # Multiple frameworks detected - fall back to JSON
        logger.info(
            "Multiple compliance frameworks detected: %s. Using JSON exporter. "
            "Use --exporter to specify a specific format.",
            frameworks
        )
        return "json"
    else:
        return "json"  # All generic analysers


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

## Implementation Tasks

### Task C: Export Foundation

1. Add `get_compliance_frameworks()` classmethod to `Analyser` and `Connector` base classes in waivern-core
2. Create `wct/exporters/` module structure
3. Implement `Exporter` protocol
4. Implement `ExporterRegistry`
5. Implement `_detect_exporter()` for schema-based discovery
6. Extract `build_core_export()` from current CLI
7. Implement `JsonExporter`
8. Add `--exporter` flag to `wct run`
9. Add `wct export` command
10. Add `wct ls-exporters` command
11. Register exporters at app startup

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
