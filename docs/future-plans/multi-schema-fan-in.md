# Multi-Schema Fan-In Design

- **Status:** Design Proposal
- **Last Updated:** 2025-12-03
- **Related:** [Artifact-Centric Runbook](./artifact-centric-runbook.md), [DAG Orchestration Layer](./dag-orchestration-layer.md)

## Overview

This document describes the design for multi-schema fan-in support in WCF, enabling analysers to consume multiple inputs with different schemas. This is essential for regulatory analysers (e.g., GDPR Article 30) that synthesise findings from multiple upstream analysers.

## Problem

The current analyser contract only supports single-schema input:

```python
def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message:
    """Process single input message."""
```

But regulatory analysers need multiple different schemas:

```yaml
# This should work - inputs have different schemas
gdpr_ropa:
  inputs:
    - personal_data_findings      # personal_data_finding schema
    - processing_purpose_findings  # processing_purpose_finding schema
    - data_subject_findings        # data_subject_finding schema
  transform:
    type: gdpr_article_30          # Needs all three!
```

## Design Principles

1. **Analysers are pure functions** - They don't know about runbooks or orchestration
2. **Runbook controls the blueprint** - Runbook declares what flows where
3. **Schema-driven validation** - All validation at plan time, not runtime
4. **Consistent public API** - One unified interface for single and multi-schema
5. **Consistent patterns** - Multi-schema uses same reader/producer pattern

## Current Analyser Contract

```python
class Analyser(ABC):
    @classmethod
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Auto-discovered from schema_readers/ directory."""

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Auto-discovered from schema_producers/ directory."""

    @abstractmethod
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process single input message."""
```

### Reader/Producer Pattern

**Readers** (`schema_readers/{schema}_{version}.py`):
- Transform wire format → internal canonical model
- Enable version compatibility
- Provide type safety via Pydantic models

```python
# schema_readers/standard_input_1_0_0.py
def read(content: dict[str, Any]) -> StandardInputDataModel:
    return StandardInputDataModel.model_validate(content)
```

**Producers** (`schema_producers/{schema}_{version}.py`):
- Transform internal model → wire format
- Ensure output matches JSON schema

```python
# schema_producers/personal_data_finding_1_0_0.py
def produce(findings, summary, ...) -> dict[str, Any]:
    return {"findings": [...], "summary": {...}, ...}
```

## Proposed Design

### New: Input Requirements Declaration

Analysers declare all valid input combinations they support. Each combination is a distinct set of required schemas:

```python
@dataclass(frozen=True)
class InputRequirement:
    """Declares a required input schema."""
    schema_name: str
    version: str


class Analyser(ABC):
    @classmethod
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Declare supported input schema combinations.

        Returns:
            List of valid input combinations. Each combination is a list of
            InputRequirements representing the schemas that must be provided.
            Multiple messages of the same schema are implicitly allowed.

        Example:
            [
                # Option 1: Single personal_data_finding v1.0.0
                [InputRequirement("personal_data_finding", "1.0.0")],

                # Option 2: Single personal_data_finding v1.1.0
                [InputRequirement("personal_data_finding", "1.1.0")],

                # Option 3: Combined personal_data + processing_purpose
                [
                    InputRequirement("personal_data_finding", "1.0.0"),
                    InputRequirement("processing_purpose_finding", "1.0.0"),
                ],
            ]
        """
        ...
```

**Key points:**
- Replaces `get_supported_input_schemas()`
- Each combination is an **exact set** of required schemas
- Multiple messages of the same schema are implicitly allowed (same-schema fan-in)
- No `required` flag - if a schema is in a combination, it's required for that combination

### New: Unified Processing Method

```python
class Analyser(ABC):
    @abstractmethod
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process input messages.

        Args:
            inputs: List of input messages. May contain multiple messages
                   of the same schema (same-schema fan-in).
            output_schema: Expected output schema.

        Returns:
            Output message.
        """
        ...
```

**Key points:**
- Replaces `process(input_schema, output_schema, message)`
- Single-schema analysers receive `[Message]` (list with one or more items of same schema)
- Multi-schema analysers receive `[Message, Message, ...]` with different schemas
- Analyser inspects `message.schema` to determine processing path

### Internal Routing Pattern

Analysers route to internal handlers based on the schema combination:

