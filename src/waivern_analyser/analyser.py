from collections.abc import Iterator
from dataclasses import dataclass

from typing_extensions import Self, assert_never

from waivern_analyser._plugins import (
    build_connectors_registry,
    build_rulesets_registry,
    build_sources_registry,
)
from waivern_analyser.config.analyser_config import AnalyserConfig
from waivern_analyser.connectors import Connection, Connector, NotConnected
from waivern_analyser.rulesets import ReportItem, Ruleset
from waivern_analyser.sources import Source


@dataclass(frozen=True, slots=True)
class Analyser:
    sources: tuple[Source, ...]
    connectors: tuple[Connector, ...]
    rulesets: tuple[Ruleset, ...]

    @classmethod
    def from_config(cls, config: AnalyserConfig) -> Self:
        # TODO: this method is doing too much;
        # Probably `config.{sources,connectors,rulesets}` should each have a method for loading their respective objects.
        plugin_registry = config.plugins.load_plugins()
        sources_registry = build_sources_registry(plugin_registry)
        connectors_registry = build_connectors_registry(plugin_registry)
        rulesets_registry = build_rulesets_registry(plugin_registry)

        sources: list[Source] = []
        for source_config in config.sources:
            source_type_name = source_config.type
            source_properties = source_config.properties
            source_type = sources_registry[source_type_name]
            source = source_type.from_properties(source_properties)
            sources.append(source)

        connectors: list[Connector] = []
        for connector_config in config.connectors:
            connector_type_name = connector_config.type
            connector_properties = connector_config.properties
            connector_type = connectors_registry[connector_type_name]
            connector = connector_type.from_properties(connector_properties)
            connectors.append(connector)

        rulesets: list[Ruleset] = []
        for ruleset_config in config.rulesets:
            ruleset_type_name = ruleset_config.type
            ruleset_properties = ruleset_config.properties
            ruleset_type = rulesets_registry[ruleset_type_name]
            ruleset = ruleset_type.from_properties(ruleset_properties)
            rulesets.append(ruleset)

        return cls(
            sources=tuple(sources),
            connectors=tuple(connectors),
            rulesets=tuple(rulesets),
        )

    def run(self) -> Iterator[ReportItem]:
        # sources -> connectors -> rulesets

        connections: list[Connection] = []
        for source in self.sources:
            for connector in self.connectors:
                match connector.connect(source):
                    case Connection() as connection:
                        connections.append(connection)
                    case NotConnected() as not_connected:
                        # TODO: find a better way to handle this
                        # Where should we log this?
                        print(not_connected.reason())
                    case never:
                        assert_never(never)

        findings = tuple(
            finding
            for connection in connections
            for finding in connection.iter_findings()
        )

        return (
            report_item
            for ruleset in self.rulesets
            for finding in findings
            for report_item in ruleset.run(finding)
        )
