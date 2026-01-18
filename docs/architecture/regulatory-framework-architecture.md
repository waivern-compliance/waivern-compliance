# Regulatory Framework Architecture

- **Status:** Implemented (Foundation)
- **Last Updated:** 2026-01-18
- **Related:** [Export Architecture](../future-plans/export-architecture.md), [Business Logic Centric Analysers](../future-plans/business-logic-centric-analysers.md)

## Overview

This document describes the architectural approach for handling regulatory framework-specific knowledge and logic within WCF. It establishes principles for separating technical analysis from regulatory interpretation, and defines clear ownership boundaries between components.

## Architecture

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

## Design Principles

### Principle 1: Framework-Agnostic Core

The core of WCF is a set of tools usable across different regulatory frameworks. Technical analysis (detecting personal data, identifying processing purposes, classifying data subjects) is fundamentally the same regardless of which regulation applies.

**Implication:** Connectors and technical analysers do not contain regulation-specific logic. They answer "what exists" not "what does regulation X say about it."

### Principle 2: Analyser-Centric Organisation

The primary organisation is by analysis type (personal data, processing purposes, data subjects), not by regulation (GDPR module, CCPA module). This reflects the reality that many regulations require similar technical analyses.

**Implication:** A single `PersonalDataAnalyser` works for any framework, avoiding duplication across `GDPRPersonalDataAnalyser`, `CCPAPersonalDataAnalyser`, etc.

### Principle 3: Regulation-Centric Aggregation at Export

Regulation-specific formatting and aggregation happens at the export layer, not the analysis layer. The exporter understands how to present findings according to a specific regulation's requirements.

**Implication:** A GDPR exporter knows how to format an Article 30 Record of Processing Activities. It consumes classified findings and produces regulation-compliant output.

### Principle 4: Classification After Technical Analysis

Technical detection completes before regulatory interpretation begins:

1. Technical analysers output generic findings ("found health data")
2. Classifiers enrich with regulatory context ("GDPR Article 9 special category")
3. Exporters format for compliance documentation

**Implication:** Classifiers sit between technical analysers and export. They apply framework-specific interpretation rules to generic findings.

### Principle 5: Framework-Specific Analysers When Necessary

Some analyses are inherently framework-specific and cannot be generalised:

- GDPR Right to Erasure analysis
- GDPR Data Transfer Impact Assessment
- CCPA Opt-Out mechanism detection

**Implication:** Framework-specific analysers own both detection AND classification internally. They don't need a separate classifier step because the analysis is already framework-bound.

### Principle 6: Single Framework Per Runbook

A runbook targets a single regulatory framework. Cross-framework comparison is a reporting concern, handled by running separate runbooks.

**Implication:** The runbook declares its framework at the root level via the `framework` field. This becomes the context for the entire execution pipeline.

## Component Responsibilities

### Rulesets

Rulesets are authored by legal experts and contain detection patterns and classification rules. They are exchangeable products—different legal firms can author different rulesets for the same framework, and runbook authors choose which to use.

Rulesets are specified via URI format: `{provider}/{name}/{version}` (e.g., `local/personal_data/1.0.0`).

### Technical Analysers

**Responsibility:** Detect technical facts without regulatory interpretation.

**Input:** Raw data (standard_input, source_code, database schemas)

**Output:** Generic findings with:

- What was detected (category, patterns matched)
- Where it was found (location, evidence)
- Confidence level

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

**Characteristics:**

- Cannot be reused across frameworks
- Classification happens internally
- Named with framework prefix (e.g., `gdpr_data_transfer`)

### Exporters

**Responsibility:** Format classified findings into compliance documentation.

**Input:** Classified findings (from classifiers or framework-specific analysers)

**Output:** Regulation-compliant documents (JSON, PDF, XML)

## Key Design Decisions

### Runbook Declares Framework

Framework is declared in the runbook root, not inferred from components. This is explicit and unambiguous.

