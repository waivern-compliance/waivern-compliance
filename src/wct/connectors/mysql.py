from wct.connectors.base import Connector


class MySQLConnector(Connector):
    def __init__(self):
        pass

    def extract(self, **config) -> dict[str, Any]:
        pass
