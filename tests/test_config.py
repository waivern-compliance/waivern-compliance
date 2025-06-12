import textwrap
from pathlib import Path

import pytest
import yaml
from pytest_mock import MockerFixture

from waivern_analyser.config import (
    Config,
    InvalidConfigFileError,
    InvalidConfigFileSchemaError,
    InvalidYamlConfigFileError,
)


class TestConfig:
    """Test suite for Config class."""

    def test_default_config(self):
        """Test creating default config."""
        config = Config.default()
        assert config.select_plugins is None
        assert config.exclude_plugins is None

    def test_config_forbids_extra_fields(self):
        """Test that config forbids extra fields."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            Config(**{"unknown_field": "value"})  # type: ignore

    def test_config_is_frozen(self):
        """Test that config is immutable (frozen)."""
        config = Config()
        with pytest.raises(ValueError, match="Instance is frozen"):
            config.select_plugins = ("plugin1",)


class TestConfigValidators:
    """Test suite for Config validators."""

    def test_select_and_exclude_both_empty_allowed(self):
        """Test that both select_plugins and exclude_plugins can be None."""
        config = Config(select_plugins=None, exclude_plugins=None)
        assert config.select_plugins is None
        assert config.exclude_plugins is None

    @pytest.mark.parametrize(
        ("select_plugins", "exclude_plugins"),
        (
            (("plugin1", "plugin2"), None),
            (None, ("plugin2", "plugin3")),
            ((), None),
            (None, ()),
        ),
    )
    def test_either_select_or_exclude_plugins_allowed(
        self,
        select_plugins: tuple[str, ...] | None,
        exclude_plugins: tuple[str, ...] | None,
    ):
        """Test that either select_plugins or exclude_plugins can be None."""
        config = Config(select_plugins=select_plugins, exclude_plugins=exclude_plugins)
        assert config.select_plugins == select_plugins
        assert config.exclude_plugins == exclude_plugins

    def test_duplicate_select_plugins_raises_error(self):
        """Test that duplicate select_plugins raise validation error."""
        with pytest.raises(
            ValueError,
            match="The following plugins are repeated in 'select_plugins': \\['plugin1'\\]",
        ):
            Config(select_plugins=("plugin1", "plugin2", "plugin1"))

    def test_duplicate_exclude_plugins_raises_error(self):
        """Test that duplicate exclude_plugins raise validation error."""
        with pytest.raises(
            ValueError,
            match="The following plugins are repeated in 'exclude_plugins': \\['plugin2'\\]",
        ):
            Config(exclude_plugins=("plugin1", "plugin2", "plugin2"))

    def test_multiple_duplicates_in_plugins(self):
        """Test multiple duplicates in plugins list."""
        with pytest.raises(
            ValueError,
            match="The following plugins are repeated in 'select_plugins': \\['plugin1', 'plugin2'\\]",
        ):
            Config(
                select_plugins=("plugin1", "plugin2", "plugin1", "plugin2", "plugin3")
            )

    def test_select_and_exclude_mutually_exclusive(self):
        """Test that select_plugins and exclude_plugins are mutually exclusive."""
        with pytest.raises(
            ValueError,
            match="`select_plugins` and `exclude_plugins` are mutually exclusive",
        ):
            Config(select_plugins=("plugin1",), exclude_plugins=("plugin2",))


class TestConfigFromFile:
    """Test suite for Config.from_file method."""

    def test_from_file_with_valid_yaml(self, tmp_path):
        """Test loading config from valid YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                    select_plugins:
                    - plugin1
                    - plugin2
                """
            ).strip()
        )

        config = Config.from_file(config_file)
        assert config.select_plugins == ("plugin1", "plugin2")
        assert config.exclude_plugins is None

    def test_from_file_with_empty_yaml(self, tmp_path):
        """Test loading config from empty YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config = Config.from_file(config_file)
        assert config.select_plugins is None
        assert config.exclude_plugins is None
        assert config == Config.default()

    def test_from_file_with_invalid_yaml(self, tmp_path):
        """Test loading config from invalid YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(
            InvalidYamlConfigFileError,
            match=f"Error loading YAML config file {config_file}",
        ):
            Config.from_file(config_file)

    def test_from_file_not_a_mapping(self, tmp_path):
        """Test loading config from not a mapping."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                    - plugin1
                    - plugin2
                """
            ).strip()
        )

        with pytest.raises(
            InvalidConfigFileSchemaError,
            match=f"Config file {config_file} must be a mapping, but got <class 'list'>",
        ):
            Config.from_file(config_file)

    def test_from_file_with_duplicate_plugins(self, tmp_path):
        """Test loading config with duplicate plugins."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent(
                """
                    select_plugins:
                    - plugin1
                    - plugin1
                """
            ).strip()
        )

        with pytest.raises(
            InvalidConfigFileSchemaError,
            match=f"Error validating config file {config_file}",
        ):
            Config.from_file(config_file)

    def test_from_file_with_mutually_exclusive_plugins(self, tmp_path):
        """Test loading config with both select and exclude plugins."""
        config_file = tmp_path / "config.yaml"
        config_data = {"select_plugins": ["plugin1"], "exclude_plugins": ["plugin2"]}
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(
            InvalidConfigFileSchemaError,
            match=f"Error validating config file {config_file}",
        ):
            Config.from_file(config_file)

    def test_from_file_with_extra_fields(self, tmp_path):
        """Test loading config with extra fields."""
        config_file = tmp_path / "config.yaml"
        config_data = {"select_plugins": ["plugin1"], "unknown_field": "value"}
        config_file.write_text(yaml.dump(config_data))

        with pytest.raises(
            InvalidConfigFileSchemaError,
            match=f"Error validating config file {config_file}",
        ):
            Config.from_file(config_file)

    def test_from_file_nonexistent_file(self):
        """Test loading config from nonexistent file."""
        nonexistent_file = Path("nonexistent.yaml")

        with pytest.raises(
            InvalidConfigFileError,
            match=f"Error loading config file {nonexistent_file}",
        ):
            Config.from_file(nonexistent_file)

    def test_from_file_permission_error(self, mocker: MockerFixture):
        """Test loading config when file cannot be opened due to permissions."""
        mocker.patch("builtins.open", side_effect=PermissionError("Permission denied"))
        config_file = Path("config.yaml")

        with pytest.raises(
            InvalidConfigFileError, match=f"Error loading config file {config_file}"
        ):
            Config.from_file(config_file)


