from waivern_connectors_source_code import (
    SourceCodeConnector,
    SourceCodeConnectorInputSchema,
    SourceCodeConnectorOutputSchema,
)


def test_basic():
    connector = SourceCodeConnector()
    assert (
        connector.run(SourceCodeConnectorInputSchema())
        == SourceCodeConnectorOutputSchema()
    )
