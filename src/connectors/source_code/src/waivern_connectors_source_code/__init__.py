from waivern_connectors_core.connector import (
    Connector,
    ConnectorInputSchema,
)
from waivern_connectors_core.output_schema import ConnectorOutputSchema


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