```python
def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    schemas = frozenset((msg.schema.name, msg.schema.version) for msg in inputs)

    if schemas == {("personal_data_finding", "1.0.0")}:
        return self._process_personal_data_v1(inputs, output_schema)
    elif schemas == {("personal_data_finding", "1.1.0")}:
        return self._process_personal_data_v1_1(inputs, output_schema)
    elif schemas == {("personal_data_finding", "1.0.0"), ("processing_purpose_finding", "1.0.0")}:
        return self._process_combined(inputs, output_schema)
    else:
        # Safety net - should never hit if Planner validation is correct
        raise ValueError(f"Unexpected schema combination: {schemas}")
```

### Reader Helper Method

```python
class Analyser(ABC):
    def _load_reader_for_schema(self, schema: Schema) -> ModuleType:
        """Load reader module for a specific schema.

        Args:
            schema: The schema to load reader for

        Returns:
            Module with read() function

        Raises:
            ModuleNotFoundError: If no reader exists for this schema/version
        """
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        package = self.__class__.__module__.rsplit('.', 1)[0]
        return importlib.import_module(f"{package}.schema_readers.{module_name}")
```

### ComponentFactory Update

```python
class ComponentFactory[T](ABC):
    # Existing methods...

    def get_input_requirements(self) -> list[list[InputRequirement]]:
        """Get supported input schema combinations."""
        ...
```

## Matching Logic

The Planner uses **exact set matching** on unique schemas:

1. Collect the **set of unique (schema_name, version)** from provided inputs
2. Check if this set matches any declared requirement combination
3. "Match" means the sets are equal (same schemas, regardless of message count)

```python
# Requirement: [InputRequirement("personal_data_finding", "1.0.0")]
# Provided: 1 personal_data_finding → ✓ matches
# Provided: 3 personal_data_findings → ✓ matches (same schema set)
# Provided: 1 personal_data + 1 processing_purpose → ✗ unexpected schema

# Requirement: [InputRequirement("personal_data_finding", "1.0.0"),
#               InputRequirement("processing_purpose_finding", "1.0.0")]
# Provided: 1 of each → ✓ matches
# Provided: 2 personal_data + 1 processing_purpose → ✓ matches
# Provided: only personal_data → ✗ missing required schema
```

## Execution Flow

```
Planner:
  - get_input_requirements() → [[InputRequirement, ...], ...]
  - Collect unique schemas from runbook inputs
  - Find matching requirement combination (exact set match)
  - Validate readers exist for all schemas
  - artifact_schemas[id] = (matched_requirement, output_schema)

Executor:
  - Collect inputs: [Message, ...]
  - Call analyser.process(inputs, output_schema)

Analyser.process():
  - Determine schema combination from inputs
  - Route to appropriate internal handler
  - For each input, load reader by message.schema
  - reader.read(content) → typed internal model
  - Business logic with typed models
  - producer.produce(...) → wire format
  - Return Message
```

## Planner Validation

```python
def _resolve_derived_schema(
    self,
    artifact_id: str,
    definition: ArtifactDefinition,
    resolved: dict[str, tuple[Any, Schema]],
) -> tuple[list[InputRequirement], Schema]:
    """Resolve schemas for a derived artifact."""
    input_refs = self._normalise_inputs(definition.inputs)
    provided_set = self._collect_provided_schemas(input_refs, resolved)

    factory = self._registry.analyser_factories[definition.transform.type]
    requirements = factory.get_input_requirements()

    matched = self._find_matching_requirement(
        artifact_id, provided_set, requirements
    )
    self._validate_readers_exist(artifact_id, factory, matched)

    output_schema = self._get_output_schema(factory, definition)
    return (matched, output_schema)


def _collect_provided_schemas(
    self,
    input_refs: list[str],
    resolved: dict[str, tuple[Any, Schema]],
) -> frozenset[tuple[str, str]]:
    """Collect unique (schema_name, version) tuples from resolved inputs."""
    input_schemas = {resolved[ref][1] for ref in input_refs}
    return frozenset((s.name, s.version) for s in input_schemas)


def _find_matching_requirement(
    self,
    artifact_id: str,
    provided_set: frozenset[tuple[str, str]],
    requirements: list[list[InputRequirement]],
) -> list[InputRequirement]:
    """Find a requirement combination that exactly matches provided schemas."""
    for req_combination in requirements:
        req_set = frozenset((r.schema_name, r.version) for r in req_combination)
        if req_set == provided_set:
            return req_combination

    available = [
        {(r.schema_name, r.version) for r in combo}
        for combo in requirements
    ]
    raise SchemaCompatibilityError(
        f"Artifact '{artifact_id}': no matching input requirement. "
        f"Provided: {provided_set}, Available: {available}"
    )


def _validate_readers_exist(
    self,
    artifact_id: str,
    factory: ComponentFactory,
    requirements: list[InputRequirement],
) -> None:
    """Validate analyser has readers for all required schemas."""
    supported_inputs = factory.get_input_schemas()
    supported_set = {(s.name, s.version) for s in supported_inputs}

    for req in requirements:
        if (req.schema_name, req.version) not in supported_set:
            raise ComponentNotFoundError(
                f"Artifact '{artifact_id}': analyser declares requirement for "
                f"'{req.schema_name}/{req.version}' but has no reader for it"
            )
```

