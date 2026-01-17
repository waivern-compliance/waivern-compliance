# LLM Validation Strategies Architecture

Generic, reusable LLM validation strategies for all analysers.

## Overview

This architecture enables any analyser to use shared LLM validation strategies with configurable by implementing simple protocols.

## Configuration

```python
LLMValidationConfig(
    # Grouping & Sampling (user-facing)
    grouping: Literal[None, "by_source", "by_concern"] = None,
    sampling_size: int | None = None,  # Requires grouping != None

    # Batching parameters (tuning, rarely changed)
    model_context_window: int = 200_000,
    prompt_overhead_tokens: int = 3000,
    output_ratio: float = 0.15,
    safety_buffer: float = 0.2,
)
```

### Grouping Strategies

| Strategy     | Description                                  | Use Case                          |
| ------------ | -------------------------------------------- | --------------------------------- |
| `None`       | No grouping - validate each finding          | Full validation, maximum accuracy |
| `by_source`  | Group by origin (file, table cell, endpoint) | When source context matters       |
| `by_concern` | Group by compliance attribute                | Cost-effective sampling           |

#### Source vs Concern: Conceptual Relationship

Conceptually, **"source" is a type of concern** - both are just ways to bucket findings for
group-level decisions. The key difference is practical, not conceptual:

| Aspect                    | `by_concern`                                           | `by_source`                                 |
| ------------------------- | ------------------------------------------------------ | ------------------------------------------- |
| **Grouping key**          | Domain-specific attribute (`purpose`, `data_category`) | Location identifier (file path, table name) |
| **Findings per group**    | May span multiple source files                         | All from same source                        |
| **LLM context available** | Evidence snippets only                                 | Full source content possible                |
| **Decision semantics**    | "All _Payment Processing_ findings are FP"             | "All findings in _config.py_ are FP"        |
| **Question answered**     | "Is this type of compliance issue real?"               | "Is this source relevant for analysis?"     |

**Why source is special**: When findings share a source, the `SourceProvider` can return full
file content via `get_source_content()`. This enables richer LLM context - the model sees the
complete file rather than isolated snippets, leading to better validation accuracy.

This is why the choice of grouping strategy influences which `LLMValidationStrategy` is optimal:

| Grouping     | Typical LLM Strategy                   | Rationale                                    |
| ------------ | -------------------------------------- | -------------------------------------------- |
| `by_concern` | `DefaultLLMValidationStrategy`         | Findings span files; only snippets available |
| `by_source`  | `ExtendedContextLLMValidationStrategy` | Can batch by source with extended context    |

The strategies are orthogonal - `GroupingStrategy` decides how to organise findings for sampling,
while `LLMValidationStrategy` decides how to batch and what context to include in prompts.

### Configuration Matrix

| `grouping`   | `sampling_size` | Behaviour                                  |
| ------------ | --------------- | ------------------------------------------ |
| `None`       | `None`          | Validate all findings individually         |
| `None`       | `3`             | Invalid - ignore `sampling_size` config    |
| `by_source`  | `None`          | Group by source, validate all with context |
| `by_source`  | `3`             | Group by source, sample 3 per source       |
| `by_concern` | `None`          | Group by concern, validate all             |
| `by_concern` | `3`             | Group by concern, sample 3 per group       |

### Context Inclusion (Protocol-Driven)

Whether full source content is included in prompts is determined by the `SourceProvider` protocol:

- **`by_source` grouping**: If `SourceProvider.get_source_content()` returns content, include it. Otherwise, use evidence snippets only.
- **`by_concern` grouping**: Always use evidence snippets (findings span multiple sources).
- **`grouping=None`**: Use evidence snippets only.

## Analyser Protocols

Each analyser implements these protocols to define what "source" and "concern" mean.

All protocols and strategies use `BaseFindingModel` as a type bound, ensuring type safety
and guaranteeing access to standard finding fields (`id`, `evidence`, `matched_patterns`).

