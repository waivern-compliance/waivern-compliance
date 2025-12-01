# Task 7: Implement GDPR Exporter

- **Phase:** 4 - Export
- **Status:** TODO
- **GitHub Issue:** TBD
- **Prerequisites:** Task 5 (CLI and output format)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Task 5 defines the core export format and exporter architecture. This task implements the first regulation-specific exporter (GDPR) as a concrete proof of the design.

## Purpose

1. Implement `GdprExporter` that adds GDPR Article 30(1)(a) compliance info
2. Validate the exporter architecture design
3. Provide a template for future regulation-specific exporters (CCPA, etc.)

## Problem

The core export format contains execution results but no regulation-specific compliance context. GDPR Article 30(1)(a) requires records of processing activities to include data controller information.

## Design

### GDPR Export Format

Extends core format with `organisation` section:

```json
{
  "format_version": "2.0.0",

  "run": { ... },
  "runbook": { ... },
  "summary": { ... },
  "outputs": [ ... ],
  "errors": [ ... ],
  "skipped": [ ... ],

  "gdpr": {
    "article_30_1_a": {
      "data_controller": {
        "name": "Company Ltd",
        "address": "123 High Street, London",
        "contact_email": "privacy@company.com",
        "company_nr": "12345678",
        "jurisdictions": ["UK", "EU"]
      },
      "dpo": {
        "name": "Jane Doe",
        "contact_email": "dpo@company.com",
        "contact_address": "123 High Street, London"
      },
      "representatives": [
        {
          "company_name": "EU Rep Ltd",
          "company_jurisdiction": "EU",
          "contact_email": "eurep@company.com",
          "contact_address": "Berlin, Germany",
          "representative_jurisdiction": "EU"
        }
      ],
      "joint_controller": null,
      "privacy_contact": {
        "email": "privacy@company.com"
      },
      "data_retention": {
        "general_rule": "Data retained for 7 years",
        "exceptions": {
          "marketing": "Until consent withdrawn"
        }
      }
    }
  }
}
```

### Exporter Interface

```python
class Exporter(Protocol):
    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
        """Export execution result to dictionary format."""
        ...

class JsonExporter:
    """Core format only."""
    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
        return build_core_export(result, runbook_path)

class GdprExporter:
    """Core format + GDPR Article 30(1)(a) compliance."""
    def __init__(self, organisation_config: OrganisationConfig | None = None):
        self._organisation = organisation_config

    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
        output = build_core_export(result, runbook_path)

        # Load organisation if not provided
        org = self._organisation or OrganisationLoader.load()

        if org:
            output["gdpr"] = {
                "article_30_1_a": org.to_export_metadata()
            }
        else:
            # Warn but don't fail - organisation info is optional
            logger.warning("No organisation config found for GDPR export")

        return output
```

## Implementation

### Files to Create/Modify

```
apps/wct/src/wct/
├── exporters/
│   ├── __init__.py        # NEW: export Exporter, JsonExporter, GdprExporter
│   ├── base.py            # NEW: Exporter protocol, build_core_export()
│   ├── json_exporter.py   # NEW: JsonExporter
│   └── gdpr_exporter.py   # NEW: GdprExporter
├── cli.py                 # MODIFY: add --exporter flag to wct run
└── organisation.py        # EXISTS: reuse OrganisationConfig, OrganisationLoader
```

### CLI Changes

```bash
# Default: core JSON format
wct run runbook.yaml

# GDPR export: includes Article 30(1)(a) info
wct run runbook.yaml --exporter gdpr

# Explicit JSON (same as default)
wct run runbook.yaml --exporter json
```

### Changes Required

#### 1. Create exporter base

```python
# exporters/base.py

from typing import Any, Protocol
from pathlib import Path
from waivern_orchestration import ExecutionResult

class Exporter(Protocol):
    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]: ...

def build_core_export(result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
    """Build core export format from ExecutionResult."""
    ...
```

#### 2. Implement JsonExporter

```python
# exporters/json_exporter.py

class JsonExporter:
    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
        return build_core_export(result, runbook_path)
```

#### 3. Implement GdprExporter

```python
# exporters/gdpr_exporter.py

class GdprExporter:
    def __init__(self, organisation_config: OrganisationConfig | None = None):
        self._organisation = organisation_config

    def export(self, result: ExecutionResult, runbook_path: Path) -> dict[str, Any]:
        output = build_core_export(result, runbook_path)

        org = self._organisation or OrganisationLoader.load()
        if org:
            output["gdpr"] = {
                "article_30_1_a": org.to_export_metadata()
            }

        return output
```

#### 4. Update CLI

Add `--exporter` option to `wct run`:

```python
@app.command()
def run(
    runbook_path: Path,
    exporter: str = typer.Option("json", help="Export format: json, gdpr"),
):
    ...

    # Select exporter
    if exporter == "gdpr":
        exp = GdprExporter()
    else:
        exp = JsonExporter()

    # Export and write
    output = exp.export(result, runbook_path)
    write_json(output_path, output)
```

## Testing

### Test Scenarios

#### 1. JsonExporter produces core format
- Execute runbook
- Export with JsonExporter
- Verify no `gdpr` section present
- Verify all core sections present

#### 2. GdprExporter with organisation config
- Create organisation.yaml
- Execute runbook
- Export with GdprExporter
- Verify `gdpr.article_30_1_a` section present
- Verify data_controller info matches config

#### 3. GdprExporter without organisation config
- Remove/rename organisation.yaml
- Execute runbook
- Export with GdprExporter
- Verify warning logged
- Verify export still succeeds (core format only)

#### 4. CLI --exporter flag
- Run `wct run runbook.yaml --exporter gdpr`
- Verify GDPR format output

### Validation Commands

```bash
# Run with GDPR export
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml --exporter gdpr

# Verify organisation info included
cat output.json | jq '.gdpr.article_30_1_a.data_controller'

# Run tests
uv run pytest apps/wct/tests/test_exporters.py -v

# Full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Reuse existing `OrganisationConfig` and `OrganisationLoader` from `wct/organisation.py`
- `build_core_export()` is shared by all exporters - single source of truth for core format
- GDPR section is `gdpr.article_30_1_a` to allow for other GDPR articles in future
- Organisation info is optional - export succeeds with warning if not configured
- This task validates the exporter architecture for future CCPA, NIS2, etc. exporters
