"""Test the architectural improvement for source code schema input handler."""

from wct.analysers.personal_data_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)


class TestSourceCodeHandlerArchitecture:
    """Test the refactored architecture where handler manages its own rulesets."""

    def test_handler_initializes_without_external_patterns(self):
        """Test that handler can initialize without receiving patterns from analyser."""
        # This should not raise any exceptions
        handler = SourceCodeSchemaInputHandler()

        # Handler should have loaded its own rulesets
        assert handler.personal_data_patterns is not None
        assert handler.source_code_patterns is not None
        assert len(handler.personal_data_patterns) > 0
        assert len(handler.source_code_patterns) > 0

    def test_handler_has_self_contained_ruleset_management(self):
        """Test that handler manages its own ruleset dependencies."""
        handler = SourceCodeSchemaInputHandler()

        # Handler should have both required pattern types
        assert hasattr(handler, "personal_data_patterns")
        assert hasattr(handler, "source_code_patterns")

        # Should contain expected pattern categories
        assert "function_patterns" in handler.source_code_patterns
        assert "class_patterns" in handler.source_code_patterns
        assert "sql_table_patterns" in handler.source_code_patterns

        # Should have personal data patterns for field matching
        personal_data_categories = handler.personal_data_patterns.keys()
        MIN_EXPECTED_CATEGORIES = 10
        assert (
            len(personal_data_categories) > MIN_EXPECTED_CATEGORIES
        )  # Should have multiple categories

    def test_field_classification_works_independently(self):
        """Test that field classification works with handler's own patterns."""
        handler = SourceCodeSchemaInputHandler()

        # Test various field classifications
        test_cases = [
            ("email", "basic_profile"),  # Should match email patterns
            ("user_email", "basic_profile"),
            ("first_name", "basic_profile"),
            ("unknown_field", None),  # Should not match anything
        ]

        for field_name, expected_category in test_cases:
            result = handler._classify_field_as_personal_data(field_name)
            if expected_category is None:
                assert result is None, (
                    f"Expected no match for {field_name}, got {result}"
                )
            else:
                assert result is not None, f"Expected match for {field_name}, got None"

    def test_function_classification_works_independently(self):
        """Test that function classification works with handler's own patterns."""
        handler = SourceCodeSchemaInputHandler()

        # Test function name classification
        test_cases = [
            ("getUserData", "user_data"),
            ("sendEmail", "email"),
            ("authenticateUser", "authentication_data"),
            ("randomFunction", None),  # Should not match
        ]

        for func_name, expected_type in test_cases:
            result = handler._classify_function_as_personal_data(func_name)
            if expected_type is None:
                assert result is None, (
                    f"Expected no match for {func_name}, got {result}"
                )
            else:
                assert result is not None, f"Expected match for {func_name}, got None"

    def test_analyze_source_code_data_with_minimal_input(self):
        """Test that handler can analyze source code data independently."""
        handler = SourceCodeSchemaInputHandler()

        # Minimal test data
        test_data = {
            "data": [
                {
                    "file_path": "test.php",
                    "language": "php",
                    "functions": [
                        {
                            "name": "getUserEmail",
                            "line_start": 10,
                            "line_end": 15,
                            "parameters": [{"name": "email_address"}],
                        }
                    ],
                    "classes": [],
                    "data_collection_indicators": [],
                    "database_interactions": [],
                    "third_party_integrations": [],
                    "metadata": {"file_size": 1000},
                }
            ]
        }

        # Should not raise exceptions and should return findings
        findings = handler.analyze_source_code_data(test_data)
        assert isinstance(findings, list)
        # Should find at least the function and parameter patterns
        assert len(findings) >= 1
