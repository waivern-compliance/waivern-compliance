"""Data collection ruleset.

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
_RULESET_NAME: Final[str] = "data_collection"

_DATA_COLLECTION_PATTERNS: Final[dict[str, RuleData]] = {
    "php_post_data": {
        "description": "PHP POST data collection patterns",
        "patterns": (
            "$_POST[",
            "_POST[",
        ),
        "risk_level": "medium",
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 6 lawful basis required for processing form data, Article 13 information duties apply",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Electronic communications data collection requires user consent or legitimate interest",
            },
            {
                "regulation": "CCPA",
                "relevance": "Personal information collection from consumers must comply with notice and opt-out requirements",
            },
        ],
        "metadata": {
            "collection_type": "form_data",
            "data_source": "http_post",
        },
    },
    "php_get_data": {
        "description": "PHP GET parameter collection patterns",
        "patterns": (
            "$_GET[",
            "_GET[",
        ),
        "risk_level": "medium",
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "URL parameters may contain personal data requiring Article 6 lawful basis and Article 14 information duties",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "URL tracking parameters may require consent under electronic communications privacy rules",
            },
            {
                "regulation": "CCPA",
                "relevance": "URL parameters containing personal information subject to consumer privacy rights and disclosure requirements",
            },
        ],
        "metadata": {
            "collection_type": "url_parameters",
            "data_source": "http_get",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Cookies containing personal data require Article 6 lawful basis and Article 7 consent where applicable",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Non-essential cookies require explicit user consent before storage or access under Cookie Law",
            },
            {
                "regulation": "CCPA",
                "relevance": "Cookies used for tracking or containing personal information subject to consumer opt-out rights",
            },
        ],
        "metadata": {
            "collection_type": "cookies",
            "data_source": "browser_cookies",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Session data processing requires Article 6 lawful basis and appropriate retention periods under Article 5",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Session tracking mechanisms may require consent for electronic communications monitoring",
            },
        ],
        "metadata": {
            "collection_type": "session_data",
            "data_source": "server_session",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "HTML forms collecting personal data require Article 13 information provision and Article 6 lawful basis",
            },
            {
                "regulation": "CCPA",
                "relevance": "Form data collection must comply with consumer notice requirements and right to know categories of information collected",
            },
        ],
        "metadata": {
            "collection_type": "html_forms",
            "data_source": "html_form",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Client-side storage of personal data requires Article 6 lawful basis and transparent information under Article 13",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Browser storage mechanisms require consent when used for tracking or storing personal data",
            },
            {
                "regulation": "CCPA",
                "relevance": "Local storage containing personal information subject to consumer access and deletion rights",
            },
        ],
        "metadata": {
            "collection_type": "client_storage",
            "data_source": "browser_javascript",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "File uploads may contain personal data requiring Article 6 lawful basis, data minimisation under Article 5, and secure processing under Article 32",
            },
            {
                "regulation": "CCPA",
                "relevance": "Uploaded files containing personal information must comply with consumer rights to know, access, and delete personal information",
            },
        ],
        "metadata": {
            "collection_type": "file_upload",
            "data_source": "uploaded_files",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Database operations on personal data require Article 6 lawful basis, data accuracy under Article 5, and appropriate technical measures under Article 32",
            },
            {
                "regulation": "CCPA",
                "relevance": "Database queries accessing personal information must support consumer rights to know, access, delete, and correct personal information",
            },
            {
                "regulation": "SOX",
                "relevance": "Financial data queries require adequate internal controls and data integrity measures under Section 404",
            },
        ],
        "metadata": {
            "collection_type": "database_query",
            "data_source": "database",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Database connections accessing personal data must implement appropriate security measures under Article 32 and ensure lawful processing under Article 6",
            },
            {
                "regulation": "CCPA",
                "relevance": "Database access to personal information requires adequate security and must support consumer privacy rights implementation",
            },
            {
                "regulation": "SOX",
                "relevance": "Database connections handling financial data must maintain adequate internal controls and audit trails under Section 404",
            },
        ],
        "metadata": {
            "collection_type": "database_connection",
            "data_source": "database",
        },
    },
}


class DataCollectionRuleset(Ruleset):
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
                        compliance=rule_data["compliance"],
                        metadata=rule_data["metadata"],
                    )
                )
            self.rules = tuple(rules_list)
            logger.debug(f"Generated {len(self.rules)} data collection patterns rules")

        return self.rules
