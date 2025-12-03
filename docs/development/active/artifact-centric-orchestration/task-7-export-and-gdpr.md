# Task 7: Export Infrastructure and GDPR Analyser

- **Phase:** 4 - Export & Regulatory Analysers
- **Status:** TODO
- **GitHub Issue:** TBD
- **Prerequisites:** Tasks 1-6 (artifact-centric orchestration complete)
- **Design:** [Multi-Schema Fan-In](../../../future-plans/multi-schema-fan-in.md), [Export Architecture](../../../future-plans/export-architecture.md)

## Context

Tasks 1-6 implemented the artifact-centric orchestration system with Planner and DAGExecutor. This task adds multi-schema fan-in support, export infrastructure, and the first regulatory analyser (GDPR Article 30).

## Purpose

1. Enable analysers to consume multiple inputs with different schemas
2. Create export infrastructure for regulation-specific output formats
3. Implement GDPR Article 30 analyser as proof of concept
4. Validate the end-to-end regulatory analysis pipeline

## Problem

The current system has limitations:

1. **Fan-in limitation:** All inputs must have the same schema
2. **Export limitation:** Only generic JSON output, no regulation-specific formatting
3. **No regulatory synthesis:** Cannot combine findings into regulatory structures

## Scope

This task is split into sub-tasks for incremental delivery:

- **Task 7a:** Multi-schema analyser support in waivern-core (refactor analyser interface)
- **Task 7b:** Multi-schema fan-in in waivern-orchestration
- **Task 7c:** Migrate existing analysers to new interface
- **Task 7d:** Export infrastructure in wct
- **Task 7e:** Organisation config enhancement
- **Task 7f:** GDPR analyser package
- **Task 7g:** GDPR exporter
- **Task 7h:** Sample runbook and documentation

---

## Task 7a: Multi-Schema Analyser Support (waivern-core)

### Changes

**1. Add `InputRequirement` dataclass:**

```python
# waivern_core/types.py (or base_analyser.py)

from dataclasses import dataclass

@dataclass(frozen=True)
class InputRequirement:
    """Declares a required input schema."""
    schema_name: str
    version: str
```

**2. Update `Analyser` base class:**

```python
# waivern_core/base_analyser.py

class Analyser(ABC):
    @classmethod
    @abstractmethod
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

    # Remove get_supported_input_schemas() - replaced by get_input_requirements()

    def _load_reader_for_schema(self, schema: Schema) -> ModuleType:
        """Load reader module for a specific schema.

        Helper method for analysers to load readers dynamically.

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

**3. Update `ComponentFactory`:**

```python
# waivern_core/component_factory.py

