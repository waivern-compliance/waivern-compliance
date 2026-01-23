"""Unit tests for GDPRDataSubjectClassifierConfig."""

from waivern_gdpr_data_subject_classifier.types import GDPRDataSubjectClassifierConfig


class TestGDPRDataSubjectClassifierConfig:
    """Test suite for GDPRDataSubjectClassifierConfig."""

    def test_config_default_has_llm_validation_disabled(self) -> None:
        """Test that default config has LLM validation disabled."""
        config = GDPRDataSubjectClassifierConfig()

        assert config.llm_validation.enable_llm_validation is False

    def test_config_from_properties_with_llm_validation_enabled(self) -> None:
        """Test that config can be created from properties with LLM validation enabled."""
        properties = {
            "llm_validation": {
                "enable_llm_validation": True,
                "llm_batch_size": 100,
            }
        }

        config = GDPRDataSubjectClassifierConfig.from_properties(properties)

        assert config.llm_validation.enable_llm_validation is True
        assert config.llm_validation.llm_batch_size == 100

    def test_config_from_properties_with_partial_llm_validation(self) -> None:
        """Test that partial llm_validation config uses defaults for unspecified fields."""
        properties = {
            "llm_validation": {
                "llm_batch_size": 75,
            }
        }

        config = GDPRDataSubjectClassifierConfig.from_properties(properties)

        # Specified value should be applied
        assert config.llm_validation.llm_batch_size == 75
        # Unspecified fields should use defaults
        assert config.llm_validation.enable_llm_validation is False
        assert config.llm_validation.llm_validation_mode == "standard"
