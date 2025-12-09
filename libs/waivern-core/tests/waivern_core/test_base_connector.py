"""Tests for Connector base class compliance framework declaration."""

from typing import override

from waivern_core import Connector, Message, Schema


class GenericConnector(Connector):
    """Concrete generic connector for testing base class behaviour."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "generic_test_connector"

    @override
    def extract(self, output_schema: Schema) -> Message:
        return Message(
            id="test",
            content={"test": "data"},
            schema=output_schema,
        )


class GdprSpecificConnector(Connector):
    """GDPR-specific connector for testing compliance framework override."""

    @classmethod
    @override
    def get_name(cls) -> str:
        return "gdpr_test_connector"

    @classmethod
    @override
    def get_compliance_frameworks(cls) -> list[str]:
        """Override to declare GDPR support."""
        return ["GDPR"]

    @override
    def extract(self, output_schema: Schema) -> Message:
        return Message(
            id="test",
            content={"test": "data"},
            schema=output_schema,
        )


class TestConnectorComplianceFrameworks:
    """Test compliance framework declaration on Connector base class."""

    def test_get_compliance_frameworks_returns_empty_list_by_default(self) -> None:
        """Default implementation returns empty list (generic connector)."""
        # Act
        frameworks = GenericConnector.get_compliance_frameworks()

        # Assert
        assert frameworks == []
        assert isinstance(frameworks, list)

    def test_subclass_can_override_compliance_frameworks(self) -> None:
        """Subclasses can override to declare specific frameworks."""
        # Act
        frameworks = GdprSpecificConnector.get_compliance_frameworks()

        # Assert
        assert frameworks == ["GDPR"]
        assert isinstance(frameworks, list)

    def test_compliance_frameworks_is_classmethod(self) -> None:
        """get_compliance_frameworks can be called without instantiation."""
        # Act - call on class directly without creating instance
        frameworks = GenericConnector.get_compliance_frameworks()

        # Assert - should work without error
        assert isinstance(frameworks, list)
