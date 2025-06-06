import sys
import typing
from collections.abc import Iterable

if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from waivern_analyser.plugin import Plugin

PLUGINS_GROUP_NAME = "waivern-plugins"

PluginName: typing.TypeAlias = str


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


class PluginRegistry(dict[PluginName, type[Plugin]]):
    pass


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

    plugin_registry = PluginRegistry()

    for entry_point in entry_points(group=PLUGINS_GROUP_NAME):
        plugin_name = entry_point.name

        if select is not None and plugin_name not in select:
            continue

        if exclude is not None and plugin_name in exclude:
            continue

        plugin = entry_point.load()

        if not issubclass(plugin, Plugin):
            raise WrongPluginClassError(plugin.__name__)

        if plugin_name in plugin_registry:
            raise DuplicatePluginError(plugin_name)

        plugin_registry[plugin_name] = plugin

    if select:
        missing_required_plugins = select.difference(plugin_registry)
        if missing_required_plugins:
            raise MissingSelectedPluginsError(missing_required_plugins)

    return plugin_registry
