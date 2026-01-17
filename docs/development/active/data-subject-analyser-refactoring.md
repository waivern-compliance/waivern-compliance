# DataSubjectAnalyser Refactoring Plan

**Status**: Draft
**Created**: 2026-01-17
**Branch**: `feature/enable-analyser-validation-orchestrators`

## Overview

Refactor the DataSubjectAnalyser to follow the two-tier architecture pattern established by PersonalDataAnalyser + GDPRPersonalDataClassifier. This separates concerns between framework-agnostic detection and GDPR-specific classification.

## Current Architecture

```
DataSubjectAnalyser (monolithic)
├── Input: standard_input:1.0.0
├── Output: data_subject_finding:1.0.0
├── Ruleset: data_subjects/1.0.0 (mixed detection + GDPR context)
└── GDPR-specific fields embedded in output
```

### Current Issues

1. **Mixed Concerns**: Detection and GDPR classification are coupled in one component
2. **Limited Extensibility**: Cannot easily add other frameworks (CCPA, LGPD)
3. **Inconsistent Pattern**: Doesn't follow the established PersonalData pattern
4. **Blocked LLM Validation**: Modifiers detection awaiting LLM integration

## Target Architecture

```
┌─────────────────────────┐     ┌──────────────────────────────┐
│  DataSubjectAnalyser    │────▶│  GDPRDataSubjectClassifier   │
│  (Detection)            │     │  (Enrichment)                │
├─────────────────────────┤     ├──────────────────────────────┤
│ Input: standard_input   │     │ Input: data_subject_indicator│
│ Output: data_subject_   │     │ Output: gdpr_data_subject    │
│         indicator       │     │                              │
│ Ruleset: data_subject_  │     │ Ruleset: gdpr_data_subject_  │
│          indicator      │     │          classification      │
└─────────────────────────┘     └──────────────────────────────┘
```

## Implementation Phases

### Phase 1: Rename Schema and Update Analyser

**Objective**: Rename `data_subject_finding` to `data_subject_indicator` for semantic consistency.

**Tasks**:

1. Create new JSON schema `data_subject_indicator/1.0.0`
   - Copy from `data_subject_finding/1.0.0`
   - Update name and description
   - **Remove `modifiers` field** - This is a GDPR-specific concept (Article 8 minors, Recital 75 vulnerable individuals) that belongs in the classifier layer

2. Rename output models
   - `DataSubjectFindingModel` → `DataSubjectIndicatorModel`
   - `DataSubjectFindingOutput` → `DataSubjectIndicatorOutput`
   - `DataSubjectFindingMetadata` → `DataSubjectIndicatorMetadata`
   - `DataSubjectFindingSummary` → `DataSubjectIndicatorSummary`

3. Update schema registration in `__init__.py`

4. Update all internal references (result_builder, analyser, tests)

5. Deprecate old schema
   - Keep `data_subject_finding:1.0.0` as alias (optional)
   - Add deprecation notice

### Phase 2: Split Ruleset

**Objective**: Separate detection patterns from GDPR classification mappings.

**Tasks**:

1. Rename existing ruleset
   - `data_subjects/1.0.0` → `data_subject_indicator/1.0.0`
   - Keep detection patterns unchanged
   - Remove GDPR-specific metadata (if any)

2. Create classification ruleset `gdpr_data_subject_classification/1.0.0`
   - Structure similar to `gdpr_personal_data_classification`
   - Map subject categories to GDPR concepts:

```yaml
name: gdpr_data_subject_classification
version: 1.0.0
description: Maps data subject indicators to GDPR classification

default_article_references:
  - "Article 4(1)"
  - "Article 30(1)(c)"

rules:
  - name: "Employees"
    indicator_categories: [employee, former_employee, contractor]
    data_subject_category: "employee"
    article_references: ["Article 4(1)", "Article 6(1)(b)", "Article 30(1)(c)"]
    typical_lawful_bases: ["contract", "legal_obligation"]

  - name: "Job Applicants"
    indicator_categories: [job_applicant]
    data_subject_category: "job_applicant"
    article_references: ["Article 4(1)", "Article 6(1)(b)"]
    typical_lawful_bases: ["consent", "contract"]

  - name: "Customers"
    indicator_categories: [customer, former_customer, prospect]
    data_subject_category: "customer"
    article_references: ["Article 4(1)", "Article 6"]
    typical_lawful_bases: ["contract", "legitimate_interests"]

  # ... additional mappings for all 23 categories

risk_modifiers:
  risk_increasing:
    - pattern: "minor|child|under.*years"
      modifier: "minor"
      article_references: ["Article 8"]
    - pattern: "vulnerable"
      modifier: "vulnerable_individual"
      article_references: ["Recital 75"]
  risk_decreasing:
    - pattern: "non-EU|third.country"
      modifier: "non_eu_resident"
```

