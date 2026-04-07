"""Tests for ExecutionPlan serialisation (to_dict / from_dict)."""

from waivern_core.schemas import Schema

from waivern_orchestration.models import ArtifactDefinition, SourceConfig
from waivern_orchestration.planner import ExecutionPlan

from .test_helpers import create_simple_plan

# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestExecutionPlanRoundTrip:
    """Tests for to_dict → from_dict round-trip fidelity."""

    def test_round_trip_preserves_source_artifact(self) -> None:
        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="filesystem", properties={"path": "./x"}),
            ),
        }
        output_schema = Schema("standard_input", "1.0.0")
        plan = create_simple_plan(artifacts, {"data": (None, output_schema)})

        restored = ExecutionPlan.from_dict(plan.to_dict())

        assert restored.runbook.name == plan.runbook.name
        assert set(restored.runbook.artifacts.keys()) == {"data"}
        assert restored.runbook.artifacts["data"].source is not None
        assert restored.runbook.artifacts["data"].source.type == "filesystem"

    def test_round_trip_preserves_artifact_schemas(self) -> None:
        artifacts = {
            "src": ArtifactDefinition(
                source=SourceConfig(type="fs", properties={}),
            ),
            "derived": ArtifactDefinition(inputs="src"),
        }
        schemas: dict[str, tuple[list[Schema] | None, Schema]] = {
            "src": (None, Schema("raw_data", "1.0.0")),
            "derived": ([Schema("raw_data", "1.0.0")], Schema("finding", "2.0.0")),
        }
        plan = create_simple_plan(artifacts, schemas)

        restored = ExecutionPlan.from_dict(plan.to_dict())

        # Source artifact: no inputs, has output
        src_inputs, src_output = restored.artifact_schemas["src"]
        assert src_inputs is None
        assert src_output.name == "raw_data"
        assert src_output.version == "1.0.0"

        # Derived artifact: has inputs and output
        derived_inputs, derived_output = restored.artifact_schemas["derived"]
        assert derived_inputs is not None
        assert len(derived_inputs) == 1
        assert derived_inputs[0].name == "raw_data"
        assert derived_output.name == "finding"
        assert derived_output.version == "2.0.0"

    def test_round_trip_preserves_aliases(self) -> None:
        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="fs", properties={}),
            ),
            "child__abc123__inner": ArtifactDefinition(inputs="data"),
        }
        schemas: dict[str, tuple[list[Schema] | None, Schema]] = {
            "data": (None, Schema("std", "1.0.0")),
            "child__abc123__inner": ([Schema("std", "1.0.0")], Schema("out", "1.0.0")),
        }
        aliases = {"output_alias": "child__abc123__inner"}
        plan = create_simple_plan(artifacts, schemas, aliases=aliases)

        restored = ExecutionPlan.from_dict(plan.to_dict())

        assert restored.aliases == {"output_alias": "child__abc123__inner"}
        assert restored.reversed_aliases == {"child__abc123__inner": "output_alias"}

    def test_round_trip_preserves_dag_dependencies(self) -> None:
        artifacts = {
            "a": ArtifactDefinition(
                source=SourceConfig(type="fs", properties={}),
            ),
            "b": ArtifactDefinition(inputs="a"),
            "c": ArtifactDefinition(inputs=["a", "b"]),
        }
        output_schema = Schema("std", "1.0.0")
        schemas: dict[str, tuple[list[Schema] | None, Schema]] = {
            "a": (None, output_schema),
            "b": ([output_schema], output_schema),
            "c": ([output_schema], output_schema),
        }
        plan = create_simple_plan(artifacts, schemas)

        restored = ExecutionPlan.from_dict(plan.to_dict())

        assert restored.dag.get_dependencies("a") == set()
        assert restored.dag.get_dependencies("b") == {"a"}
        assert restored.dag.get_dependencies("c") == {"a", "b"}

    def test_round_trip_with_empty_aliases(self) -> None:
        artifacts = {
            "data": ArtifactDefinition(
                source=SourceConfig(type="fs", properties={}),
            ),
        }
        plan = create_simple_plan(artifacts)

        restored = ExecutionPlan.from_dict(plan.to_dict())

        assert restored.aliases == {}
        assert restored.reversed_aliases == {}
