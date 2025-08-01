"""Unit tests for base connector functionality."""

from wct.connectors.base import Connector


class TestConnector:
    """Test suite for base Connector class."""

    def test_connector_is_abstract(self):
        """Test that Connector cannot be instantiated directly."""
        # This should raise TypeError because Connector is abstract
        try:
            Connector()
            assert False, "Should not be able to instantiate abstract Connector"
        except TypeError:
            pass  # Expected behavior

    def test_connector_subclass_must_implement_abstract_methods(self):
        """Test that Connector subclasses must implement abstract methods."""

        class IncompleteConnector(Connector):
            """Incomplete connector missing required methods."""

            pass

        # This should raise TypeError because abstract methods aren't implemented
        try:
            IncompleteConnector()
            assert False, "Should not be able to instantiate incomplete connector"
        except TypeError:
            pass  # Expected behavior

    # TODO: Add tests for:
    # - Complete connector implementation
    # - get_output_schema() method
    # - transform() method
    # - Schema validation
    # - Configuration handling
