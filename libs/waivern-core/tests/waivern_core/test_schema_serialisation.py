"""Tests for Schema serialisation (pickle and Pydantic).

For Schema value object tests, see test_schema.py.
For loading infrastructure tests, see test_schema_loader.py.
"""

import pickle

from pydantic import BaseModel

from waivern_core.schemas import Schema

# =============================================================================
# Pickle Serialisation
# =============================================================================


class TestSchemaPickle:
    """Tests for Schema pickle serialisation."""

    def test_pickle_round_trip(self) -> None:
        """Schema can be pickled and unpickled correctly."""
        original = Schema("standard_input", "1.0.0")

        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)  # noqa: S301

        assert restored.name == original.name
        assert restored.version == original.version
        assert restored == original

    def test_pickled_schema_can_load_definition(self) -> None:
        """Unpickled Schema can still load its JSON schema definition."""
        original = Schema("standard_input", "1.0.0")
        # Trigger lazy loading before pickling
        _ = original.schema

        pickled = pickle.dumps(original)
        restored = pickle.loads(pickled)  # noqa: S301

        # Restored schema can still load definition
        assert restored.schema["version"] == "1.0.0"


# =============================================================================
# Pydantic Serialisation
# =============================================================================


class TestSchemaPydantic:
    """Tests for Schema Pydantic serialisation."""

    def test_pydantic_model_with_schema_field(self) -> None:
        """Schema can be used as a field in Pydantic models."""

        class TestModel(BaseModel):
            schema_ref: Schema

        model = TestModel(schema_ref=Schema("standard_input", "1.0.0"))

        assert model.schema_ref.name == "standard_input"
        assert model.schema_ref.version == "1.0.0"

    def test_pydantic_serialisation_round_trip(self) -> None:
        """Schema in Pydantic model serialises and deserialises correctly."""

        class TestModel(BaseModel):
            schema_ref: Schema

        original = TestModel(schema_ref=Schema("standard_input", "1.0.0"))

        data = original.model_dump()
        restored = TestModel.model_validate(data)

        assert restored.schema_ref.name == "standard_input"
        assert restored.schema_ref.version == "1.0.0"

    def test_pydantic_optional_schema_field(self) -> None:
        """Optional Schema field works in Pydantic models."""

        class TestModel(BaseModel):
            schema_ref: Schema | None = None

        # With None
        model_none = TestModel()
        assert model_none.schema_ref is None

        # With Schema
        model_with = TestModel(schema_ref=Schema("standard_input", "1.0.0"))
        assert model_with.schema_ref is not None
        assert model_with.schema_ref.name == "standard_input"

        # Round-trip with None
        restored_none = TestModel.model_validate(model_none.model_dump())
        assert restored_none.schema_ref is None

        # Round-trip with Schema
        restored_with = TestModel.model_validate(model_with.model_dump())
        assert restored_with.schema_ref is not None
        assert restored_with.schema_ref.name == "standard_input"