```python
from waivern_core.schemas.finding_types import BaseFindingModel

class SourceProvider[T: BaseFindingModel](Protocol):
    """Provides source content for validation context."""

    def get_source_id(self, finding: T) -> str:
        """Extract source identifier from a finding

        A finding may not contain the complete source context.
        """
        ...

    def get_source_content(self, source_id: str) -> str | None:
        """Return the content of the source (file, table schema, etc.)."""
        ...


class ConcernProvider[T: BaseFindingModel](Protocol):
    """Defines what the 'compliance concern' is for this analyser."""

    @property
    def concern_key(self) -> str:
        """The attribute name for output metadata (e.g., 'purpose', 'data_category')."""
        ...

    def get_concern(self, finding: T) -> str:
        """Extract the concern value from a finding.

        May be a simple attribute access or derived from multiple attributes.
        Used for grouping findings.
        """
        ...
```

### Analyser Implementations

| Analyser           | Source (`get_source_id`)              | `concern_key`     | `get_concern()` returns (example) |
| ------------------ | ------------------------------------- | ----------------- | --------------------------------- |
| Processing Purpose | `finding.metadata.source` (file path) | `"purpose"`       | `"Payment Processing"`            |
| Personal Data      | `finding.metadata.source` (file path) | `"data_category"` | `"Email Address"`                 |
| Data Subject       | `finding.metadata.source` (file path) | `"subject_type"`  | `"Customer"`                      |
| Database (future)  | Table name or Table cell              | `"purpose"`       | `"Payment Processing"`            |

## Information Flow (when grouping is enabled)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PATTERN MATCHING PHASE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Input Data ──────► Pattern Matcher ──────► All Findings                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GROUPING PHASE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Strategy: by_concern                                                      │
│   Provider: ConcernProvider.get_concern(finding)                            │
│                                                                             │
│   All Findings ──────► Group by Concern ──────► Concern Groups              │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Groups (Processing Purpose example):                             │      │
│   │   "Payment Processing"     → 150 findings                        │      │
│   │   "Customer Service"       → 89 findings                         │      │
│   │   "Documentation Example"  → 45 findings                         │      │
│   │   "Analytics Tracking"     → 234 findings                        │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Groups (Personal Data example):                                  │      │
│   │   "Email Address"          → 230 findings                        │      │
│   │   "Phone Number"           → 156 findings                        │      │
│   │   "IP Address"             → 89 findings                         │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│          SAMPLING PHASE (when sampling is enabled)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   For each Group:                                                           │
│     - If findings >= sampling_size: randomly pick N samples                 │
│     - If findings < sampling_size: use all findings as samples              │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ Sampled Findings:                                                │      │
│   │   "Payment Processing"     → 3 samples (from 150)                │      │
│   │   "Customer Service"       → 3 samples (from 89)                 │      │
│   │   "Documentation Example"  → 3 samples (from 45)                 │      │
│   │   ... (N samples per group)                                      │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LLM VALIDATION PHASE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Sampled/non-sampled findings batched by token limits, sent to LLM.        │
│   (`1By_source` will ensure findings per source are always batched together)│
│   LLM returns validation results (ONLY return FALSE_POSITIVE).              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DECISION PHASE                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   For each Group, evaluate sampled findings:                                │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE A: ALL samples are FALSE_POSITIVE                              │   │
│   │                                                                     │   │
│   │   Group "Documentation Example" (3 samples):                        │   │
│   │     - sample-1: FALSE_POSITIVE ✗                                    │   │
│   │     - sample-2: FALSE_POSITIVE ✗                                    │   │
│   │     - sample-3: FALSE_POSITIVE ✗                                    │   │
│   │                                                                     │   │
│   │   ACTION: Remove ENTIRE group (all 45 findings)                     │   │
│   │           Flag for human review                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE B: SOME samples are FALSE_POSITIVE                             │   │
│   │                                                                     │   │
│   │   Group "Test Data" (3 samples):                                    │   │
│   │     - sample-1: FALSE_POSITIVE ✗  → Remove this finding             │   │
│   │     - sample-2: FALSE_POSITIVE ✗  → Remove this finding             │   │
│   │     - sample-3: TRUE_POSITIVE ✓   → Keep, mark validated            │   │
│   │                                                                     │   │
│   │   ACTION: Keep group (at least one TRUE_POSITIVE exists)            │   │
│   │           Remove only the FALSE_POSITIVE samples                    │   │
│   │           Keep non-sampled findings (by inference)                  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ CASE C: NO samples are FALSE_POSITIVE                               │   │
│   │                                                                     │   │
│   │   Group "Payment Processing" (3 samples):                           │   │
│   │     - sample-1: TRUE_POSITIVE ✓  → Keep, mark validated             │   │
│   │     - sample-2: TRUE_POSITIVE ✓  → Keep, mark validated             │   │
│   │     - sample-3: TRUE_POSITIVE ✓  → Keep, mark validated             │   │
│   │                                                                     │   │
│   │   ACTION: Keep entire group                                         │   │
│   │           Mark sampled findings as validated                        │   │
│   │           Keep non-sampled findings (by inference, NOT validated)   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ SKIPPED SAMPLES HANDLING                                            │   │
│   │                                                                     │   │
│   │   Samples that couldn't be validated (oversized, missing content,   │   │
│   │   batch error) are EXCLUDED from group-level decisions.             │   │
│   │                                                                     │   │
│   │   Only validated samples (kept + removed) count for Case A/B/C.     │   │
│   │   Skipped samples are kept in the group (conservative approach).    │   │
│   │   Caller can handle skipped_samples via ValidationResult.           │   │
│   │                                                                     │   │
│   │   If ALL samples are skipped → keep entire group (no decision).     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT PHASE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Final Findings:                                                           │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │ [                                                                │      │
│   │   {                                                              │      │
│   │     "id": "finding-001",                                         │      │
│   │     "metadata": {                                                │      │
│   │       "context": { "<analyser>_llm_validated": true }            │      │
│   │     }                              ← Sampled & validated         │      │
│   │   },                                                             │      │
│   │   {                                                              │      │
│   │     "id": "finding-002",                                         │      │
│   │     "metadata": { }                ← Kept by inference           │      │
│   │   },                                                             │      │
│   │ ]                                                                │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Design Philosophy

