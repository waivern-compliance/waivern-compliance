# Organisation Config Enhancement and Documentation

- **Status:** Deferred - Awaiting GDPR Analyser and Exporter
- **Last Updated:** 2025-12-09
- **Related:** [Export Architecture](./export-architecture.md), [GDPR Complete](./gdpr-complete.md)

## Problem

Framework-specific exporters (GDPR, CCPA) require organisation metadata for compliance outputs. Multi-jurisdiction organisations need different organisation configurations per jurisdiction (EU vs UK vs US-CA).

## Rationale for Deferral

Without GDPR exporter implemented, organisation config requirements are **speculative**. Building infrastructure before understanding actual needs risks premature design.

**Key considerations:**

1. **No consumer** - Multi-jurisdiction config has no exporter to use it yet. Current simple organisation config is sufficient for existing functionality.

2. **Requirements uncertainty** - GDPR Article 30 requirements are theoretical until we implement the exporter. We don't know what fields are truly required vs nice-to-have.

3. **Better feedback loop** - Implementing GDPR exporter first will reveal actual organisation config needs, enabling evidence-based design rather than speculation.

4. **Documentation completeness** - Documenting organisation config → GDPR export flow makes sense only when both pieces exist.

## Scope

### Organisation Config Enhancement (formerly Task 7e)

**Goal:** Support multi-jurisdiction organisation configurations.

**Example use case:**
- Organisation operates in EU, UK, and US-CA
- Each jurisdiction has different data controller entity
- Each jurisdiction requires different representative information
- GDPR exporter needs EU-specific config; CCPA exporter needs US-CA-specific config

**Design considerations:**
- Jurisdiction-specific data controller and representatives
- Common fields shared across jurisdictions (DPO, retention policies)
- Jurisdiction selection via CLI flag (`--jurisdiction EU`)
- Validation that required jurisdiction config exists

### Sample Runbooks and Documentation (formerly Task 7f)

**Goal:** Demonstrate export infrastructure with real regulatory examples.

**Planned updates:**
- Sample runbook showing multi-jurisdiction GDPR export
- Documentation of organisation config → exporter flow
- Examples of framework-specific vs generic export outputs
- Updated CLAUDE.md with exporter development patterns

## Implementation Dependencies

1. **GDPR Analyser** - Implement GdprArticle30Analyser (multi-schema fan-in synthesiser)
2. **GDPR Exporter** - Implement GdprExporter with organisation metadata integration
3. **Real requirements** - Discover actual organisation config fields from GDPR Article 30 RoPA format

## Implementation Approach

When implementing GDPR exporter:

1. **Start simple** - Use existing organisation config initially
2. **Identify gaps** - Note which fields are missing for proper GDPR Article 30 output
3. **Design enhancement** - Create multi-jurisdiction config based on actual needs
4. **Implement loader** - Add jurisdiction selection to OrganisationLoader
5. **Update CLI** - Add `--jurisdiction` flag
6. **Create samples** - Build runbook demonstrating GDPR export with jurisdiction selection
7. **Document flow** - Update docs showing complete organisation config → export pipeline

## Why Not Implement Now

**Speculative design risks:**
- Over-engineering fields we won't use
- Under-engineering fields we'll discover we need
- Wrong structure requiring refactoring when real requirements emerge

**YAGNI principle:**
- Build infrastructure when it has a consumer
- Design based on actual requirements, not theoretical ones
- Avoid premature abstraction

**Implementation coherence:**
- GDPR work as coherent batch (analyser + exporter + config + samples + docs)
- Natural discovery process: implement exporter → identify config needs → enhance config
- Better integration when pieces are built together

## Success Criteria

When implementing, we'll know it's successful if:
- GDPR exporter can access all required organisation metadata
- Multi-jurisdiction selection works correctly
- Sample runbooks demonstrate real regulatory use cases
- Documentation clearly explains organisation config → exporter flow
- No speculative fields remain unused
