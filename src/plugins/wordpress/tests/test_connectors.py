from pathlib import Path

import pytest
from waivern_wordpress_plugin.connectors import (
    NoWordpressProject,
    WordpressConnector,
    WordpressProjectConfig,
    WordpressProjectConnection,
)

from waivern_analyser.connectors import UnsupportedSourceType
from waivern_analyser.sources import DirectorySource, FileSource, Source


class TestWordpressProjectConnector:
    """Test cases for WordpressProjectConnector."""

    @pytest.fixture
    def wordpress_config(self) -> WordpressProjectConfig:
        """Fixture providing a default WordPress project configuration."""
        return WordpressProjectConfig()

    @pytest.fixture
    def connector(self, wordpress_config: WordpressProjectConfig) -> WordpressConnector:
        """Fixture providing a WordpressProjectConnector instance."""
        return WordpressConnector(config=wordpress_config)

    def test_get_name(self):
        """Test that get_name returns the correct connector name."""
        assert WordpressConnector.get_name() == "wordpress"

    def test_from_properties_with_empty_dict(self):
        """Test creating connector from empty properties dictionary."""
        connector = WordpressConnector.from_properties({})

        assert isinstance(connector, WordpressConnector)
        assert isinstance(connector.config, WordpressProjectConfig)
        # Check that the default values are used
        assert connector.config == WordpressProjectConfig()

    def test_from_properties_with_custom_values(self):
        """Test creating connector from properties dictionary with custom values."""
        properties = {
            "config_file": "custom-wp-config.php",
            "core_files": ["custom-wp-load.php"],
            "db_table_prefix": "custom_wp_",
        }

        connector = WordpressConnector.from_properties(properties)

        assert isinstance(connector, WordpressConnector)
        assert connector.config.config_file == "custom-wp-config.php"
        assert connector.config.core_files == ("custom-wp-load.php",)
        assert connector.config.db_table_prefix == "custom_wp_"

    def test_connect_with_directory_source_success(self, connector: WordpressConnector):
        """Test connecting with a DirectorySource that contains a valid WordPress project."""
        mock_path = Mock(spec=Path)
        directory_source = DirectorySource(path=mock_path)

        with patch.object(
            WordpressProjectConnection, "from_directory"
        ) as mock_from_directory:
            mock_connection = Mock(spec=WordpressProjectConnection)
            mock_from_directory.return_value = mock_connection

            result = connector.connect(directory_source)

            assert result == mock_connection
            mock_from_directory.assert_called_once_with(mock_path, connector.config)

    def test_connect_with_file_source_success(self, connector):
        """Test connecting with a FileSource."""
        mock_path = Mock(spec=Path)
        file_source = FileSource(path=mock_path)

        with patch.object(WordpressProjectConnection, "from_file") as mock_from_file:
            mock_connection = Mock(spec=WordpressProjectConnection)
            mock_from_file.return_value = mock_connection

            result = connector.connect(file_source)

            assert result == mock_connection
            mock_from_file.assert_called_once_with(mock_path, connector.config)

    def test_connect_with_unsupported_source_type(self, connector):
        """Test connecting with an unsupported source type."""
        unsupported_source = Mock(spec=Source)

        result = connector.connect(unsupported_source)

        assert isinstance(result, UnsupportedSourceType)
        assert result.connector == connector
        assert result.source == unsupported_source