**Group-level validation is sufficient for compliance analysis.**

For GDPR and similar regulations, what matters is whether a compliance concern exists in the codebase - not how many times a pattern matched. If "Payment Processing" appears 150 times, validating 3 representative samples tells us whether the concern is legitimate.

### Validation Marking Rule

Only sampled findings that are TRUE_POSITIVE get marked as `<analyser>_llm_validated: true`:

```
Group "Payment Processing" (150 findings, 3 sampled):
  - 3 sampled findings → marked as validated (if TRUE_POSITIVE)
  - 147 other findings → no validation mark (kept by inference)
```

This is honest about what was actually checked. Auditors can see "3 directly validated, 147 inferred".

## Output Schema

```yaml
summary:
  total_findings: 13927 # After validation
  <concern_type>_identified: 26 # e.g., purposes_identified, data_categories_identified

  # Per-group breakdown
  <groups>: # e.g., purposes, data_categories
    - <group_name>: "Payment Processing"
      findings_count: 150

analysis_metadata:
  llm_validation_enabled: true

  validation_summary:
    grouping: "by_concern" # or "by_source", null
    grouping_attribute: "purpose" # or "data_category", "subject_type"
    samples_per_group: 3
    samples_validated: 81

  groups_removed: # Flagged for human review
    - concern_key: "purpose"
      concern_value: "Documentation Example"
      findings_count: 45
      samples_validated: 2 # Could be 1, 2 ... up to sampling_size
      reason: "All sampled findings are false positives"
      require_review: true
```

## Implementation Structure

```
waivern-analysers-shared/
└── llm_validation/
    ├── strategy.py                    # LLMValidationStrategy - abstract base class
    │   ├── LLMValidationStrategy[T]   # Base class with validate_findings() interface
    │   ├── DefaultLLMValidationStrategy[T]          # Batches by count, evidence snippets
    │   └── ExtendedContextLLMValidationStrategy[T]  # Batches by source, extended context
    ├── grouping.py                    # GroupingStrategy implementations
    │   ├── GroupingStrategy[T]        # Abstract protocol
    │   ├── SourceGroupingStrategy[T]  # grouping="by_source"
    │   └── ConcernGroupingStrategy[T] # grouping="by_concern"
    ├── sampling.py                    # SamplingStrategy
    │   └── RandomSamplingStrategy[T]  # Sample N per group
    ├── protocols.py                   # SourceProvider, ConcernProvider
    └── validation_orchestrator.py     # Orchestrates grouping → sampling → LLM → decisions

waivern-processing-purpose-analyser/
└── validation/
    └── providers.py                   # ProcessingPurposeSourceProvider, ProcessingPurposeConcernProvider
```

