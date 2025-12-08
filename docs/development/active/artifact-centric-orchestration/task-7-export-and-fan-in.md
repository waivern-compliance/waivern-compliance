# Task 7: Export Infrastructure and Multi-Schema Fan-In

- **Phase:** 4 - Export & Regulatory Analysers
- **Status:** IN_PROGRESS (Tasks 7a-7c complete)
- **GitHub Issue:** TBD
- **Prerequisites:** Tasks 1-6 (artifact-centric orchestration complete)
- **Design:** [Multi-Schema Fan-In](../../../future-plans/multi-schema-fan-in.md), [Export Architecture](../../../future-plans/export-architecture.md)
- **Follow-on:** [GDPR Complete](../../../future-plans/gdpr-complete.md)

## Context

Tasks 1-6 implemented the artifact-centric orchestration system with Planner and DAGExecutor. This task adds multi-schema fan-in support and export infrastructure - the foundation for regulatory analysers.

## Purpose

1. Enable analysers to consume multiple inputs with different schemas
2. Create export infrastructure for regulation-specific output formats
3. Prepare the foundation for regulatory synthesisers (GDPR, etc.)

## Problem

The current system has limitations:

1. **Fan-in limitation:** All inputs must have the same schema
2. **Export limitation:** Only generic JSON output, no regulation-specific formatting

## Scope

This task focuses on **infrastructure only**. GDPR-specific implementation is tracked separately in [GDPR Complete](../../../future-plans/gdpr-complete.md).

Sub-tasks for incremental delivery:

- **Task 7a:** Multi-schema analyser support in waivern-core (refactor analyser interface)
- **Task 7b:** Multi-schema fan-in in waivern-orchestration
- **Task 7c:** Migrate existing analysers to new interface
- **Task 7d:** Export infrastructure in wct
- **Task 7e:** Organisation config enhancement
- **Task 7f:** Sample runbook and documentation

---

## Task 7a: Multi-Schema Analyser Support (waivern-core)

**Status:** DONE

### Changes

**1. Add `InputRequirement` dataclass:**

```python
# waivern_core/types.py

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
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
    def get_name(cls) -> str:
        """Get the name of the analyser."""

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

    @classmethod
    @abstractmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Declare output schemas this analyser can produce."""
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

    # Removed: get_supported_input_schemas() - replaced by get_input_requirements()
```

**3. Update `ComponentFactory`:**

Factory handles instantiation and provides metadata access via `component_class`.

```python
# waivern_core/component_factory.py

class ComponentFactory[T](ABC):
    @property
    @abstractmethod
    def component_class(self) -> type[T]:
        """Return the component class this factory creates.

        Used by executor to access class methods like get_input_requirements()
        and get_supported_output_schemas() without instantiating the component.
        """
        ...

    @abstractmethod
    def create(self, config: ComponentConfig) -> T:
        """Create a component instance."""
        ...

    @abstractmethod
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if factory can create component with given config."""
        ...

    def get_service_dependencies(self) -> dict[str, type]:
        """Declare service dependencies for DI container."""
        return {}
```

**4. Add `AnalyserContractTests` base class:**

```python
# waivern_core/testing.py

class AnalyserContractTests[T: Analyser]:
    """Abstract contract tests that all Analyser implementations must pass.

    Required Fixtures:
        analyser_class: The Analyser class (not instance) to test

    Usage Pattern:
        class TestPersonalDataAnalyserContract(AnalyserContractTests[PersonalDataAnalyser]):
            @pytest.fixture
            def analyser_class(self) -> type[PersonalDataAnalyser]:
                return PersonalDataAnalyser

            # All contract tests run automatically
    """

    @pytest.fixture
    def analyser_class(self) -> type[T]:
        """Provide Analyser class to test. Subclasses MUST override."""
        raise NotImplementedError(
            "Subclass must provide 'analyser_class' fixture with Analyser class"
        )

    def test_input_requirements_not_empty(self, analyser_class: type[T]) -> None:
        """Input requirements must have at least one combination."""
        requirements = analyser_class.get_input_requirements()
        assert len(requirements) > 0

    def test_no_duplicate_combinations(self, analyser_class: type[T]) -> None:
        """Each combination must be unique."""
        requirements = analyser_class.get_input_requirements()
        seen: set[frozenset[tuple[str, str]]] = set()

        for combo in requirements:
            combo_set = frozenset((r.schema_name, r.version) for r in combo)
            assert combo_set not in seen, f"Duplicate combination: {combo_set}"
            seen.add(combo_set)

    def test_no_empty_combinations(self, analyser_class: type[T]) -> None:
        """Each combination must have at least one requirement."""
        requirements = analyser_class.get_input_requirements()

        for i, combo in enumerate(requirements):
            assert len(combo) > 0, f"Combination {i} is empty"
```

**5. Update exports:**

```python
# waivern_core/__init__.py

from waivern_core.types import InputRequirement
from waivern_core.testing import AnalyserContractTests
# ... existing exports ...

__all__ = [
    # ... existing ...
    "InputRequirement",
    "AnalyserContractTests",
]
```

### Tests

**InputRequirement tests** (`test_input_requirement.py`):
- `test_creation_with_valid_values` - dataclass creation
- `test_immutability` - frozen dataclass cannot be modified
- `test_equality_same_values` - two requirements with same values are equal
- `test_equality_different_values` - different values are not equal
- `test_hashable_for_sets` - can be used in sets
- `test_hashable_for_dict_keys` - can be used as dict keys

**AnalyserContractTests** - inherited by analyser test classes (Task 7c)

---

## Task 7b: Multi-Schema Fan-In (waivern-orchestration)

**Status:** DONE

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
    requirements = factory.component_class.get_input_requirements()

    matched = self._find_matching_requirement(artifact_id, provided_set, requirements)
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