class TestWordpressProjectConnection:
    """Test cases for WordpressProjectConnection."""

    @pytest.fixture
    def default_config(self):
        """Fixture providing a default WordPress project configuration."""
        return WordpressProjectConfig()

    @pytest.fixture
    def mock_directory(self):
        """Fixture providing a mock directory path."""
        return Mock(spec=Path)

    def test_from_file_calls_from_directory(self, default_config):
        """Test that from_file calls from_directory with the parent directory."""
        mock_file = Mock(spec=Path)
        mock_parent = Mock(spec=Path)
        mock_file.parent = mock_parent

        with patch.object(
            WordpressProjectConnection, "from_directory"
        ) as mock_from_directory:
            mock_connection = Mock(spec=WordpressProjectConnection)
            mock_from_directory.return_value = mock_connection

            result = WordpressProjectConnection.from_file(mock_file, default_config)

            assert result == mock_connection
            mock_from_directory.assert_called_once_with(mock_parent, default_config)

    def test_from_directory_success(self, default_config, mock_directory):
        """Test successful creation of connection from directory."""
        # Mock the config file
        mock_config_file = Mock(spec=Path)
        mock_config_file.is_file.return_value = True
        mock_directory.__truediv__.return_value = mock_config_file

        # Mock core files
        mock_core_file = Mock(spec=Path)
        mock_core_file.exists.return_value = True

        with patch.object(Path, "__truediv__", return_value=mock_core_file):
            result = WordpressProjectConnection.from_directory(
                mock_directory, default_config
            )

            assert isinstance(result, WordpressProjectConnection)
            assert result.root == mock_directory
            assert result.config == default_config

    def test_from_directory_missing_config_file(self, default_config, mock_directory):
        """Test from_directory when config file is missing."""
        # Mock the config file as not existing
        mock_config_file = Mock(spec=Path)
        mock_config_file.is_file.return_value = False
        mock_directory.__truediv__.return_value = mock_config_file

        result = WordpressProjectConnection.from_directory(
            mock_directory, default_config
        )

        assert isinstance(result, NoWordpressProject)
        assert "config file" in result.reason_
        assert str(mock_config_file) in result.reason_

    def test_from_directory_missing_core_files(self, default_config, mock_directory):
        """Test from_directory when core files are missing."""
        # Mock the config file as existing
        mock_config_file = Mock(spec=Path)
        mock_config_file.is_file.return_value = True

        # Mock core files as not existing
        mock_core_file = Mock(spec=Path)
        mock_core_file.exists.return_value = False

        def mock_truediv(self, other):
            if other == default_config.config_file:
                return mock_config_file
            else:
                return mock_core_file

        with patch.object(Path, "__truediv__", side_effect=mock_truediv):
            result = WordpressProjectConnection.from_directory(
                mock_directory, default_config
            )

            assert isinstance(result, NoWordpressProject)
            assert "core files" in result.reason_

    def test_from_directory_some_core_files_missing(
        self, default_config, mock_directory
    ):
        """Test from_directory when some core files are missing."""
        # Mock the config file as existing
        mock_config_file = Mock(spec=Path)
        mock_config_file.is_file.return_value = True

        # Mock some core files as existing, others as not
        def mock_core_file_exists(core_file_name):
            # First core file exists, others don't
            return core_file_name == default_config.core_files[0]

        def mock_truediv(self, other):
            if other == default_config.config_file:
                return mock_config_file
            else:
                mock_core_file = Mock(spec=Path)
                mock_core_file.exists.return_value = mock_core_file_exists(other)
                return mock_core_file

        with patch.object(Path, "__truediv__", side_effect=mock_truediv):
            result = WordpressProjectConnection.from_directory(
                mock_directory, default_config
            )

            assert isinstance(result, NoWordpressProject)
            assert "core files" in result.reason_

    def test_connection_immutability(self, default_config, mock_directory):
        """Test that WordpressProjectConnection is immutable (frozen dataclass)."""
        connection = WordpressProjectConnection(
            root=mock_directory, config=default_config
        )

        with pytest.raises(AttributeError):
            connection.root = Mock(spec=Path)

        with pytest.raises(AttributeError):
            connection.config = WordpressProjectConfig()


class TestNoWordpressProject:
    """Test cases for NoWordpressProject."""

    def test_creation_with_reason(self):
        """Test creating NoWordpressProject with a reason."""
        reason = "Test reason for no WordPress project"
        no_wp = NoWordpressProject(reason_=reason)

        assert no_wp.reason_ == reason

    def test_inherits_from_not_connected_with_reason(self):
        """Test that NoWordpressProject inherits from NotConnectedWithReason."""
        from waivern_analyser.connectors import NotConnectedWithReason

        no_wp = NoWordpressProject(reason_="test")
        assert isinstance(no_wp, NotConnectedWithReason)


class TestIntegration:
    """Integration tests for the WordPress connector system."""

    @pytest.fixture
    def temp_wp_project(self, tmp_path):
        """Create a temporary WordPress project directory for testing."""
        wp_dir = tmp_path / "wordpress_project"
        wp_dir.mkdir()

        # Create required files
        (wp_dir / "wp-config.php").touch()
        (wp_dir / "wp-load.php").touch()
        (wp_dir / "wp-login.php").touch()
        (wp_dir / "wp-admin").mkdir()

        return wp_dir

    @pytest.fixture
    def incomplete_wp_project(self, tmp_path):
        """Create a temporary incomplete WordPress project directory for testing."""
        wp_dir = tmp_path / "incomplete_wordpress_project"
        wp_dir.mkdir()

        # Create only some required files
        (wp_dir / "wp-config.php").touch()
        # wp-load.php is missing

        return wp_dir

    def test_end_to_end_success(self, temp_wp_project):
        """Test the complete flow from connector to connection with a valid WordPress project."""
        config = WordpressProjectConfig()
        connector = WordpressConnector(config=config)
        source = DirectorySource(path=temp_wp_project)

        result = connector.connect(source)

        assert isinstance(result, WordpressProjectConnection)
        assert result.root == temp_wp_project
        assert result.config == config

    def test_end_to_end_failure(self, incomplete_wp_project):
        """Test the complete flow with an incomplete WordPress project."""
        config = WordpressProjectConfig()
        connector = WordpressConnector(config=config)
        source = DirectorySource(path=incomplete_wp_project)

        result = connector.connect(source)

        assert isinstance(result, NoWordpressProject)
        assert "core files" in result.reason_

    def test_file_source_integration(self, temp_wp_project):
        """Test integration with FileSource pointing to a file in a WordPress project."""
        config = WordpressProjectConfig()
        connector = WordpressConnector(config=config)

        # Point to a file within the WordPress project
        wp_file = temp_wp_project / "wp-config.php"
        source = FileSource(path=wp_file)

        result = connector.connect(source)

        assert isinstance(result, WordpressProjectConnection)
        assert result.root == temp_wp_project
        assert result.config == config
