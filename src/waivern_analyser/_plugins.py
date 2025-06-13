import typing
from collections import defaultdict
from collections.abc import Iterable
from importlib.metadata import entry_points

from waivern_analyser.connectors import Connector
from waivern_analyser.plugins import Plugin
from waivern_analyser.rulesets import Ruleset
from waivern_analyser.sources import Source
from waivern_analyser.utils.frozendict import FrozenDict

PLUGINS_GROUP_NAME = "waivern-plugins"

PluginName: typing.TypeAlias = str
SourceName: typing.TypeAlias = str
ConnectorName: typing.TypeAlias = str
RulesetName: typing.TypeAlias = str

PluginRegistry: typing.TypeAlias = FrozenDict[PluginName, type[Plugin]]
SourcesRegistry: typing.TypeAlias = FrozenDict[SourceName, type[Source]]
ConnectorsRegistry: typing.TypeAlias = FrozenDict[ConnectorName, type[Connector]]
RulesetsRegistry: typing.TypeAlias = FrozenDict[RulesetName, type[Ruleset]]


class DuplicatePluginError(KeyError):
    def __init__(self, plugin_name: PluginName):
        super().__init__(
            plugin_name,
            f"Plugin {plugin_name} was loaded multiple times.",
        )


class MissingSelectedPluginsError(KeyError):
    def __init__(self, plugin_names: Iterable[PluginName]):
        plugin_names = sorted(frozenset(plugin_names))

        # TODO: differentiate between built-in and external plugins
        plugin_names_str = " ".join(plugin_names)
        installation_command = f"pip install {plugin_names_str}"

        super().__init__(
            plugin_names,
            f"Required plugins {plugin_names} are not installed. "
            f"Please install them using `{installation_command}`.",
        )


class WrongPluginClassError(TypeError):
    def __init__(self, plugin: typing.Any):
        super().__init__(
            plugin,
            f"Plugin {plugin} is not a valid Plugin (expected a subclass of {Plugin})",
        )


class SourceOwnerConflictError(TypeError):
    def __init__(self, source_type: type[Source], plugin_names: Iterable[PluginName]):
        plugin_names = sorted(frozenset(plugin_names))
        owners = ", ".join(plugin_names)
        super().__init__(
            source_type,
            f"Source type {source_type.get_name()!r} is defined by multiple plugins: {owners}.",
        )


class ConnectorOwnerConflictError(TypeError):
    def __init__(
        self, connector_type: type[Connector], plugin_names: Iterable[PluginName]
    ):
        plugin_names = sorted(frozenset(plugin_names))
        owners = ", ".join(plugin_names)
        super().__init__(
            connector_type,
            f"Connector type {connector_type.get_name()!r} is defined by multiple plugins: {owners}.",
        )


class RulesetOwnerConflictError(TypeError):
    def __init__(self, ruleset_type: type[Ruleset], plugin_names: Iterable[PluginName]):
        plugin_names = sorted(frozenset(plugin_names))
        owners = ", ".join(plugin_names)
        super().__init__(
            ruleset_type,
            f"Ruleset type {ruleset_type.get_name()!r} is defined by multiple plugins: {owners}.",
        )


@typing.overload
def load_plugins(
    *,
    select: None = None,
    exclude: None = None,
) -> PluginRegistry: ...


@typing.overload
def load_plugins(
    *,
    select: Iterable[PluginName],
    exclude: None = None,
) -> PluginRegistry: ...


@typing.overload
def load_plugins(
    *,
    select: None = None,
    exclude: Iterable[PluginName],
) -> PluginRegistry: ...


def load_plugins(
    *,
    select: Iterable[PluginName] | None = None,
    exclude: Iterable[PluginName] | None = None,
) -> PluginRegistry:
    """Load installed plugins.

    If `select` is provided, only the plugins in `select` will be loaded.
    If `exclude` is provided, the plugins in `exclude` will not be loaded.

    The arguments `select` and `exclude` are mutually exclusive.

    Args:
        select: A list of plugin names to select.
        exclude: A list of plugin names to exclude.
    """
    if select and exclude:
        raise TypeError("`select` and `exclude` are mutually exclusive")

    select = frozenset(select) if select is not None else None
    exclude = frozenset(exclude) if exclude is not None else None

    plugin_registry_builder: dict[PluginName, type[Plugin]] = {}

    for entry_point in entry_points(group=PLUGINS_GROUP_NAME):
        plugin_name = entry_point.name

        if select is not None and plugin_name not in select:
            continue

        if exclude is not None and plugin_name in exclude:
            continue

        plugin = entry_point.load()

        if not issubclass(plugin, Plugin):
            raise WrongPluginClassError(plugin.__name__)

        if plugin_name in plugin_registry_builder:
            raise DuplicatePluginError(plugin_name)

        plugin_registry_builder[plugin_name] = plugin

    if select:
        missing_required_plugins = select.difference(plugin_registry_builder)
        if missing_required_plugins:
            raise MissingSelectedPluginsError(missing_required_plugins)

    return PluginRegistry(plugin_registry_builder)


def build_sources_registry(plugin_registry: PluginRegistry) -> SourcesRegistry:
    source_owners: dict[type[Source], set[PluginName]] = defaultdict(set)
    sources_registry_builder: dict[SourceName, type[Source]] = {}

    for plugin_name, plugin in plugin_registry.items():
        for source_type in plugin.get_source_types():
            source_name = source_type.get_name()
            source_owners[source_type].add(plugin_name)
            sources_registry_builder[source_name] = source_type

    for source_type, plugin_names in source_owners.items():
        if len(plugin_names) > 1:
            raise SourceOwnerConflictError(source_type, plugin_names)

    return SourcesRegistry(sources_registry_builder)


def build_connectors_registry(plugin_registry: PluginRegistry) -> ConnectorsRegistry:
    connector_owners: dict[type[Connector], set[PluginName]] = defaultdict(set)
    connectors_registry_builder: dict[ConnectorName, type[Connector]] = {}

    for plugin_name, plugin in plugin_registry.items():
        for connector_type in plugin.get_connector_types():
            connector_name = connector_type.get_name()
            connector_owners[connector_type].add(plugin_name)
            connectors_registry_builder[connector_name] = connector_type

    for connector_type, plugin_names in connector_owners.items():
        if len(plugin_names) > 1:
            raise ConnectorOwnerConflictError(connector_type, plugin_names)

    return ConnectorsRegistry(connectors_registry_builder)


def build_rulesets_registry(plugin_registry: PluginRegistry) -> RulesetsRegistry:
    ruleset_owners: dict[type[Ruleset], set[PluginName]] = defaultdict(set)
    rulesets_registry_builder: dict[RulesetName, type[Ruleset]] = {}

    for plugin_name, plugin in plugin_registry.items():
        for ruleset_type in plugin.get_ruleset_types():
            ruleset_name = ruleset_type.get_name()
            ruleset_owners[ruleset_type].add(plugin_name)
            rulesets_registry_builder[ruleset_name] = ruleset_type

    for ruleset_type, plugin_names in ruleset_owners.items():
        if len(plugin_names) > 1:
            raise RulesetOwnerConflictError(ruleset_type, plugin_names)

    return RulesetsRegistry(rulesets_registry_builder)
