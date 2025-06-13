from dataclasses import dataclass

from waivern_analyser.config import AnalyserConfig


@dataclass(frozen=True, slots=True)
class Analyser:
    config: AnalyserConfig

    def run(self) -> None:
        sources = self.config.load_sources()
        connectors = self.config.load_connectors()
        connections = connectors.connect(sources)

        for finding in connections.iter_findings():
            print(finding)