### LLM Validation Strategy Hierarchy

The analyser decides which LLM validation strategy to use based on configuration. The shared
package provides a base class and common implementations; analysers can create bespoke strategies
if domain-specific prompt generation or batching logic is required.

```
LLMValidationStrategy[T: BaseFindingModel] (abstract base)
    │
    │   validate_findings(findings, config, llm_service) -> LLMValidationOutcome[T]
    │   get_validation_prompt(batch, config) -> str  [abstract]
    │
    ├── DefaultLLMValidationStrategy[T]
    │       Batches by fixed count (llm_batch_size)
    │       Prompt contains evidence snippets only
    │       Use for: general validation, by_concern grouping
    │
    └── ExtendedContextLLMValidationStrategy[T]
            Batches by source, extends prompt with source content
            Use for: by_source grouping when SourceProvider has content

LLMValidationOutcome[T] provides detailed breakdown:
    - llm_validated_kept: Findings LLM confirmed as TRUE_POSITIVE
    - llm_validated_removed: Findings LLM marked as FALSE_POSITIVE
    - llm_not_flagged: Findings LLM didn't return (fail-safe kept)
    - skipped: Findings that couldn't be validated (oversized, missing content, batch error)
    - kept_findings: Property returning all kept findings (validated + not_flagged + skipped)
    - validation_succeeded: Property indicating all findings were validated (no skipped)
```

**Ownership**: The analyser instantiates the appropriate strategy based on `config.grouping`:

```python
# In analyser.process()
if config.grouping == "by_source" and source_provider.has_content():
    llm_strategy = ExtendedContextLLMValidationStrategy(source_provider, prompt_builder)
else:
    llm_strategy = DefaultLLMValidationStrategy(prompt_builder)
```

The `ValidationOrchestrator` is strategy-agnostic - it accepts any `LLMValidationStrategy`
and delegates batching/LLM calls entirely to the strategy.

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VALIDATION FLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   All Findings                                                              │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 1. GROUPING (optional)                                              │   │
│   │    ├─ grouping=None      → Skip to batching                         │   │
│   │    ├─ grouping=by_source → Group by SourceProvider.get_source_id()  │   │
│   │    └─ grouping=by_concern→ Group by ConcernProvider.get_concern()   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2. SAMPLING (optional, requires grouping)                           │   │
│   │    ├─ sampling_size=None → Use all findings in group                │   │
│   │    └─ sampling_size=N    → Randomly sample N per group              │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 3. BATCHING (always happens - internal)                             │   │
│   │    Chunk findings by token limits (model_context_window)            │   │
│   │    Include source content if by_source + provider returns it        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 4. LLM VALIDATION                                                   │   │
│   │    Send batches to LLM, parse responses                             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 5. DECISION APPLICATION                                             │   │
│   │    ├─ grouping=None    → Individual finding decisions               │   │
│   │    └─ grouping=by_*    → Group-level decisions (see Decision Phase) │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Class Design

All classes use `BaseFindingModel` as a type bound for consistency and type safety.