```

**Note:** Reader validation is handled at runtime when loading reader modules. If an analyser declares an `InputRequirement` but has no corresponding reader module, the error will be raised during `process()` when attempting to load the reader.

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
    input_refs = self._normalise_inputs(definition.inputs)
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
- `test_executor_passes_list_to_process` - inputs as list[Message]
- `test_executor_same_schema_fan_in` - multiple messages of same schema

---

## Task 7c: Migrate Existing Analysers

**Status:** DONE

Update all existing analysers to the new interface:

### waivern-personal-data-analyser

```python
# Before (current state - needs migration)
@classmethod
def get_supported_input_schemas(cls) -> list[Schema]:
    return [Schema("standard_input", "1.0.0")]

def process(self, input_schema: Schema, output_schema: Schema, message: Message) -> Message:
    reader = self._load_reader(input_schema)
    data = reader.read(message.content)
    ...

# After (new interface)
@classmethod
def get_input_requirements(cls) -> list[list[InputRequirement]]:
    return [
        [InputRequirement("standard_input", "1.0.0")],
    ]

def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    # For single-input analysers, just use inputs[0]
    message = inputs[0]
    reader = self._load_reader(message.schema)
    data = reader.read(message.content)
    ...

    # For multi-input (fan-in) analysers, merge all inputs:
    # all_items = []
    # for msg in inputs:
    #     reader = self._load_reader(msg.schema)
    #     all_items.extend(reader.read(msg.content).get("items", []))
```

### Affected Packages

- waivern-personal-data-analyser
- waivern-data-subject-analyser
- waivern-processing-purpose-analyser
- waivern-source-code-analyser
- waivern-data-export-analyser (WIP)

### Tests

Each analyser package should:
1. Inherit from `AnalyserContractTests` for contract validation
2. Update unit tests for new `process()` signature
3. Add tests for merge-first pattern (multiple inputs merged into one dataset)

### Completion Notes

Successfully migrated all analysers to the new multi-schema interface:
- ✅ waivern-personal-data-analyser
- ✅ waivern-data-subject-analyser
- ✅ waivern-processing-purpose-analyser
- ✅ waivern-source-code-analyser

Additional improvements completed:
- Fixed infinite loop bug in DAG executor when skipped artifacts mixed with executing ones
- Removed redundant JSON schema validation (Pydantic already validates)
- Added comprehensive debug logging to executor
- Improved CLI table formatting (removed emojis, added colour-coded status)

All 841 tests passing. Branch: `feature/multi-schema-analyser-support`

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
            frameworks.update(factory.component_class.get_compliance_frameworks())

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

## Task 7f: Sample Runbook and Documentation

### Sample Runbook

Update existing sample runbooks to demonstrate multi-schema fan-in:

**`apps/wct/runbooks/samples/multi_source_analysis.yaml`:**

```yaml
name: "Multi-Source Compliance Analysis"
description: "Analyse data from multiple sources with fan-in"
contact: "Compliance Team <compliance@company.com>"

artifacts:
  # Multiple source extractions
  mysql_schema:
    source:
      type: mysql
      properties:
        host: "${MYSQL_HOST}"
        database: "${MYSQL_DATABASE}"

  sqlite_schema:
    source:
      type: sqlite
      properties:
        path: "./data/local.db"

  # Same-schema fan-in: multiple sources → single analyser
  # All inputs are merged before analysis (cross-source correlation)
  personal_data_findings:
    inputs:
      - mysql_schema
      - sqlite_schema
    transform:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "personal_data"
    output: true
```

### Documentation Updates

1. Update `apps/wct/runbooks/README.md` with multi-schema fan-in example
2. Update `CLAUDE.md` with new analyser interface
3. Create ADR for multi-schema fan-in pattern
4. Update architecture documentation
5. Add reference to [GDPR Complete](../../../future-plans/gdpr-complete.md) for regulatory analyser examples

---

## Testing

### Validation Commands

```bash
# Run all tests
uv run pytest -v

# Run specific test files
uv run pytest libs/waivern-core/tests/ -v
uv run pytest libs/waivern-orchestration/tests/ -v
uv run pytest apps/wct/tests/test_exporters.py -v

# Run multi-source sample runbook
uv run wct run apps/wct/runbooks/samples/multi_source_analysis.yaml

# Full dev-checks
./scripts/dev-checks.sh
```

### Integration Test

```python
def test_multi_schema_fan_in_end_to_end():
    """Test multi-schema fan-in from runbook to export."""
    # 1. Parse runbook with multiple inputs
    # 2. Plan execution (verify input requirement matching)
    # 3. Execute (mocked connectors)
    # 4. Verify analyser receives list[Message] input
    # 5. Verify JSON exporter produces correct output
```

## Implementation Order

1. **Task 7a** - Core infrastructure (InputRequirement, unified process(), contract tests)
2. **Task 7b** - Orchestration support (Planner exact set matching, Executor)
3. **Task 7c** - Migrate existing analysers (breaking change, all at once)
4. **Task 7d** - Export foundation (protocol, registry, JsonExporter)
5. **Task 7e** - Organisation enhancement (multi-jurisdiction)
6. **Task 7f** - Sample runbook and docs

Each sub-task should pass `./scripts/dev-checks.sh` before proceeding.

## Follow-on Work

After Task 7 is complete, the infrastructure is ready for regulatory analysers. See [GDPR Complete](../../../future-plans/gdpr-complete.md) for the full GDPR implementation plan including:

- DataTransferAnalyser (complete the existing stub)
- RetentionAnalyser
- LegalBasisAnalyser
- GdprArticle30Analyser (multi-schema fan-in synthesiser)
- GDPRExporter
