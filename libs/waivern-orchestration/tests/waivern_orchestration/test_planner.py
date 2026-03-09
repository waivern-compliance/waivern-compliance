"""Tests for Planner - successful planning scenarios.

For error handling scenarios, see test_planner_errors.py.
"""

import pytest
from waivern_core.schemas import Schema

from waivern_orchestration.planner import ExecutionPlan, Planner

from .test_helpers import (
    create_mock_connector_factory,
    create_mock_processor_factory,
    create_mock_registry,
)

# =============================================================================
# Planner Happy Path
# =============================================================================


class TestPlannerHappyPath:
    """Tests for successful planning scenarios."""

    def test_plan_valid_source_artifact(self) -> None:
        """Planner can plan a runbook with a source artifact."""
        output_schema = Schema("standard_input", "1.0.0")
        connector_factory = create_mock_connector_factory("filesystem", [output_schema])

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test Runbook",
            "description": "A test runbook",
            "artifacts": {
                "data_source": {
                    "source": {
                        "type": "filesystem",
                        "properties": {"path": "/tmp"},
                    }
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        assert isinstance(plan, ExecutionPlan)
        assert plan.runbook.name == "Test Runbook"
        assert "data_source" in plan.runbook.artifacts
        assert plan.dag is not None
        assert "data_source" in plan.artifact_schemas
        input_schema, result_output_schema = plan.artifact_schemas["data_source"]
        assert input_schema is None
        assert result_output_schema.name == "standard_input"

    def test_plan_valid_derived_artifact_with_process(self) -> None:
        """Planner can plan derived artifact with process (source → processor chain)."""
        connector_output = Schema("standard_input", "1.0.0")
        analyser_input = Schema("standard_input", "1.0.0")
        analyser_output = Schema("personal_data_finding", "1.0.0")

        connector_factory = create_mock_connector_factory(
            "filesystem", [connector_output]
        )
        analyser_factory = create_mock_processor_factory(
            "personal_data_analyser", [analyser_input], [analyser_output]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory},
            processor_factories={"personal_data_analyser": analyser_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test Runbook",
            "description": "Source to derived chain",
            "artifacts": {
                "data_source": {
                    "source": {"type": "filesystem", "properties": {"path": "/tmp"}}
                },
                "findings": {
                    "inputs": "data_source",
                    "process": {
                        "type": "personal_data_analyser",
                        "properties": {},
                    },
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        assert isinstance(plan, ExecutionPlan)
        assert "data_source" in plan.artifact_schemas
        assert "findings" in plan.artifact_schemas

        source_input, source_output = plan.artifact_schemas["data_source"]
        assert source_input is None
        assert source_output.name == "standard_input"

        derived_input, derived_output = plan.artifact_schemas["findings"]
        assert derived_input is not None
        assert isinstance(derived_input, list)
        assert derived_input[0].name == "standard_input"
        assert derived_output.name == "personal_data_finding"

    def test_plan_derived_artifact_without_process_passthrough(self) -> None:
        """Derived artifact without process passes schema through (no processor)."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Passthrough test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "passthrough": {
                    "inputs": "source",
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, source_output = plan.artifact_schemas["source"]
        pass_input, pass_output = plan.artifact_schemas["passthrough"]

        assert source_output.name == "standard_input"
        assert pass_input is not None
        assert isinstance(pass_input, list)
        assert pass_input[0].name == "standard_input"
        assert pass_output.name == "standard_input"

    def test_plan_fan_in_compatible_schemas(self) -> None:
        """Fan-in works when all inputs have same schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Fan-in test",
            "artifacts": {
                "source_a": {
                    "source": {"type": "filesystem", "properties": {"path": "/a"}}
                },
                "source_b": {
                    "source": {"type": "filesystem", "properties": {"path": "/b"}}
                },
                "merged": {
                    "inputs": ["source_a", "source_b"],
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        merged_input, merged_output = plan.artifact_schemas["merged"]
        assert merged_input is not None
        assert isinstance(merged_input, list)
        assert merged_input[0].name == "standard_input"
        assert merged_output.name == "standard_input"

    def test_plan_input_schemas_as_list_for_single_schema(self) -> None:
        """Single-schema derived artifact stores input_schemas as a list of one Schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        analyser_factory = create_mock_processor_factory(
            "personal_data_analyser",
            [Schema("standard_input", "1.0.0")],
            [Schema("personal_data_finding", "1.0.0")],
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory},
            processor_factories={"personal_data_analyser": analyser_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "findings": {
                    "inputs": "source",
                    "process": {"type": "personal_data_analyser", "properties": {}},
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        input_schemas, _ = plan.artifact_schemas["findings"]
        assert isinstance(input_schemas, list)
        assert len(input_schemas) == 1
        assert input_schemas[0].name == "standard_input"

    def test_plan_explicit_output_schema_override(self) -> None:
        """Explicit output_schema on derived artifact overrides analyser's inferred schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )
        analyser_factory = create_mock_processor_factory(
            "personal_data_analyser",
            [Schema("standard_input", "1.0.0")],
            [Schema("personal_data_finding", "1.0.0")],
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory},
            processor_factories={"personal_data_analyser": analyser_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "source": {"source": {"type": "filesystem", "properties": {}}},
                "findings": {
                    "inputs": "source",
                    "process": {
                        "type": "personal_data_analyser",
                        "properties": {},
                    },
                    "output_schema": "custom_output/2.0.0",
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["findings"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "2.0.0"

    def test_plan_source_artifact_with_output_schema_override(self) -> None:
        """Source artifact with explicit output_schema uses override instead of connector's schema."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output/1.0.0",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.name != "standard_input"


# =============================================================================
# Multi-Schema Input Combinations
# =============================================================================


class TestPlannerMultiSchemaInputs:
    """Tests for processors accepting multiple distinct input schema types."""

    def test_plan_multi_schema_combination_with_matching_processor(self) -> None:
        """Inputs of schema A + schema B succeed when processor declares [[A, B]]."""
        schema_a = Schema("security_evidence", "1.0.0")
        schema_b = Schema("security_document_context", "1.0.0")
        output_schema = Schema("iso27001_assessment", "1.0.0")

        connector_a = create_mock_connector_factory("source_code", [schema_a])
        connector_b = create_mock_connector_factory("filesystem", [schema_b])
        assessor_factory = create_mock_processor_factory(
            "iso27001_assessor",
            [],
            [output_schema],
            input_requirements=[[schema_a, schema_b]],
        )

        registry = create_mock_registry(
            connector_factories={"source_code": connector_a, "filesystem": connector_b},
            processor_factories={"iso27001_assessor": assessor_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Multi-schema combination",
            "artifacts": {
                "evidence": {"source": {"type": "source_code", "properties": {}}},
                "documents": {"source": {"type": "filesystem", "properties": {}}},
                "assessment": {
                    "inputs": ["evidence", "documents"],
                    "process": {"type": "iso27001_assessor", "properties": {}},
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        input_schemas, result_output = plan.artifact_schemas["assessment"]
        assert input_schemas is not None
        assert len(input_schemas) == 2
        schema_names = {s.name for s in input_schemas}
        assert schema_names == {"security_evidence", "security_document_context"}
        assert result_output.name == "iso27001_assessment"

    def test_plan_multi_schema_combination_with_fan_in(self) -> None:
        """Two inputs of schema A + one of schema B succeed when processor declares [[A, B]]."""
        schema_a = Schema("security_evidence", "1.0.0")
        schema_b = Schema("security_document_context", "1.0.0")
        output_schema = Schema("iso27001_assessment", "1.0.0")

        connector_a = create_mock_connector_factory("source_code", [schema_a])
        connector_b = create_mock_connector_factory("filesystem", [schema_b])
        assessor_factory = create_mock_processor_factory(
            "iso27001_assessor",
            [],
            [output_schema],
            input_requirements=[[schema_a, schema_b]],
        )

        registry = create_mock_registry(
            connector_factories={"source_code": connector_a, "filesystem": connector_b},
            processor_factories={"iso27001_assessor": assessor_factory},
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Multi-schema with fan-in",
            "artifacts": {
                "evidence_a": {
                    "source": {"type": "source_code", "properties": {"path": "/a"}}
                },
                "evidence_b": {
                    "source": {"type": "source_code", "properties": {"path": "/b"}}
                },
                "documents": {"source": {"type": "filesystem", "properties": {}}},
                "assessment": {
                    "inputs": ["evidence_a", "evidence_b", "documents"],
                    "process": {"type": "iso27001_assessor", "properties": {}},
                },
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        input_schemas, result_output = plan.artifact_schemas["assessment"]
        assert input_schemas is not None
        assert len(input_schemas) == 2
        schema_names = {s.name for s in input_schemas}
        assert schema_names == {"security_evidence", "security_document_context"}
        assert result_output.name == "iso27001_assessment"


# =============================================================================
# Schema String Parsing
# =============================================================================


class TestSchemaStringParsing:
    """Tests for schema string parsing via output_schema override."""

    def test_parse_schema_string_without_version(self) -> None:
        """Schema string without version defaults to 1.0.0."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "1.0.0"

    def test_parse_schema_string_with_version(self) -> None:
        """Schema string with version uses explicit version."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {
                "data": {
                    "source": {"type": "filesystem", "properties": {}},
                    "output_schema": "custom_output/2.0.0",
                }
            },
        }

        plan = planner.plan_from_dict(runbook_data)

        _, output_schema = plan.artifact_schemas["data"]
        assert output_schema.name == "custom_output"
        assert output_schema.version == "2.0.0"


# =============================================================================
# Execution Plan
# =============================================================================


class TestExecutionPlan:
    """Tests for the ExecutionPlan dataclass."""

    def test_execution_plan_immutable(self) -> None:
        """ExecutionPlan is frozen/immutable."""
        connector_factory = create_mock_connector_factory(
            "filesystem", [Schema("standard_input", "1.0.0")]
        )

        registry = create_mock_registry(
            connector_factories={"filesystem": connector_factory}
        )
        planner = Planner(registry)

        runbook_data = {
            "name": "Test",
            "description": "Test",
            "artifacts": {"data": {"source": {"type": "filesystem", "properties": {}}}},
        }
        plan = planner.plan_from_dict(runbook_data)

        with pytest.raises(AttributeError):
            plan.runbook = None  # type: ignore[misc]