## Executor Handling

```python
async def _produce_derived(
    self,
    artifact_id: str,
    definition: ArtifactDefinition,
    plan: ExecutionPlan,
    ctx: _ExecutionContext,
) -> Message:
    """Produce a derived artifact from its inputs."""
    input_refs = self._normalise_inputs(definition.inputs)

    # Retrieve input messages from store
    input_messages = [ctx.store.get(ref) for ref in input_refs]

    # Get output schema from plan
    _, output_schema = plan.artifact_schemas[artifact_id]

    factory = self._registry.analyser_factories[definition.transform.type]

    def sync_process() -> Message:
        analyser = factory.create(definition.transform.properties)
        return analyser.process(input_messages, output_schema)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(ctx.thread_pool, sync_process)
```

## Contract Testing

A base test class validates analyser implementations:

```python
class AnalyserContractTest(ABC):
    """Base test class for analyser contract validation."""

    @abstractmethod
    def get_analyser_factory(self) -> ComponentFactory[Analyser]:
        """Return the analyser factory to test."""
        ...

    def test_input_requirements_not_empty(self):
        """Input requirements must have at least one combination."""
        factory = self.get_analyser_factory()
        requirements = factory.get_input_requirements()
        assert len(requirements) > 0, "get_input_requirements() must return at least one combination"

    def test_no_duplicate_combinations(self):
        """Each combination must be unique."""
        factory = self.get_analyser_factory()
        requirements = factory.get_input_requirements()

        seen = set()
        for combo in requirements:
            combo_set = frozenset((r.schema_name, r.version) for r in combo)
            assert combo_set not in seen, f"Duplicate combination: {combo_set}"
            seen.add(combo_set)

    def test_readers_exist_for_all_requirements(self):
        """Readers must exist for all declared input schemas."""
        factory = self.get_analyser_factory()
        requirements = factory.get_input_requirements()
        supported = factory.get_input_schemas()
        supported_set = {(s.name, s.version) for s in supported}

        for combo in requirements:
            for req in combo:
                assert (req.schema_name, req.version) in supported_set, (
                    f"No reader for {req.schema_name}/{req.version}"
                )

    def test_no_empty_combinations(self):
        """Each combination must have at least one requirement."""
        factory = self.get_analyser_factory()
        requirements = factory.get_input_requirements()

        for i, combo in enumerate(requirements):
            assert len(combo) > 0, f"Combination {i} is empty"
```

## Example: GDPR Article 30 Analyser

### Package Structure

```
libs/waivern-gdpr-analyser/
└── src/waivern_gdpr_analyser/
    ├── __init__.py
    ├── factory.py
    ├── models.py                    # Internal Pydantic models
    ├── analysers/
    │   └── article_30.py
    ├── schema_readers/
    │   ├── __init__.py
    │   ├── personal_data_finding_1_0_0.py
    │   ├── processing_purpose_finding_1_0_0.py
    │   └── data_subject_finding_1_0_0.py
    ├── schema_producers/
    │   ├── __init__.py
    │   └── gdpr_article_30_finding_1_0_0.py
    └── schemas/
        └── json_schemas/
            └── gdpr_article_30_finding/
                └── 1.0.0/
                    └── gdpr_article_30_finding.json
```

### Analyser Implementation