```python
from waivern_core.schemas.finding_types import BaseFindingModel

class ValidationOrchestrator[T: BaseFindingModel]:
    """Orchestrates the complete validation flow.

    The orchestrator composes orthogonal strategies:
    - GroupingStrategy: How to organize findings (optional, owns concern_key)
    - SamplingStrategy: How to sample from groups (optional, requires grouping)
    - LLMValidationStrategy: How to batch and call the LLM

    Validation flow:
    1. Group findings using GroupingStrategy (if provided)
    2. Sample from groups using SamplingStrategy (if provided)
    3. Flatten all sampled findings into a single list
    4. Validate via llm_strategy.validate_findings() (one call, internally batched)
    5. Match results back to groups by finding ID
    6. Apply group-level decisions (Case A/B/C)
    7. Get concern_key from grouping_strategy for RemovedGroup metadata

    When grouping_strategy is None:
    - Direct validation without grouping or group-level decisions
    - sampling_strategy must also be None (raises ValueError otherwise)
    - Results mapped directly from LLMValidationOutcome

    Why flatten instead of validate per-group?
    HTTP round-trip latency and prompt template token overhead make per-group
    calls expensive. Flattening allows optimal batching; matching back by ID
    is trivial (set operations).
    """

    def __init__(
        self,
        llm_strategy: LLMValidationStrategy[T],
        grouping_strategy: GroupingStrategy[T] | None = None,
        sampling_strategy: SamplingStrategy[T] | None = None,
    ) -> None: ...

    def validate(
        self,
        findings: list[T],
        config: LLMValidationConfig,
        llm_service: BaseLLMService,
    ) -> ValidationResult[T]: ...


class GroupingStrategy[T: BaseFindingModel](Protocol):
    """Groups findings for validation.

    Grouping strategies are orthogonal to LLM validation strategies:
    - GroupingStrategy: How to organize findings for sampling decisions
    - LLMValidationStrategy: How to batch and call the LLM

    The orchestrator composes them - they don't know about each other.
    """

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        """Group findings by some attribute."""
        ...

    @property
    def concern_key(self) -> str:
        """The attribute name used for grouping (e.g., 'purpose', 'source').

        Used by the orchestrator for RemovedGroup metadata.
        """
        ...


class ConcernGroupingStrategy[T: BaseFindingModel]:
    """Groups findings by compliance concern using a provider."""

    def __init__(self, concern_provider: ConcernProvider[T]) -> None:
        self._provider = concern_provider

    @property
    def concern_key(self) -> str:
        return self._provider.concern_key

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        groups: dict[str, list[T]] = defaultdict(list)
        for finding in findings:
            concern = self._provider.get_concern(finding)
            groups[concern].append(finding)
        return groups


class SourceGroupingStrategy[T: BaseFindingModel]:
    """Groups findings by source using a provider."""

    def __init__(self, source_provider: SourceProvider[T]) -> None:
        self._provider = source_provider

    @property
    def concern_key(self) -> str:
        return "source"

    def group(self, findings: list[T]) -> dict[str, list[T]]:
        groups: dict[str, list[T]] = defaultdict(list)
        for finding in findings:
            source_id = self._provider.get_source_id(finding)
            groups[source_id].append(finding)
        return groups


class SamplingStrategy[T: BaseFindingModel](Protocol):
    """Samples findings from groups for validation."""

    def sample(self, groups: dict[str, list[T]]) -> SamplingResult[T]:
        """Sample findings from each group."""
        ...


@dataclass
class SamplingResult[T: BaseFindingModel]:
    """Result of a sampling operation."""

    sampled: dict[str, list[T]]      # Findings selected for LLM validation
    non_sampled: dict[str, list[T]]  # Findings kept by inference


@dataclass
class RemovedGroup:
    """A group removed because all samples were false positives."""

    concern_key: str        # From ConcernProvider.concern_key (e.g., "purpose")
    concern_value: str      # From ConcernProvider.get_concern() (e.g., "Documentation Example")
    findings_count: int     # Total findings in this group before removal
    samples_validated: int  # How many samples were validated
    reason: str             # Why removed
    require_review: bool    # Flag for human review


@dataclass
class ValidationResult[T: BaseFindingModel]:
    """Result of validation orchestration."""

    kept_findings: list[T]              # Findings kept (validated + non-sampled + skipped)
    removed_findings: list[T]           # Individual findings removed (all modes)
    removed_groups: list[RemovedGroup]  # Groups removed (only when grouping enabled)
    samples_validated: int
    all_succeeded: bool
    skipped_samples: list[SkippedFinding[T]]  # Findings that couldn't be validated
```

### Analyser-Specific Components

Each analyser implements:

| Component        | Shared (Abstract)          | Analyser Implementation                                                 |
| ---------------- | -------------------------- | ----------------------------------------------------------------------- |
| LLM Prompts      | `LLMValidationStrategy[T]` | `ProcessingPurposeValidationStrategy`, `PersonalDataValidationStrategy` |
| Source Provider  | `SourceProvider[T]`        | `ProcessingPurposeSourceProvider`                                       |
| Concern Provider | `ConcernProvider[T]`       | `ProcessingPurposeConcernProvider`                                      |

