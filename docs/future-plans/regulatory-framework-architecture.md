# Regulatory Framework Architecture

- **Status:** Design Discussion
- **Last Updated:** 2025-12-30
- **Related:** [Export Architecture](./export-architecture.md), [Business Logic Centric Analysers](./business-logic-centric-analysers.md)

## Overview

This document describes the architectural approach for handling regulatory framework-specific knowledge and logic within WCF. It establishes principles for separating technical analysis from regulatory interpretation, and defines clear ownership boundaries between components.

## Problem Statement

The current architecture mixes technical detection with regulatory interpretation:

1. **Rulesets contain both patterns and compliance mappings** - A personal data rule contains the pattern (`email`) AND the GDPR article reference (`Article 9`). This couples technical detection to specific regulations.

2. **Analysers reference multiple frameworks** - The `personal_data` ruleset references GDPR, ePrivacy, and EU AI Act within the same rules. This makes it unclear which regulation owns which logic.

3. **No regulation-centric view** - Cannot easily query "show me everything related to GDPR Article 9" across all analysers.

4. **Framework inference from components** - The `get_compliance_frameworks()` method on analysers was designed to infer the regulatory framework from components rather than declaring it explicitly.

## Design Principles

### Principle 1: Framework-Agnostic Core

The core of WCF should be a set of tools usable across different regulatory frameworks. Technical analysis (detecting personal data, identifying processing purposes, classifying data subjects) is fundamentally the same regardless of which regulation applies.

**Implication:** Connectors and technical analysers should not contain regulation-specific logic. They answer "what exists" not "what does regulation X say about it."

### Principle 2: Analyser-Centric Organisation

The primary organisation is by analysis type (personal data, processing purposes, data subjects), not by regulation (GDPR module, CCPA module). This reflects the reality that many regulations require similar technical analyses.

**Implication:** We build a `PersonalDataAnalyser` that works for any framework, not a `GDPRPersonalDataAnalyser` and a `CCPAPersonalDataAnalyser` with 90% duplication.

### Principle 3: Regulation-Centric Aggregation at Export

Regulation-specific formatting and aggregation happens at the export layer, not the analysis layer. The exporter is the component that understands how to present findings according to a specific regulation's requirements.

**Implication:** A GDPR exporter knows how to format an Article 30 Record of Processing Activities. It consumes classified findings and produces regulation-compliant output.

### Principle 4: Classification After Technical Analysis

Technical detection should complete before regulatory interpretation begins. This provides flexibility and clear separation of concerns:

1. Technical analysers output generic findings ("found health data")
2. Classifiers enrich with regulatory context ("GDPR Article 9 special category")
3. Exporters format for compliance documentation

**Implication:** A new component type—the Classifier—sits between technical analysers and export. It applies framework-specific interpretation rules to generic findings.

### Principle 5: Framework-Specific Analysers When Necessary

Some analyses are inherently framework-specific and cannot be generalised. For these cases, build a framework-specific analyser rather than forcing genericity through abstraction layers.

Examples:

- GDPR Right to Erasure analysis
- GDPR Data Transfer Impact Assessment
- CCPA Opt-Out mechanism detection

**Implication:** Framework-specific analysers own both detection AND classification internally. They don't need a separate classifier step because the analysis is already framework-bound.

### Principle 6: Runbook Declares Single Framework

A runbook targets a single regulatory framework. There is no use case for a runbook that simultaneously assesses GDPR and CCPA compliance in the same execution. Cross-framework comparison is a reporting concern, handled by running separate runbooks.

**Implication:** The runbook declares its framework at the root level. This becomes the context for the entire execution pipeline.

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RUNBOOK                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  framework: "GDPR"                                                  │    │
│  │  All downstream processing knows the regulatory context             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                      ▼
┌─────────────────────┐                              ┌─────────────────────┐
│  GENERIC TECHNICAL  │                              │  FRAMEWORK-SPECIFIC │
│  ANALYSERS          │                              │  ANALYSERS          │
│                     │                              │                     │
│  PersonalData       │                              │  GDPRDataTransfer   │
│  ProcessingPurpose  │                              │  GDPRDPIA           │
│  DataSubject        │                              │  CCPAOptOut         │
│                     │                              │                     │
│  Output: Technical  │                              │  Output: Already    │
│  findings (generic) │                              │  classified         │
└──────────┬──────────┘                              └──────────┬──────────┘
           │                                                    │
           ▼                                                    │