```python
class GdprArticle30Analyser(Analyser):
    """Synthesises findings into GDPR Article 30 RoPA structure."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "gdpr_article_30"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [
            # Option 1: All three finding types
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
                InputRequirement("data_subject_finding", "1.0.0"),
            ],
            # Option 2: Without data subjects (optional in some contexts)
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
            ],
        ]

    @override
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        schemas = frozenset((msg.schema.name, msg.schema.version) for msg in inputs)

        if schemas == {
            ("personal_data_finding", "1.0.0"),
            ("processing_purpose_finding", "1.0.0"),
            ("data_subject_finding", "1.0.0"),
        }:
            return self._process_full(inputs, output_schema)
        elif schemas == {
            ("personal_data_finding", "1.0.0"),
            ("processing_purpose_finding", "1.0.0"),
        }:
            return self._process_without_subjects(inputs, output_schema)
        else:
            raise ValueError(f"Unexpected schema combination: {schemas}")

    def _process_full(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        # Read each input with appropriate reader
        personal_data = self._read_by_schema(inputs, "personal_data_finding")
        purposes = self._read_by_schema(inputs, "processing_purpose_finding")
        subjects = self._read_by_schema(inputs, "data_subject_finding")

        # Synthesise into Article 30 structure
        activities = self._build_processing_activities(
            personal_data,
            purposes,
            subjects,
        )
        gaps = self._identify_compliance_gaps(activities)

        # Produce output
        producer = self._load_producer(output_schema)
        content = producer.produce(
            processing_activities=activities,
            compliance_gaps=gaps,
            requires_human_review=len(gaps) > 0,
        )

        output = Message(schema=output_schema, content=content)
        output.validate()
        return output

    def _process_without_subjects(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        personal_data = self._read_by_schema(inputs, "personal_data_finding")
        purposes = self._read_by_schema(inputs, "processing_purpose_finding")

        activities = self._build_processing_activities(
            personal_data,
            purposes,
            subjects=[],  # Empty subjects
        )
        gaps = self._identify_compliance_gaps(activities)
        gaps.append("Data subjects not analysed")

        producer = self._load_producer(output_schema)
        content = producer.produce(
            processing_activities=activities,
            compliance_gaps=gaps,
            requires_human_review=True,
        )

        output = Message(schema=output_schema, content=content)
        output.validate()
        return output

    def _read_by_schema(
        self,
        inputs: list[Message],
        schema_name: str,
    ) -> list[Any]:
        """Find and read all inputs matching schema name."""
        results = []
        for msg in inputs:
            if msg.schema.name == schema_name:
                reader = self._load_reader_for_schema(msg.schema)
                results.extend(reader.read(msg.content))
        return results
```

### Sample Runbook

```yaml
name: "GDPR Article 30 RoPA Analysis"
description: "Generate Records of Processing Activities for GDPR compliance"
contact: "DPO <dpo@company.com>"

artifacts:
  # Source extraction
  db_schema:
    source:
      type: mysql
      properties:
        host: "${MYSQL_HOST}"
        database: "${MYSQL_DATABASE}"

  # Technical findings (run in parallel)
  personal_data_findings:
    inputs: db_schema
    transform:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "personal_data"

  processing_purposes:
    inputs: db_schema
    transform:
      type: processing_purpose

  data_subjects:
    inputs: db_schema
    transform:
      type: data_subject

  # Regulatory synthesis (fan-in from three schemas)
  gdpr_ropa:
    name: "GDPR Records of Processing Activities"
    description: "Article 30(1)(a) compliant processing record"
    inputs:
      - personal_data_findings
      - processing_purposes
      - data_subjects
    transform:
      type: gdpr_article_30
      properties:
        jurisdiction: "EU"
        flag_missing: true
    output: true
```

## Runbook Syntax

No syntax changes required. The runbook simply lists inputs:

```yaml
# Single input
findings:
  inputs: db_schema
  transform:
    type: personal_data

# Same-schema fan-in (multiple sources, same schema)
combined:
  inputs:
    - mysql_findings
    - postgres_findings
  transform:
    type: personal_data

# Multi-schema fan-in
gdpr_ropa:
  inputs:
    - personal_data_findings
    - processing_purposes
    - data_subjects
  transform:
    type: gdpr_article_30
```

The Planner determines which input requirement matches based on the schemas of provided artifacts.

## Migration Guide

### Existing Analysers

All existing analysers need updating:

1. **Replace `get_supported_input_schemas()`** with `get_input_requirements()`:
   ```python
   # Before
   @classmethod
   def get_supported_input_schemas(cls) -> list[Schema]:
       return [Schema("standard_input", "1.0.0")]

   # After
   @classmethod
   def get_input_requirements(cls) -> list[list[InputRequirement]]:
       return [
           [InputRequirement("standard_input", "1.0.0")],
       ]
   ```

2. **Update `process()` signature with merge-first pattern**:
   ```python
   # Before
   def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message:
       reader = self._load_reader(input_schema)
       data = reader.read(message.content)
       ...

   # After - always merge all inputs (standard pattern)
   def process(self, inputs: list[Message], output_schema: Schema) -> Message:
       # Merge all inputs into one dataset (handles same-schema fan-in)
       all_items = []
       for msg in inputs:
           reader = self._load_reader_for_schema(msg.schema)
           all_items.extend(reader.read(msg.content).get("items", []))

       # Analyse the combined dataset
       # Item-level source metadata is preserved for provenance
       ...
   ```

### Affected Packages

