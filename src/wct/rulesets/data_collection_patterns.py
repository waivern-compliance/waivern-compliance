"""Data collection patterns ruleset.

This module defines patterns for detecting data collection mechanisms
in source code, such as HTTP form data, cookies, sessions, and API endpoints.
All patterns use simple string matching for human readability and easy maintenance.
"""

import logging
from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

logger = logging.getLogger(__name__)

# Version constant for this ruleset (private)
_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "data_collection_patterns"

_DATA_COLLECTION_PATTERNS: Final[dict[str, RuleData]] = {
    "php_post_data": {
        "description": "PHP POST data collection patterns",
        "patterns": (
            "$_POST[",
            "_POST[",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "form_data",
            "data_source": "http_post",
            "compliance_relevance": "Form data collection detection for GDPR compliance",
        },
    },
    "php_get_data": {
        "description": "PHP GET parameter collection patterns",
        "patterns": (
            "$_GET[",
            "_GET[",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "url_parameters",
            "data_source": "http_get",
            "compliance_relevance": "URL parameter data collection detection",
        },
    },
    "php_cookie_access": {
        "description": "PHP cookie access patterns",
        "patterns": (
            "$_COOKIE[",
            "_COOKIE[",
            "setcookie(",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "cookies",
            "data_source": "browser_cookies",
            "compliance_relevance": "Cookie-based data storage and retrieval",
        },
    },
    "php_session_data": {
        "description": "PHP session data patterns",
        "patterns": (
            "$_SESSION[",
            "_SESSION[",
            "session_start",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "session_data",
            "data_source": "server_session",
            "compliance_relevance": "Session-based data storage detection",
        },
    },
    "html_input_fields": {
        "description": "HTML form input field patterns",
        "patterns": (
            'name="',
            "name='",
            "<input",
            "<textarea",
            "<select",
        ),
        "risk_level": "low",
        "metadata": {
            "collection_type": "html_forms",
            "data_source": "html_form",
            "compliance_relevance": "HTML form-based data collection detection",
        },
    },
    "javascript_storage": {
        "description": "JavaScript local storage and data access",
        "patterns": (
            "localStorage",
            "sessionStorage",
            "document.cookie",
            "FormData",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "client_storage",
            "data_source": "browser_javascript",
            "compliance_relevance": "Client-side data collection and storage",
        },
    },
    "file_uploads": {
        "description": "File upload processing patterns",
        "patterns": (
            "$_FILES[",
            "move_uploaded_file",
            "is_uploaded_file",
            "file_get_contents",
            "upload",
        ),
        "risk_level": "high",
        "metadata": {
            "collection_type": "file_upload",
            "data_source": "uploaded_files",
            "compliance_relevance": "File uploads may contain personal data requiring special handling",
        },
    },
    "sql_database_queries": {
        "description": "SQL database query patterns for data retrieval and manipulation",
        "patterns": (
            "SELECT",
            "INSERT INTO",
            "UPDATE",
            "DELETE FROM",
            "WHERE email",
            "WHERE phone",
            "WHERE user_id",
            "WHERE customer_id",
            "FROM users",
            "FROM customers",
            "FROM profiles",
            "->prepare(",
            "->execute(",
            "mysqli_query",
            "mysql_query",
            "pg_query",
            "sqlite_query",
        ),
        "risk_level": "high",
        "metadata": {
            "collection_type": "database_query",
            "data_source": "database",
            "compliance_relevance": "SQL queries may access or modify personal data in databases",
        },
    },
    "database_connections": {
        "description": "Database connection and ORM patterns",
        "patterns": (
            "PDO::",
            "new PDO(",
            "mysqli_connect",
            "mysql_connect",
            "pg_connect",
            "new Database",
            "->connection",
            "::connection",
            "Eloquent::",
            "Model::",
            "ActiveRecord::",
            "->query(",
            "->find(",
            "->where(",
            "->get(",
            "->save(",
            "->create(",
            "->update(",
            "->delete(",
        ),
        "risk_level": "medium",
        "metadata": {
            "collection_type": "database_connection",
            "data_source": "database",
            "compliance_relevance": "Database connections enable access to stored personal data",
        },
    },
}


class DataCollectionPatternsRuleset(Ruleset):
    """Ruleset for detecting data collection patterns in source code."""

    def __init__(self) -> None:
        """Initialise the data collection patterns ruleset."""
        super().__init__()
        self.rules: tuple[Rule, ...] | None = None
        logger.debug(f"Initialised {self.name} ruleset version {self.version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return _RULESET_NAME

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return _VERSION

    @override
    def get_rules(self) -> tuple[Rule, ...]:
        """Get the data collection patterns rules.

        Returns:
            Immutable tuple of Rule objects containing all data collection patterns

        """
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _DATA_COLLECTION_PATTERNS.items():
                rules_list.append(
                    Rule(
                        name=rule_name,
                        description=rule_data["description"],
                        patterns=rule_data["patterns"],
                        risk_level=rule_data["risk_level"],
                        metadata=rule_data["metadata"],
                    )
                )
            self.rules = tuple(rules_list)
            logger.debug(f"Generated {len(self.rules)} data collection patterns rules")

        return self.rules