class TestConfigLoadPlugins:
    """Test suite for Config.load_plugins method."""

    def test_load_plugins_with_select_plugins(self, mocker: MockerFixture):
        """Test load_plugins with select_plugins."""
        mock_registry = {}  # Mock registry object
        mock_load_plugins = mocker.patch("waivern_analyser.config._load_plugins")
        mock_load_plugins.return_value = mock_registry

        config = Config(select_plugins=("plugin1", "plugin2"))
        result = config.load_plugins()

        mock_load_plugins.assert_called_once_with(
            select=("plugin1", "plugin2"), exclude=None
        )
        assert result is mock_registry

    def test_load_plugins_with_exclude_plugins(self, mocker: MockerFixture):
        """Test load_plugins with exclude_plugins."""
        mock_registry = {}  # Mock registry object
        mock_load_plugins = mocker.patch("waivern_analyser.config._load_plugins")
        mock_load_plugins.return_value = mock_registry

        config = Config(exclude_plugins=("plugin1", "plugin2"))
        result = config.load_plugins()

        mock_load_plugins.assert_called_once_with(
            select=None, exclude=("plugin1", "plugin2")
        )
        assert result is mock_registry

    def test_load_plugins_with_no_plugins(self, mocker: MockerFixture):
        """Test load_plugins with no plugins specified."""
        mock_registry = {}  # Mock registry object
        mock_load_plugins = mocker.patch("waivern_analyser.config._load_plugins")
        mock_load_plugins.return_value = mock_registry

        config = Config()
        result = config.load_plugins()

        mock_load_plugins.assert_called_once_with(select=None, exclude=None)
        assert result is mock_registry


class TestExceptionClasses:
    """Test suite for custom exception classes."""

    def test_invalid_config_file_error_inheritance(self):
        """Test that InvalidConfigFileError inherits from ValueError."""
        assert issubclass(InvalidConfigFileError, ValueError)

    def test_invalid_yaml_config_file_error_inheritance(self):
        """Test that InvalidYamlConfigFileError inherits from InvalidConfigFileError."""
        assert issubclass(InvalidYamlConfigFileError, InvalidConfigFileError)
        assert issubclass(InvalidYamlConfigFileError, ValueError)

    def test_invalid_config_file_schema_error_inheritance(self):
        """Test that InvalidConfigFileSchemaError inherits from InvalidConfigFileError."""
        assert issubclass(InvalidConfigFileSchemaError, InvalidConfigFileError)
        assert issubclass(InvalidConfigFileSchemaError, ValueError)

    def test_exception_messages(self):
        """Test that custom exceptions can be raised with messages."""
        with pytest.raises(InvalidConfigFileError, match="Test message"):
            raise InvalidConfigFileError("Test message")

        with pytest.raises(InvalidYamlConfigFileError, match="YAML error"):
            raise InvalidYamlConfigFileError("YAML error")

        with pytest.raises(InvalidConfigFileSchemaError, match="Schema error"):
            raise InvalidConfigFileSchemaError("Schema error")
