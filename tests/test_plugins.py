from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from waivern_analyser._plugins import (
    DuplicatePluginError,
    MissingSelectedPluginsError,
    PluginRegistry,
    WrongPluginClassError,
    load_plugins,
)
from waivern_analyser.plugins import Plugin


class Plugin1(Plugin):
    pass


class Plugin2(Plugin):
    pass


class MockInvalidPluginNotSubclassOfPlugin:
    """Mock invalid plugin class.

    This plugin is invalid because it is not a subclass of Plugin.
    """


@pytest.fixture
def mock_entry_point_plugin1(mocker: MockerFixture) -> Mock:
    """Fixture that provides a mock entry point for testing."""
    mock_entry_point_plugin1 = mocker.MagicMock()
    mock_entry_point_plugin1.name = "plugin1"
    mock_entry_point_plugin1.load.return_value = Plugin1
    return mock_entry_point_plugin1


@pytest.fixture
def mock_entry_point_plugin2(mocker: MockerFixture) -> Mock:
    """Fixture that provides a mock entry point for testing."""
    mock_entry_point_plugin2 = mocker.MagicMock()
    mock_entry_point_plugin2.name = "plugin2"
    mock_entry_point_plugin2.load.return_value = Plugin2
    return mock_entry_point_plugin2


@pytest.fixture
def mock_entry_point_invalid_plugin(mocker: MockerFixture) -> Mock:
    """Fixture that provides a mock entry point for testing."""
    mock_entry_point_invalid_plugin = mocker.MagicMock()
    mock_entry_point_invalid_plugin.name = "invalid_plugin"
    mock_entry_point_invalid_plugin.load.return_value = (
        MockInvalidPluginNotSubclassOfPlugin
    )
    return mock_entry_point_invalid_plugin


def test_load_valid_plugins(
    mocker: MockerFixture,
    mock_entry_point_plugin1: Mock,
    mock_entry_point_plugin2: Mock,
):
    """Test loading all available plugins."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        return_value=[mock_entry_point_plugin1, mock_entry_point_plugin2],
    )

    registry = load_plugins()

    assert registry == PluginRegistry(
        {
            "plugin1": Plugin1,
            "plugin2": Plugin2,
        }
    )


def test_load_plugins_with_select(
    mocker: MockerFixture,
    mock_entry_point_plugin1: Mock,
    mock_entry_point_plugin2: Mock,
):
    """Test loading only selected plugins."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        return_value=[mock_entry_point_plugin1, mock_entry_point_plugin2],
    )

    registry = load_plugins(select=["plugin1"])

    assert registry == PluginRegistry(
        {
            "plugin1": Plugin1,
        }
    )


def test_load_plugins_with_exclude(
    mocker: MockerFixture,
    mock_entry_point_plugin1: Mock,
    mock_entry_point_plugin2: Mock,
):
    """Test loading plugins with exclusions."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        return_value=[mock_entry_point_plugin1, mock_entry_point_plugin2],
    )

    registry = load_plugins(exclude=["plugin2"])

    assert registry == PluginRegistry(
        {
            "plugin1": Plugin1,
        }
    )


def test_duplicate_plugin_error(
    mocker: MockerFixture,
    mock_entry_point_plugin1: Mock,
):
    """Test that duplicate plugins raise an error."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        # Create a duplicate entry point
        return_value=[mock_entry_point_plugin1, mock_entry_point_plugin1],
    )

    with pytest.raises(DuplicatePluginError) as exc_info:
        load_plugins()

    assert exc_info.value.args[0] == "plugin1"


def test_missing_selected_plugins_error(
    mocker: MockerFixture,
    mock_entry_point_plugin1: Mock,
):
    """Test that missing selected plugins raise an error."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        return_value=[mock_entry_point_plugin1],
    )

    with pytest.raises(MissingSelectedPluginsError) as exc_info:
        load_plugins(select=["plugin1", "nonexistent_plugin"])

    assert "nonexistent_plugin" in exc_info.value.args[0]


def test_wrong_plugin_class_error(
    mocker: MockerFixture,
    mock_entry_point_invalid_plugin: Mock,
):
    """Test that invalid plugin classes raise an error."""
    mocker.patch(
        "waivern_analyser._plugins.entry_points",
        return_value=[mock_entry_point_invalid_plugin],
    )

    with pytest.raises(WrongPluginClassError) as exc_info:
        load_plugins()

    assert exc_info.value.args[0] == "MockInvalidPluginNotSubclassOfPlugin"


def test_select_exclude_mutually_exclusive():
    """Test that select and exclude parameters are mutually exclusive."""
    with pytest.raises(
        TypeError, match="`select` and `exclude` are mutually exclusive"
    ):
        # We need to use None here to match the overload signatures
        load_plugins(select=["plugin1"], exclude=["plugin2"])  # type: ignore
