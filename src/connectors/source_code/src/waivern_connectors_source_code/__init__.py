from waivern_connectors_core import (
    Connector,
    ConnectorInputSchema,
    ConnectorOutputSchema,
)


class SourceCodeConnectorInputSchema(ConnectorInputSchema):
    pass


class SourceCodeConnectorOutputSchema(ConnectorOutputSchema):
    pass


class SourceCodeConnector(Connector):
    def run(
        self,
        input: SourceCodeConnectorInputSchema,
    ) -> SourceCodeConnectorOutputSchema:
        # TODO: return a nice output
        return SourceCodeConnectorOutputSchema()
