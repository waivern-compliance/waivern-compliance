"""Tests for MongoDB connector configuration."""

import pytest
from waivern_core.errors import ConnectorConfigError

from waivern_mongodb import MongoDBConnectorConfig

MONGODB_ENV_VARS = ["MONGODB_URI", "MONGODB_DATABASE"]


class TestMongoDBConnectorConfig:
    """Tests for MongoDBConnectorConfig validation and creation."""

    def test_creates_config_with_required_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config is created when uri and database are provided."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://localhost:27017",
                "database": "healthcare_db",
            }
        )

        assert config.uri == "mongodb://localhost:27017"
        assert config.database == "healthcare_db"
        assert config.sample_size == 10  # Default

    def test_raises_error_when_uri_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConnectorConfigError is raised when uri is not provided."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="uri.*required"):
            MongoDBConnectorConfig.from_properties({"database": "test_db"})

    def test_raises_error_when_database_is_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConnectorConfigError is raised when database is not provided."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="database.*required"):
            MongoDBConnectorConfig.from_properties({"uri": "mongodb://localhost:27017"})

    def test_raises_error_when_uri_is_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConnectorConfigError is raised when uri is an empty string."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="uri.*required"):
            MongoDBConnectorConfig.from_properties({"uri": "", "database": "test_db"})

    def test_raises_error_when_database_is_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ConnectorConfigError is raised when database is an empty string."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        with pytest.raises(ConnectorConfigError, match="database.*required"):
            MongoDBConnectorConfig.from_properties(
                {"uri": "mongodb://localhost:27017", "database": ""}
            )

    def test_environment_variable_overrides_uri(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MONGODB_URI environment variable takes precedence over properties."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("MONGODB_URI", "mongodb://env-host:27017")

        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://property-host:27017",
                "database": "test_db",
            }
        )

        assert config.uri == "mongodb://env-host:27017"

    def test_environment_variable_overrides_database(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MONGODB_DATABASE environment variable takes precedence over properties."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("MONGODB_DATABASE", "env_database")

        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://localhost:27017",
                "database": "property_database",
            }
        )

        assert config.database == "env_database"

    def test_default_sample_size_is_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default sample_size is set when not provided."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://localhost:27017",
                "database": "test_db",
            }
        )

        assert config.sample_size == 10

    def test_custom_sample_size_is_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Custom sample_size value is accepted."""
        for var in MONGODB_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = MongoDBConnectorConfig.from_properties(
            {
                "uri": "mongodb://localhost:27017",
                "database": "test_db",
                "sample_size": 50,
            }
        )

        assert config.sample_size == 50
