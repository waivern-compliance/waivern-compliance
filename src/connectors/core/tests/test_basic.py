from waivern_connectors_core.connector import (
    Connector,
    ConnectorInputSchema,
)
from waivern_connectors_core.output_schema import ConnectorOutputSchema


class PlaceholderConnector(Connector):
    def run(self, input: ConnectorInputSchema) -> ConnectorOutputSchema:
        return ConnectorOutputSchema()


def test_basic():
    connector = PlaceholderConnector()
    assert connector.run(ConnectorInputSchema()) == ConnectorOutputSchema()