### Runbook Authors Select Analysers

The framework does not validate which analysers can be used. Child runbooks and templates provide guidance without enforcement.

### Classification as Separate Component Type

Classifiers are a distinct component type (like Analysers, Connectors) that run after technical analysis. This enables:

- Clear separation of technical detection and regulatory interpretation
- Easy addition of new frameworks (create new classifier, don't touch technical analysers)
- Independent testing of classification logic

### LLM Validation on Technical Findings

LLM validation happens on technical findings, before classification. The LLM filters false positives ("is this really an email address?"), not regulatory judgments.

### Schema as Contract

Schema versioning and integration tests enforce the contract between technical analysers and classifiers. Prefer specific schemas over generic ones; each framework may need its own finding schema.

### Classifiers Invoked Explicitly

Classifiers are explicit artifacts in the runbook, added by the runbook author as a processing step. No magic injection or hidden behaviour.

## Adding a New Regulation

To add support for a new regulation (e.g., Brazil LGPD):

1. **Create classifier** - `LGPDClassifier` that understands LGPD-specific concepts
2. **Create rulesets** - Detection patterns and classification rules for LGPD
3. **Create exporter** - `LGPDExporter` for LGPD-compliant documentation
4. **Create runbook templates** - Pre-built runbooks for common LGPD assessments
5. **Optionally create framework-specific analysers** - Only if LGPD has unique detection requirements

Technical analysers (PersonalData, ProcessingPurpose, DataSubject) require no changes.

### Related Regulations

Regulations in the same "family" (GDPR, UK GDPR, Swiss DPA) share most logic:

- **Option A: Inheritance** - `UKGDPRClassifier(GDPRClassifier)` with overrides
- **Option B: Parameterisation** - `EuropeanDPAClassifier(variant="UK")`
- **Option C: Duplication** - Separate classifiers with copy-paste

**Recommendation:** Start with duplication. Refactor to inheritance if duplication becomes painful.

## Ruleset as Legal Product

### Vision

Rulesets are the primary vehicle for legal expertise. Different legal firms can author rulesets that reflect their unique interpretations:

- **Firm A** may have a conservative GDPR ruleset with strict classification
- **Firm B** may have a different interpretation with more nuanced risk levels
- **Firm C** may offer a premium ruleset behind an API

### Ruleset Providers

Rulesets can be loaded from different sources:

- Local YAML files (bundled, open source)
- Remote API (commercial, premium)
- Organisation-specific (internal legal team's customisations)

### Runbook Configuration

Rulesets are specified as analyser properties:

```yaml
framework: "GDPR"

artifacts:
  personal_data_findings:
    inputs: source_data
    process:
      type: "personal_data"
      properties:
        ruleset: "local/personal_data/1.0.0"
```

### Relationship to Classifier

- **Classifier** = Framework-specific code (understands GDPR concepts, CCPA concepts, etc.)
- **Ruleset** = Legal expert's knowledge within that framework's structure (data)

Different frameworks have fundamentally different classification concepts:

| GDPR                              | CCPA                           | EU AI Act           |
| --------------------------------- | ------------------------------ | ------------------- |
| Special category (Article 9)      | Sensitive personal information | High-risk AI system |
| Legal basis (Article 6)           | "Sale" or "sharing"            | Prohibited practice |
| Cross-border transfer (Chapter V) | Right to opt-out               | Risk category       |

A legal firm's GDPR ruleset is consumed by the `GDPRClassifier`. The ruleset provides specific values, thresholds, and mappings; the classifier understands GDPR-specific concepts and applies them.

## Related Documents

- [Export Architecture](../future-plans/export-architecture.md) - Exporter design and selection
- [Business Logic Centric Analysers](../future-plans/business-logic-centric-analysers.md) - Related design thinking
- [Artifact-Centric Orchestration](artifact-centric-orchestration.md) - Execution model for pipelines
