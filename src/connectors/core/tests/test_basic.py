from waivern_connectors_core import (
    Connector,
    ConnectorInputSchema,
    ConnectorOutputSchema,
)


class PlaceholderConnector(Connector):
    def run(self, input: ConnectorInputSchema) -> ConnectorOutputSchema:
        return ConnectorOutputSchema()


def test_basic():
    connector = PlaceholderConnector()
    assert connector.run(ConnectorInputSchema()) == ConnectorOutputSchema()
