# Export Re-Export Command (`wct export`)

- **Status:** Deferred - Awaiting Execution Persistence
- **Last Updated:** 2025-12-10
- **Related:** [Export Architecture](./export-architecture.md), [Execution Persistence](./execution-persistence.md)

## Problem

Users need to generate multiple compliance formats (GDPR, CCPA, etc.) from a single analysis run without re-executing the entire runbook. Currently, re-exporting requires re-running the analysis.

## Architectural Decisions

The following architectural decisions drive the design of the export and re-export functionality:

1. **ExecutionResult is the single source of truth**
   - `ExecutionResult` contains all execution metadata, artifact results, timing, and status information
   - All export operations must work from `ExecutionResult` as the canonical data source
   - In future, `ExecutionResult` should be persistable in a datastore (similar to artifacts) to enable historical access and re-export

2. **Re-exporting operates on ExecutionResult, not re-execution**
   - Re-export should load a previously saved `ExecutionResult` from persistent storage
   - Re-export must NOT re-run the analysis pipeline
   - This enables fast format conversion and supports SaaS deployments where users need historical access

These decisions ensure that:
- Export logic remains pure presentation layer (no analysis logic)
- Performance is optimised (no unnecessary re-computation)
- Historical data can be accessed without re-execution
- Future persistence layer can be implemented cleanly

## Rationale for Deferral

The `wct export` command requires access to the original `ExecutionResult` and `ExecutionPlan` objects to call exporters. The current system saves only the final exported format (CoreExport JSON), not the raw execution artifacts.

**Key considerations:**

1. **Data availability** - Exporters require `ExecutionResult` and `ExecutionPlan` as inputs. Reconstructing these from CoreExport JSON is fragile and lossy.

2. **Dependency on persistence** - Proper re-export requires execution persistence (see [Execution Persistence](./execution-persistence.md)) to save raw execution artifacts alongside exported formats.

3. **Limited testing value** - Without multiple exporters (GDPR, CCPA, etc.) implemented, re-export functionality cannot be meaningfully tested.

4. **Core functionality complete** - The essential export infrastructure is implemented:
   - Exporter protocol and registry
   - Auto-detection based on compliance frameworks
   - Manual override via `--exporter` flag
   - Exporter listing via `wct ls-exporters`

## Design Considerations

When implementing `wct export`, the following must be addressed:

1. **Storage format** - Save both exported output AND raw execution data (ExecutionResult + ExecutionPlan) for re-export capability.

2. **Format compatibility** - Re-export must work only from "raw" formats (CoreExport JSON), not from framework-specific exports (GDPR, CCPA), as these lose information.

3. **Validation** - Re-export must validate that the loaded execution data contains required schemas for the target exporter.

4. **Organisation config** - Framework-specific exporters (GDPR) require organisation configuration, which must be re-specified during re-export.

## Proposed Interface

```bash
# Re-export from saved execution data
wct export <run-id> --exporter gdpr --output gdpr_ropa.json

# With jurisdiction override
wct export <run-id> --exporter gdpr --jurisdiction EU --output eu_ropa.json
```

## Implementation Dependencies

1. **Execution Persistence** - Implement ExecutionStore and ArtifactStore to save raw execution data (see [Execution Persistence](./execution-persistence.md))

2. **Multiple Exporters** - Implement framework-specific exporters (GDPR, CCPA) to validate re-export functionality

3. **Organisation Config Enhancement** - Support jurisdiction-specific organisation configuration for multi-region deployments

## Alternative Considered

**Immediate simplified implementation** - Load CoreExport JSON and reconstruct minimal ExecutionResult/ExecutionPlan.

Rejected because:
- Fragile reconstruction logic prone to breaking with format changes
- Lossy transformation (CoreExport doesn't preserve all execution metadata)
- Limited testing without multiple exporters
- Adds complexity without clear immediate value

## Next Steps

When ready to implement:
1. Implement execution persistence (ExecutionStore + ArtifactStore)
2. Implement GDPR exporter for testing re-export across formats
3. Add `wct export` command reading from persisted stores
4. Add integration tests validating re-export with multiple formats