┌─────────────────────┐                                         │
│  CLASSIFIER         │                                         │
│  (per framework)    │                                         │
│                     │                                         │
│  GDPRClassifier     │                                         │
│  CCPAClassifier     │                                         │
│                     │                                         │
│  Enriches findings  │                                         │
│  with regulatory    │                                         │
│  interpretation     │                                         │
└──────────┬──────────┘                                         │
           │                                                    │
           └────────────────────┬───────────────────────────────┘
                                ▼
                  ┌─────────────────────┐
                  │  EXPORTER           │
                  │  (per framework)    │
                  │                     │
                  │  Formats for        │
                  │  compliance docs    │
                  └─────────────────────┘
```

## Component Responsibilities

### Rulesets

**Current:** Mix of patterns and compliance mappings in the same YAML files, tightly coupled to the framework.

**Proposed:** Rulesets are authored by legal experts and contain BOTH detection patterns AND classification rules. This is their complete methodology. See [Ruleset as Legal Product](#ruleset-as-legal-product) for details.

**Key change:** Rulesets become exchangeable products—different legal firms can author different rulesets for the same framework, and runbook authors choose which to use.

### Technical Analysers

**Responsibility:** Detect technical facts without regulatory interpretation.

**Input:** Raw data (standard_input, source_code, database schemas)

**Output:** Generic findings with:

- What was detected (category, patterns matched)
- Where it was found (location, evidence)
- Confidence level
- NO regulation-specific fields

### Classifiers

**Responsibility:** Apply framework-specific interpretation to generic findings.

**Input:** Generic technical findings

**Output:** Enriched findings with:

- Regulatory classification (e.g., "special category")
- Article/section references
- Legal basis requirements
- Risk level adjustments per framework

**Ownership:** One classifier per framework. Related frameworks (GDPR, UK GDPR, Swiss DPA) may share logic through inheritance or composition.

### Framework-Specific Analysers

**Responsibility:** Detect AND classify framework-specific concepts that have no generic equivalent.

**Examples:**

- GDPR Right to Erasure implementation detection
- GDPR Data Transfer mechanisms (SCCs, adequacy decisions)
- CCPA "Do Not Sell" signal handling

**Characteristics:**

- Cannot be reused across frameworks
- Classification happens internally
- Named with framework prefix (e.g., `gdpr_data_transfer`)

### Exporters

**Responsibility:** Format classified findings into compliance documentation.

**Input:** Classified findings (from classifiers or framework-specific analysers)

**Output:** Regulation-compliant documents (JSON, PDF, XML)

## Key Decisions

### Decision 1: Remove `get_compliance_frameworks()` from Component Contract

**Context:** The current `Analyser` and `Connector` base classes include a `get_compliance_frameworks()` method used to infer which framework a runbook targets.

**Decision:** Remove this method. Framework is declared in the runbook, not inferred from components.

**Rationale:**

1. Runbook declaration is explicit and unambiguous
2. Generic analysers return `[]` anyway (most analysers)
3. Framework-specific analysers are self-documenting via naming
4. Removes coupling between components and framework knowledge
5. Simplifies the component contract

**Migration:** Update `export-architecture.md` to reflect that exporter selection is based on `runbook.framework`, not inferred from analysers.

### Decision 2: Runbook Authors Responsible for Analyser Selection

**Context:** Should the framework validate which analysers can be used?

**Decision:** No. Runbook authors select appropriate analysers. The framework provides child runbooks and templates to make correct composition easier.

**Rationale:**

1. Avoids false limitations (what if someone wants to use a GDPR analyser for UK GDPR research?)
2. Keeps component contract simple
3. Child runbooks and templates provide guidance without enforcement
4. Framework-specific analysers are obviously framework-specific by naming

### Decision 3: Single Framework Per Runbook

**Context:** Should a runbook support multiple frameworks simultaneously?

**Decision:** No. Each runbook targets exactly one regulatory framework.

**Rationale:**

1. Simplifies the entire pipeline (no need to branch or multiplex)
2. Framework becomes implicit context for all components
3. Cross-framework comparison is a reporting concern, handled externally
4. Aligns with real-world use cases (organisations assess one framework at a time)

### Decision 4: Classification as Separate Component Type

**Context:** Where should regulatory interpretation happen?

**Decision:** Classifiers are a distinct component type (like Analysers, Connectors) that run after technical analysis.

**Rationale:**

1. Clear separation of technical detection and regulatory interpretation
2. Easy to add new frameworks (create new classifier, don't touch technical analysers)
3. Classifiers can be tested independently of detection logic
4. Classifiers consume rulesets which contain legal experts' interpretation

**Alternative considered:** Classification as configuration to technical analysers. Rejected because it blurs responsibilities and makes testing harder.

### Decision 5: LLM Validation on Technical Findings

**Context:** When should LLM validation occur—on technical findings or classified findings?

**Decision:** LLM validation happens on technical findings, before classification.

**Rationale:**

1. LLM is filtering false positives ("is this really an email address?")
2. LLM is not making regulatory judgments
3. Classification operates on validated, high-confidence findings
4. Keeps LLM role focused and auditable

### Decision 6: Schema as Contract Between Analysers and Classifiers

**Context:** How do we enforce the contract between technical analysers and classifiers?

**Decision:** Use schema versioning and integration tests. If a schema is not relevant for a classifier, create a new one rather than forcing genericity.

**Rationale:**

1. Schema versioning already exists—classifiers declare which schema versions they support
2. Integration tests verify analyser outputs are classifier-compatible
3. Schemas are the ONLY contract—no shared base types or abstract interfaces
4. Prefer specific schemas over generic ones; each framework may need its own finding schema

**Rejected:** Shared base types in `waivern-core` for finding structures. This would force artificial genericity and couple components unnecessarily.

### Decision 7: Classifiers Invoked Explicitly in Runbooks

**Context:** How should classifiers be invoked?

**Decision:** Classifiers are explicit artifacts in the runbook, added by the runbook author as a processing step.

**Rationale:**

1. Runbooks mastermind the analysis—components don't decide what runs
2. Keeps runbooks transparent and predictable
3. No magic injection or hidden behaviour
4. User has full control over the pipeline

**Rejected alternatives:**

- Automatic injection by orchestrator—makes runbooks opaque, hides behaviour
- Exporter applies classification—conflates presentation with analysis

## What Changes from Current State

| Aspect                        | Current                                     | Proposed                                              |
| ----------------------------- | ------------------------------------------- | ----------------------------------------------------- |
| Rulesets                      | Patterns + compliance mappings in same file | Separate detection patterns from classification rules |
| Technical analysers           | Output findings with regulation references  | Output generic findings (no regulation references)    |
| `get_compliance_frameworks()` | On all analysers/connectors                 | Removed                                               |
| Framework declaration         | Inferred from components                    | Explicit in runbook root                              |
| Classification                | Mixed into analysers                        | Separate classifier component type                    |
| Exporter selection            | Auto-detected from analyser frameworks      | Based on runbook.framework                            |

## Regulation Coverage Strategy

### Adding a New Regulation

To add support for a new regulation (e.g., Brazil LGPD):

1. **Create classifier** - `LGPDClassifier` that understands LGPD-specific concepts
2. **Create rulesets** - Detection patterns and classification rules for LGPD (can be authored by legal firms)
3. **Create exporter** - `LGPDExporter` for LGPD-compliant documentation
4. **Create runbook templates** - Pre-built runbooks for common LGPD assessments
5. **Optionally create framework-specific analysers** - Only if LGPD has unique detection requirements

**Note:** Technical analysers (PersonalData, ProcessingPurpose, DataSubject) require NO changes. The generic findings they produce work for any framework.

### Related Regulations

Regulations in the same "family" (GDPR, UK GDPR, Swiss DPA) share most logic:

- **Option A: Inheritance** - `UKGDPRClassifier(GDPRClassifier)` with overrides
- **Option B: Parameterisation** - `EuropeanDPAClassifier(variant="UK")`
- **Option C: Duplication** - Separate classifiers with copy-paste

**Recommendation:** Start with duplication (Option C). Refactor to inheritance if duplication becomes painful. Premature abstraction is worse than some copy-paste.

## Ruleset as Legal Product

### Vision

Rulesets are not just internal configuration—they are the primary vehicle for legal expertise. Different legal firms can author rulesets that reflect their unique interpretations and methodologies:

- **Firm A** may have a conservative GDPR ruleset with strict classification of special categories
- **Firm B** may have a different interpretation with more nuanced risk levels
- **Firm C** may offer a premium ruleset behind an API as a commercial product

As long as rulesets follow the same schema, runbook authors can choose which one to use.

### Implications

1. **Rulesets include classification rules** - A legal firm's GDPR ruleset contains BOTH detection patterns AND classification logic. This is their complete methodology.

2. **Ruleset providers** - Need abstraction to load rulesets from different sources:

   - Local YAML files (bundled, open source)
   - Remote API (commercial, premium)
   - Organisation-specific (internal legal team's customisations)

3. **Ruleset schema must be stable** - Third parties author against it. Breaking changes require versioning and migration paths.

4. **Analysers are ruleset-agnostic** - The `PersonalDataAnalyser` doesn't know which firm's ruleset it's using. It just consumes whatever ruleset is configured.

5. **Classification is part of the ruleset** - Classification rules are authored by legal experts as part of their ruleset, not as separate framework configuration.

### Ruleset Structure (Conceptual)

A complete ruleset authored by a legal firm might include:

| Section              | Purpose                   | Example                             |
| -------------------- | ------------------------- | ----------------------------------- |
| Detection patterns   | What to look for          | `email`, `health_data`, `biometric` |
| Categories           | How to group detections   | `special_category`, `sensitive_pii` |
| Classification rules | Regulatory interpretation | `health_data → GDPR Article 9`      |
| Risk levels          | Firm's risk methodology   | `health_data → high`                |
| Compliance mappings  | Article references        | `Article 9(2)(a) explicit consent`  |

### Runbook Configuration

Rulesets are specified as analyser properties, following the existing configuration pattern:

```yaml
framework: "GDPR"

