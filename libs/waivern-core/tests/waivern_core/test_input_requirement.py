"""Tests for InputRequirement dataclass."""

import pytest


class TestInputRequirement:
    """Tests for InputRequirement dataclass creation and behaviour."""

    def test_creation_with_valid_values(self) -> None:
        """InputRequirement can be created with schema_name and version."""
        from waivern_core import InputRequirement

        req = InputRequirement(schema_name="personal_data_finding", version="1.0.0")

        assert req.schema_name == "personal_data_finding"
        assert req.version == "1.0.0"

    def test_immutability(self) -> None:
        """InputRequirement is frozen and cannot be modified after creation."""
        from dataclasses import FrozenInstanceError

        from waivern_core import InputRequirement

        req = InputRequirement(schema_name="personal_data_finding", version="1.0.0")

        with pytest.raises(FrozenInstanceError):
            setattr(req, "schema_name", "different_schema")

    def test_equality_same_values(self) -> None:
        """Two InputRequirements with same values are equal."""
        from waivern_core import InputRequirement

        req1 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")
        req2 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")

        assert req1 == req2

    def test_equality_different_values(self) -> None:
        """Two InputRequirements with different values are not equal."""
        from waivern_core import InputRequirement

        req1 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")
        req2 = InputRequirement(schema_name="personal_data_finding", version="2.0.0")
        req3 = InputRequirement(schema_name="other_finding", version="1.0.0")

        assert req1 != req2
        assert req1 != req3

    def test_hashable_for_sets(self) -> None:
        """InputRequirement can be used in sets."""
        from waivern_core import InputRequirement

        req1 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")
        req2 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")
        req3 = InputRequirement(schema_name="other_finding", version="1.0.0")

        # Duplicates should be deduplicated in a set
        requirement_set = {req1, req2, req3}

        assert len(requirement_set) == 2
        assert req1 in requirement_set
        assert req3 in requirement_set

    def test_hashable_for_dict_keys(self) -> None:
        """InputRequirement can be used as dict keys."""
        from waivern_core import InputRequirement

        req1 = InputRequirement(schema_name="personal_data_finding", version="1.0.0")
        req2 = InputRequirement(schema_name="other_finding", version="1.0.0")

        mapping = {req1: "first", req2: "second"}

        assert mapping[req1] == "first"
        assert mapping[req2] == "second"

        # Same values should retrieve same value
        req1_copy = InputRequirement(
            schema_name="personal_data_finding", version="1.0.0"
        )
        assert mapping[req1_copy] == "first"