class ComponentFactory[T](ABC):
    # Existing methods...

    @abstractmethod
    def get_input_requirements(self) -> list[list[InputRequirement]]:
        """Get supported input schema combinations."""
        ...

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this component's output supports.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic components.
        """
        return []  # Default: generic component
```

**4. Add `AnalyserContractTest` base class:**

```python
# waivern_core/testing.py

from abc import ABC, abstractmethod

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

**5. Update exports:**

```python
# waivern_core/__init__.py

from waivern_core.types import InputRequirement
from waivern_core.testing import AnalyserContractTest
# ... existing exports ...

__all__ = [
    # ... existing ...
    "InputRequirement",
    "AnalyserContractTest",
]
```

### Tests

- `test_input_requirement_creation` - dataclass creation and immutability
- `test_input_requirement_equality` - two requirements with same values are equal
- `test_load_reader_for_schema` - helper loads correct module
- `test_analyser_contract_test_base` - contract tests work correctly

---

## Task 7b: Multi-Schema Fan-In (waivern-orchestration)

### Planner Changes

**1. Update `_resolve_derived_schema()`:**

```python
# waivern_orchestration/planner.py

def _resolve_derived_schema(
    self,
    artifact_id: str,
    definition: ArtifactDefinition,
    resolved: dict[str, tuple[list[InputRequirement] | None, Schema]],
) -> tuple[list[InputRequirement], Schema]:
    """Resolve schemas for a derived artifact."""
    inputs = definition.inputs
    if inputs is None:
        raise ValueError(f"Artifact '{artifact_id}' has neither source nor inputs")

    input_refs = [inputs] if isinstance(inputs, str) else inputs

    if definition.transform is None:
        return self._resolve_passthrough(artifact_id, input_refs, resolved)

    provided_set = self._collect_provided_schemas(input_refs, resolved)
    factory = self._registry.analyser_factories[definition.transform.type]
    requirements = factory.get_input_requirements()

    matched = self._find_matching_requirement(artifact_id, provided_set, requirements)
    self._validate_readers_exist(artifact_id, factory, matched)

    output_schema = self._get_output_schema(factory, definition)
    return (matched, output_schema)


def _collect_provided_schemas(
    self,
    input_refs: list[str],
    resolved: dict[str, tuple[list[InputRequirement] | None, Schema]],
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

### Executor Changes

**1. Update `_produce_derived()`:**

```python
# waivern_orchestration/executor.py

async def _produce_derived(
    self,
    artifact_id: str,
    definition: ArtifactDefinition,
    plan: ExecutionPlan,
    ctx: _ExecutionContext,
) -> Message:
    """Produce a derived artifact from its inputs."""
    input_refs = self._normalize_inputs(definition.inputs)
    _, output_schema = plan.artifact_schemas[artifact_id]

    if definition.transform is None:
        return self._handle_passthrough(input_refs, ctx.store)

    # Retrieve input messages from store
    input_messages = [ctx.store.get(ref) for ref in input_refs]

    factory = self._registry.analyser_factories[definition.transform.type]

    def sync_process() -> Message:
        analyser = factory.create(definition.transform.properties)
        return analyser.process(input_messages, output_schema)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(ctx.thread_pool, sync_process)
```

### Tests

- `test_planner_exact_set_matching_success` - matching combination found
- `test_planner_exact_set_matching_no_match` - error when no combination matches
- `test_planner_validates_readers_exist` - error on missing reader
- `test_executor_passes_list_to_process` - inputs as list[Message]
- `test_executor_same_schema_fan_in` - multiple messages of same schema

---

## Task 7c: Migrate Existing Analysers

Update all existing analysers to the new interface:

### waivern-personal-data-analyser

```python
# Before
@classmethod
def get_supported_input_schemas(cls) -> list[Schema]:
    return [Schema("standard_input", "1.0.0")]

def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message:
    reader = self._load_reader(input_schema)
    data = reader.read(message.content)
    ...

# After
@classmethod
def get_input_requirements(cls) -> list[list[InputRequirement]]:
    return [
        [InputRequirement("standard_input", "1.0.0")],
    ]

def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    # Standard pattern: merge all inputs into one dataset
    # This enables cross-source correlation while preserving item-level provenance
    all_items = []
    for msg in inputs:
        reader = self._load_reader_for_schema(msg.schema)
        all_items.extend(reader.read(msg.content).get("items", []))

    # Analyse the combined dataset
    # Each item retains source metadata (table, column, file path) for audit trail
    ...
```

### Affected Packages

- waivern-personal-data-analyser
- waivern-data-subject-analyser
- waivern-processing-purpose-analyser
- waivern-data-export-analyser (WIP)

### Tests

Each analyser package should:
1. Inherit from `AnalyserContractTest` for contract validation
2. Update unit tests for new `process()` signature
3. Add tests for merge-first pattern (multiple inputs merged into one dataset)

---

## Task 7d: Export Infrastructure (wct)

### Directory Structure

```
apps/wct/src/wct/
├── exporters/
│   ├── __init__.py
│   ├── protocol.py
│   ├── registry.py
│   ├── core.py
│   └── json_exporter.py
```

### Implementation

**1. Create `protocol.py`:**

```python
from typing import Any, Protocol
from waivern_orchestration import ExecutionPlan, ExecutionResult
from wct.organisation import OrganisationConfig

class Exporter(Protocol):
    @property
    def name(self) -> str: ...

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
    ) -> list[str]: ...

    def export(
        self,
        result: ExecutionResult,
        plan: ExecutionPlan,
        organisation: OrganisationConfig | None = None,
    ) -> dict[str, Any]: ...
```

**2. Create `registry.py`:**

```python
class ExporterRegistry:
    _exporters: dict[str, Exporter] = {}

    @classmethod
    def register(cls, exporter: Exporter) -> None:
        cls._exporters[exporter.name] = exporter

    @classmethod
    def get(cls, name: str) -> Exporter:
        if name not in cls._exporters:
            raise ValueError(f"Unknown exporter '{name}'")
        return cls._exporters[name]

    @classmethod
    def list_exporters(cls) -> list[str]:
        return list(cls._exporters.keys())
```

**3. Create `core.py`:**

Extract `build_core_export()` from current `cli.py`:

```python
def build_core_export(
    result: ExecutionResult,
    plan: ExecutionPlan,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build core export format shared by all exporters."""
    # ... existing _build_export_output logic ...