artifacts:
  personal_data_findings:
    inputs: source_data
    process:
      type: "personal_data"
      properties:
        ruleset: "firm-a/gdpr-personal-data:2.1.0"

  processing_purpose_findings:
    inputs: source_code
    process:
      type: "processing_purpose"
      properties:
        # Remote premium ruleset
        ruleset: "api://premium-legal.com/gdpr-processing"
```

This approach:

- Follows the existing `properties` pattern for analyser configuration
- Is explicit about which analyser uses which ruleset
- Allows flexibility (different instances could use different rulesets if needed)

### Relationship to Classifier Component

With classification rules in the ruleset, what is the Classifier's role?

- **Classifier** = Framework-specific code (understands GDPR concepts, CCPA concepts, etc.)
- **Ruleset** = Legal expert's knowledge within that framework's structure (data)

Classifiers are **framework-specific** because different regulatory frameworks have fundamentally different classification concepts:

| GDPR                              | CCPA                           | EU AI Act           |
| --------------------------------- | ------------------------------ | ------------------- |
| Special category (Article 9)      | Sensitive personal information | High-risk AI system |
| Legal basis (Article 6)           | "Sale" or "sharing"            | Prohibited practice |
| Cross-border transfer (Chapter V) | Right to opt-out               | Risk category       |

These aren't just different values—they're different concepts and logic that can't be parameterised away.

A legal firm's GDPR ruleset is consumed by the `GDPRClassifier`. The ruleset provides specific values, thresholds, and mappings; the classifier understands GDPR-specific concepts and applies them.

## Related Documents

- [Export Architecture](./export-architecture.md) - Current exporter design (needs update)
- [Business Logic Centric Analysers](./business-logic-centric-analysers.md) - Related design thinking
- [DAG Orchestration Layer](./dag-orchestration-layer.md) - Execution model for pipelines

## Revision History

| Date       | Author | Changes                            |
| ---------- | ------ | ---------------------------------- |
| 2025-12-30 | -      | Initial design discussion captured |