The `ValidationOrchestrator` is generic - analysers inject their specific implementations.

### Usage Pattern

The analyser creates and calls `ValidationOrchestrator` within its `process()` method.
The analyser decides which strategies to use based on configuration:

```python
# In ProcessingPurposeAnalyser.process()

class ProcessingPurposeAnalyser:
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        # 1. Pattern matching
        findings = self._run_pattern_matching(inputs)

        # 2. Analyser decides which strategies to use
        concern_provider = ProcessingPurposeConcernProvider()
        source_provider = ProcessingPurposeSourceProvider(source_data)

        # LLM strategy (always required)
        if config.grouping == "by_source" and source_provider.has_content():
            llm_strategy = ExtendedContextLLMValidationStrategy(source_provider)
        else:
            llm_strategy = DefaultLLMValidationStrategy()

        # Grouping strategy (optional, based on config)
        grouping_strategy: GroupingStrategy | None = None
        if config.grouping == "by_source":
            grouping_strategy = SourceGroupingStrategy(source_provider)
        elif config.grouping == "by_concern":
            grouping_strategy = ConcernGroupingStrategy(concern_provider)

        # Sampling strategy (optional, requires grouping)
        sampling_strategy: SamplingStrategy | None = None
        if grouping_strategy and config.sampling_size:
            sampling_strategy = RandomSamplingStrategy(config.sampling_size)

        # 3. Create orchestrator - strategy-agnostic
        orchestrator = ValidationOrchestrator(
            llm_strategy=llm_strategy,
            grouping_strategy=grouping_strategy,
            sampling_strategy=sampling_strategy,
        )

        # 4. Validate
        result = orchestrator.validate(findings, config, llm_service)

        # 5. Build output
        return self._build_output(result.kept_findings, ...)
```

**Call hierarchy:**

```
Analyser.process()
    │
    ├─► Pattern Matching → All Findings
    │
    └─► ValidationOrchestrator.validate()
            │
            ├─► GroupingStrategy.group()
            ├─► SamplingStrategy.sample()
            ├─► LLMValidationStrategy.validate_findings()  (batching + LLM calls)
            └─► Decision Application
```

## Error Handling

| Scenario                             | Behaviour                                                        |
| ------------------------------------ | ---------------------------------------------------------------- |
| LLM call fails                       | Keep all findings in affected batch, mark `all_succeeded: false` |
| LLM returns unknown finding ID       | Log warning, ignore the unknown ID                               |
| Group has < N sampling_size findings | Use all findings as samples                                      |
| Empty response from LLM              | All samples treated as TRUE_POSITIVE                             |
| Provider not implemented             | Fall back to `grouping="none"`                                   |

## Migration Path

### Phase 1: Current State (Implemented)

- Sampling hardcoded in `ProcessingPurposeAnalyser`
- Works only for processing purpose findings

### Phase 2: Build Shared Infrastructure (Implemented)

- ✅ Create `ValidationOrchestrator` with grouping → sampling → batching → LLM → decisions flow
- ✅ Implement `GroupingStrategy` protocol and `ConcernGroupingStrategy`, `SourceGroupingStrategy`
- ✅ Implement `SamplingStrategy` protocol and `RandomSamplingStrategy`
- ✅ Define `SourceProvider` and `ConcernProvider` protocols
- ✅ Define `RemovedGroup` and `ValidationResult` dataclasses
- ✅ Comprehensive unit tests for all shared components

### Phase 3: Refactor ProcessingPurposeAnalyser (Implemented)

- Implement `ProcessingPurposeConcernProvider`
- Implement `ProcessingPurposeSourceProvider`
- Replace hardcoded sampling logic with `ValidationOrchestrator`
- Verify behaviour matches current implementation (same results)

### Phase 4: Enable Other Analysers

- Personal data analyser implements `ConcernProvider` (by data_category)
- Data subject analyser implements `ConcernProvider` (by subject_type)
- All analysers can use sampling with no code duplication

### Phase 5: Advanced Strategies

- Stratified sampling (by file AND concern)
- Adaptive sampling (more samples for uncertain groups)
- Parallel batch validation for large sample sets