```

**4. Create `json_exporter.py`:**

```python
class JsonExporter:
    @property
    def name(self) -> str:
        return "json"

    @property
    def supported_frameworks(self) -> list[str]:
        return []  # Any framework (generic)

    def validate(self, result, plan) -> list[str]:
        return []

    def export(self, result, plan, organisation=None) -> dict[str, Any]:
        return build_core_export(result, plan)
```

**5. Update `cli.py`:**

- Refactor to use `ExporterRegistry`
- Add `--exporter` flag to `wct run`
- Add `wct export` command
- Add `wct ls-exporters` command
- Implement `_detect_exporter()` for schema-based discovery

**6. Add `_detect_exporter()` function:**

```python
# apps/wct/src/wct/cli.py

def _detect_exporter(
    result: ExecutionResult,
    plan: ExecutionPlan,
    registry: ComponentRegistry,
) -> str:
    """Auto-detect exporter based on analyser compliance frameworks.

    Examines analyser factories used in successful artifacts and collects
    their declared compliance frameworks.

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
        if definition is None or definition.transform is None:
            continue

        # Get analyser factory and check its compliance frameworks
        analyser_type = definition.transform.type
        if analyser_type in registry.analyser_factories:
            factory = registry.analyser_factories[analyser_type]
            frameworks.update(factory.get_compliance_frameworks())

    # Map frameworks to exporter
    if len(frameworks) == 1:
        return _framework_to_exporter(frameworks.pop())
    elif len(frameworks) > 1:
        # Multiple frameworks detected - fall back to JSON
        logger.info(
            "Multiple compliance frameworks detected: %s. Using JSON exporter.",
            frameworks
        )
        return "json"
    else:
        return "json"  # All generic analysers


def _framework_to_exporter(framework: str) -> str:
    """Map compliance framework to exporter name."""
    mapping = {
        "GDPR": "gdpr",
        "UK_GDPR": "gdpr",
        "CCPA": "ccpa",
    }
    return mapping.get(framework, "json")
```

The compliance framework is **not** declared in the Runbook. Instead, it is discovered from the analysers used:
- Generic analysers (personal_data, data_subject, etc.) return empty list
- GDPR-specific analysers return `["GDPR"]`
- Multi-framework analysers return `["GDPR", "UK_GDPR", ...]`

### Tests

- `test_exporter_registry_register_and_get`
- `test_exporter_registry_unknown_raises`
- `test_json_exporter_produces_core_format`
- `test_detect_exporter_single_framework`
- `test_detect_exporter_multiple_frameworks_uses_json`
- `test_detect_exporter_no_frameworks_uses_json`
- `test_cli_export_command`

---

## Task 7e: Organisation Config Enhancement

### Changes

**1. Update `organisation.py` for multi-jurisdiction:**

```python
class JurisdictionConfig(BaseModel):
    """Jurisdiction-specific organisation configuration."""
    data_controller: DataControllerConfig
    representatives: list[Representative] = Field(default_factory=list)

class OrganisationConfig(BaseModel):
    # Existing fields for simple config...
    data_controller: DataControllerConfig | None = None

    # New: per-jurisdiction configs
    jurisdictions: dict[str, JurisdictionConfig] | None = None

    # Common fields (apply to all jurisdictions)
    dpo: DpoConfig | None = None
    privacy_contact: PrivacyContactConfig | None = None
    data_retention: DataRetentionConfig | None = None
```

**2. Update `OrganisationLoader`:**

```python
class OrganisationLoader:
    @classmethod
    def load(cls, jurisdiction: str | None = None) -> OrganisationConfig | None:
        # ... load YAML ...

        if jurisdiction and data.get("jurisdictions"):
            return cls._build_for_jurisdiction(data, jurisdiction)

        return OrganisationConfig.model_validate(data)

    @classmethod
    def _build_for_jurisdiction(
        cls,
        data: dict,
        jurisdiction: str,
    ) -> OrganisationConfig | None:
        jurisdictions = data.get("jurisdictions", {})
        if jurisdiction not in jurisdictions:
            logger.warning(f"Jurisdiction '{jurisdiction}' not found")
            return None

        jur_config = jurisdictions[jurisdiction]
        return OrganisationConfig(
            data_controller=DataControllerConfig(**jur_config["data_controller"]),
            representatives=jur_config.get("representatives", []),
            dpo=data.get("dpo"),
            privacy_contact=data.get("privacy_contact"),
            data_retention=data.get("data_retention"),
        )
```

**3. Add `--jurisdiction` flag to CLI**

### Tests

- `test_organisation_loader_simple_config`
- `test_organisation_loader_multi_jurisdiction`
- `test_organisation_loader_jurisdiction_not_found`

---

## Task 7f: GDPR Analyser Package

### Package Structure

```
libs/waivern-gdpr-analyser/
├── pyproject.toml
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
└── src/waivern_gdpr_analyser/
    ├── __init__.py
    ├── factory.py
    ├── models.py
    ├── analysers/
    │   ├── __init__.py
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

### Key Files

**1. `factory.py`:**

```python
class GdprArticle30AnalyserFactory(ComponentFactory[Analyser]):
    """Factory for GDPR Article 30 analyser."""

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        return ["GDPR"]  # Declares this is a GDPR-specific component

    # ... other factory methods ...
```

**2. `analysers/article_30.py`:**

```python
class GdprArticle30Analyser(Analyser):
    """Synthesizes findings into GDPR Article 30 RoPA structure."""

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

        # Synthesize into Article 30 structure
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
            subjects=[],
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

**3. `schemas/json_schemas/gdpr_article_30_finding/1.0.0/gdpr_article_30_finding.json`:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "version": "1.0.0",
  "type": "object",
  "properties": {
    "processing_activities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "purpose": { "type": "string" },
          "legal_basis": { "type": ["string", "null"] },
          "legal_basis_status": {
            "type": "string",
            "enum": ["determined", "inferred", "requires_review"]
          },
          "data_categories": { "type": "array", "items": { "type": "string" } },
          "special_category_data": { "type": "boolean" },
          "data_subject_categories": { "type": "array", "items": { "type": "string" } },
          "retention_period": { "type": ["string", "null"] },
          "retention_status": {
            "type": "string",
            "enum": ["determined", "from_policy", "requires_review"]
          },
          "evidence": { "type": "array" }
        }
      }
    },
    "compliance_gaps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": { "type": "string" },
          "activity": { "type": "string" },
          "severity": { "type": "string", "enum": ["critical", "important", "minor"] },
          "message": { "type": "string" }
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_activities": { "type": "integer" },
        "activities_with_gaps": { "type": "integer" },
        "requires_human_review": { "type": "boolean" }
      }
    }
  },
  "required": ["processing_activities", "compliance_gaps", "summary"]
}
```

**4. Entry point in `pyproject.toml`:**

```toml
[project.entry-points."waivern.analysers"]
gdpr_article_30 = "waivern_gdpr_analyser.factory:GdprArticle30AnalyserFactory"
```

### Tests

- Inherit from `AnalyserContractTest` for contract validation
- `test_article_30_process_full_combination`
- `test_article_30_process_without_subjects`
- `test_article_30_identifies_compliance_gaps`
- `test_article_30_same_schema_fan_in` - multiple personal_data inputs merged

---

## Task 7g: GDPR Exporter

### Implementation

```
apps/wct/src/wct/exporters/gdpr/
├── __init__.py
└── exporter.py
```

**`exporter.py`:**

```python
class GdprExporter:
    # Schema this exporter requires (internal implementation detail)
    _REQUIRED_SCHEMA = "gdpr_article_30_finding"

    @property
    def name(self) -> str:
        return "gdpr"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["GDPR", "UK_GDPR"]

    def validate(self, result, plan) -> list[str]:
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
                "Add a gdpr_article_30 analyser to your pipeline."
            )
        return errors

    def export(self, result, plan, organisation=None) -> dict[str, Any]:
        output = build_core_export(result, plan)
        output["gdpr"] = {
            "article_30_1_a": self._build_article_30(result, plan, organisation)
        }
        return output
```

### Tests

- `test_gdpr_exporter_validates_required_schema`
- `test_gdpr_exporter_includes_organisation`
- `test_gdpr_exporter_warns_missing_organisation`
- `test_gdpr_exporter_supported_frameworks`

---

## Task 7h: Sample Runbook and Documentation

### Sample Runbook

**`apps/wct/runbooks/samples/gdpr_article_30_analysis.yaml`:**

```yaml
name: "GDPR Article 30 RoPA Analysis"
description: "Generate Records of Processing Activities for GDPR compliance"
contact: "DPO <dpo@company.com>"

# Note: No compliance_framework field needed - exporter is auto-detected
# from the gdpr_article_30 analyser's get_compliance_frameworks() declaration

artifacts:
  # Source extraction
  db_schema:
    source:
      type: mysql
      properties:
        host: "${MYSQL_HOST}"
        database: "${MYSQL_DATABASE}"

  # Technical findings (parallel)
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

  # Regulatory synthesis
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

### Documentation Updates

1. Update `apps/wct/runbooks/README.md` with multi-schema example
2. Update `CLAUDE.md` with GDPR analyser info
3. Create ADR for multi-schema fan-in pattern
4. Update architecture documentation

---

## Testing

### Validation Commands

```bash
# Run all tests
uv run pytest -v

# Run specific test files
uv run pytest libs/waivern-core/tests/ -v
uv run pytest libs/waivern-orchestration/tests/ -v
uv run pytest libs/waivern-gdpr-analyser/tests/ -v
uv run pytest apps/wct/tests/test_exporters.py -v

# Run GDPR sample runbook
uv run wct run apps/wct/runbooks/samples/gdpr_article_30_analysis.yaml

# Verify GDPR export
cat output/results.json | jq '.gdpr.article_30_1_a'

# Full dev-checks
./scripts/dev-checks.sh
```

### Integration Test

```python
def test_gdpr_article_30_end_to_end():
    """Test full GDPR pipeline from runbook to export."""
    # 1. Parse runbook
    # 2. Plan execution
    # 3. Execute (mocked connectors)
    # 4. Verify analyser receives list[Message] input
    # 5. Verify GDPR exporter produces correct output
    # 6. Verify organisation metadata included
```

## Implementation Order

1. **Task 7a** - Core infrastructure (InputRequirement, unified process(), contract tests)
2. **Task 7b** - Orchestration support (Planner exact set matching, Executor)
3. **Task 7c** - Migrate existing analysers (breaking change, all at once)
4. **Task 7d** - Export foundation (protocol, registry, JsonExporter)
5. **Task 7e** - Organisation enhancement (multi-jurisdiction)
6. **Task 7f** - GDPR analyser package
7. **Task 7g** - GDPR exporter
8. **Task 7h** - Sample runbook and docs

Each sub-task should pass `./scripts/dev-checks.sh` before proceeding.