- waivern-personal-data-analyser
- waivern-data-subject-analyser
- waivern-processing-purpose-analyser
- waivern-data-export-analyser (WIP)

## Design Decisions

### Why List of Lists for Input Requirements?

Each inner list represents a distinct, valid input combination. This allows:
- Explicit declaration of all supported scenarios
- Version flexibility (v1.0.0 OR v1.1.0)
- Mixed combinations (schema A alone OR schema A + B together)

### Why Exact Set Matching?

Ambiguity arises if we allow partial matching or optional schemas within a combination. Exact set matching is:
- Unambiguous - exactly one combination matches or none
- Simple to implement and understand
- Follows principle: "if same input needs different handling, use different analysers"

### Why Implicit Same-Schema Fan-In with Merge-First?

Multiple messages of the same schema are naturally handled via the **merge-first pattern**:

- The schema set is still the same (e.g., `{standard_input/1.0.0}`)
- All analysers merge inputs into one combined dataset before analysis
- No special cardinality declaration needed

**Why merge-first is the standard:**

1. **Cross-source correlation** - Can detect patterns across sources (e.g., "email in MySQL relates to customer_email in PostgreSQL")
2. **Holistic compliance view** - GDPR Article 30 requires documenting ALL processing, not per-source
3. **Deduplication** - Can identify same data appearing in multiple places
4. **Provenance preserved** - Input schemas include source metadata per item, so findings retain traceability

```
MySQL → [{"source": "mysql.users.email", ...}]
PostgreSQL → [{"source": "postgres.customers.email", ...}]

After merge → [{"source": "mysql.users.email", ...}, {"source": "postgres.customers.email", ...}]

Findings → Each finding retains its source for audit trail
```

This is consistent across all analysers - no per-analyser strategy decisions.

### Why Analyser-Level Compliance Framework?

Compliance frameworks are declared by **analysers**, not runbooks:

```python
class ComponentFactory[T](ABC):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this component's output supports.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic components.
        """
        return []  # Default: generic component
```

**Examples:**
```python
# Generic analyser
class PersonalDataAnalyserFactory(ComponentFactory[Analyser]):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return []  # Generic building block

# GDPR-specific analyser
class GdprArticle30AnalyserFactory(ComponentFactory[Analyser]):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR"]

# Multi-framework analyser
class CrossBorderTransferAnalyserFactory(ComponentFactory[Analyser]):
    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR", "UK_GDPR", "SWISS_DPA"]
```

**Why analyser-level, not runbook-level:**

1. **Single source of truth** - Analyser knows what frameworks its output supports
2. **No mismatch** - Can't declare GDPR runbook with non-GDPR analysers
3. **Auto-discovery** - Exporter selection based on what analysers actually produced
4. **Explicit** - Not relying on schema naming conventions

**Consumer behaviour:**
- After execution, WCT examines analyser factories used
- Collects all declared compliance frameworks
- Single framework → use matching exporter
- Multiple frameworks → user must specify or use generic JSON
- No frameworks → use JSON exporter (default)

See [Export Architecture](./export-architecture.md) for full details.

### Why Unified `process()` Interface?

- Consistent API for single and multi-schema analysers
- No branching between `process()` and `process_multi()`
- Single-schema is just a special case (list with items of same schema)

## Implementation Tasks

### Phase 1: Core Infrastructure

**Task A: Update waivern-core**
- Add `InputRequirement` dataclass
- Update `Analyser` base class:
  - Add `get_input_requirements()` (replace `get_supported_input_schemas()`)
  - Update `process()` signature
  - Add `_load_reader_for_schema()` helper
- Update `ComponentFactory`
- Add `AnalyserContractTest` base class

**Task B: Update waivern-orchestration**
- Update `Planner._resolve_derived_schema()` for new matching logic
- Update `DAGExecutor._produce_derived()` for new `process()` signature

**Task C: Migrate Existing Analysers**
- waivern-personal-data-analyser
- waivern-data-subject-analyser
- waivern-processing-purpose-analyser
- waivern-data-export-analyser

### Phase 2: GDPR Implementation

**Task D: waivern-gdpr-analyser Package**
- Package structure and setup
- `gdpr_article_30_finding` schema
- Readers for input schemas
- Producer for output
- `GdprArticle30Analyser` implementation

**Task E: Documentation**
- Sample GDPR runbook
- Update architecture documentation

## Related Documents

- [Artifact-Centric Runbook](./artifact-centric-runbook.md)
- [DAG Orchestration Layer](./dag-orchestration-layer.md)
- [Export Architecture](./export-architecture.md)