### Phase 3: Create GDPRDataSubjectClassifier Package

**Objective**: Create a new package following the GDPRPersonalDataClassifier pattern.

**Package Structure**:
```
libs/waivern-gdpr-data-subject-classifier/
├── pyproject.toml
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── src/waivern_gdpr_data_subject_classifier/
│   ├── __init__.py
│   ├── classifier.py          # GDPRDataSubjectClassifier
│   ├── factory.py             # GDPRDataSubjectClassifierFactory
│   ├── result_builder.py      # Output construction
│   ├── ruleset.py             # Cached ruleset loading
│   └── schemas/
│       ├── __init__.py
│       ├── types.py           # GDPRDataSubjectFindingModel
│       └── json_schemas/
│           └── gdpr_data_subject/1.0.0/gdpr_data_subject.json
└── tests/
    ├── conftest.py
    ├── test_classifier.py
    └── test_contract.py
```

**Output Schema** (`gdpr_data_subject:1.0.0`):
```python
class GDPRDataSubjectFindingModel(BaseFindingModel):
    # From indicator (propagated)
    indicator_id: str
    indicator_category: str  # Original category from indicator
    evidence: list[BaseFindingEvidence]
    matched_patterns: list[str]
    confidence_score: int

    # GDPR-specific enrichment
    data_subject_category: str  # Normalised GDPR category
    article_references: tuple[str, ...]  # e.g., ("Article 4(1)", "Article 30(1)(c)")
    typical_lawful_bases: tuple[str, ...]  # e.g., ("contract", "legal_obligation")
    risk_modifiers: list[str]  # e.g., ["minor", "vulnerable_individual"]
    # NOTE: risk_modifiers moved here from DataSubjectIndicatorModel.modifiers
    # These are GDPR-specific concepts: Article 8 (children), Recital 75 (vulnerable)

    metadata: GDPRDataSubjectFindingMetadata | None
```

### Phase 4: Update Runbooks and Documentation

**Tasks**:

1. Update sample runbooks to use new two-stage pipeline
2. Update documentation to reflect new architecture
3. Add migration guide for existing consumers

## File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `libs/waivern-gdpr-data-subject-classifier/` | New classifier package |
| `libs/waivern-rulesets/.../gdpr_data_subject_classification/1.0.0/` | Classification ruleset |
| `libs/waivern-data-subject-analyser/.../data_subject_indicator/1.0.0/` | Renamed schema |

### Modified Files

| File | Changes |
|------|---------|
| `libs/waivern-data-subject-analyser/src/.../schemas/types.py` | Rename models |
| `libs/waivern-data-subject-analyser/src/.../analyser.py` | Update schema reference |
| `libs/waivern-data-subject-analyser/src/.../result_builder.py` | Update model names |
| `libs/waivern-data-subject-analyser/src/.../__init__.py` | Update exports |
| `libs/waivern-rulesets/.../data_subjects/` | Rename to `data_subject_indicator/` |
| Root `pyproject.toml` | Add new package to workspace |

### Deprecated Files

| File | Action |
|------|--------|
| `data_subject_finding/1.0.0/` schema | Keep as deprecated alias or remove |

## Testing Strategy

1. **Unit Tests**: Update existing tests to use new model names
2. **Contract Tests**: Inherit from `ClassifierContractTests` for new classifier
3. **Integration Tests**: Test full pipeline (Analyser → Classifier)
4. **Regression Tests**: Ensure output semantics unchanged for detection

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing runbooks | Provide migration guide; consider deprecation period |
| Schema version confusion | Clear naming: `indicator` = detection, `gdpr_*` = enriched |
| Ruleset duplication | Detection ruleset is reused; only classification is new |

## Success Criteria

1. DataSubjectAnalyser outputs `data_subject_indicator:1.0.0`
2. GDPRDataSubjectClassifier enriches to `gdpr_data_subject:1.0.0`
3. All existing tests pass (with updated expectations)
4. New classifier has contract test coverage
5. Sample runbook demonstrates two-stage pipeline

## Dependencies

- Completion of Phase 2 LLM validation infrastructure (done)
- PersonalDataAnalyser + GDPRPersonalDataClassifier as reference (exists)

## Future Work

After this refactoring:
1. Add LLM validation to DataSubjectAnalyser (validate detected categories)
2. Add LLM validation to GDPRDataSubjectClassifier (detect risk_modifiers like "minor", "vulnerable")
3. Consider CCPADataSubjectClassifier for California compliance
