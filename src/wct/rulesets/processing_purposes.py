"""Known processing purposes to search for during analysis."""

import re
from typing import Any, Final

from typing_extensions import override

from wct.rulesets.base import Ruleset

PROCESSING_PURPOSES: Final = {
    "Artificial Intelligence Model Training": {
        "keywords": [
            "model training",
            "machine learning",
            "ai training",
            "training data",
            "ml model",
            "learning model",
            "predictive model",
            "Google Vertex AI",
            "AWS Sagemaker",
            "Microsoft Azure Machine Learning",
            "IBM Watson Machine Learning",
            "DataRobot",
            "TensorFlow Extended",
            "Hugging Face Transformers",
            "Hopsworks",
            "Snorkel AI",
            "KubeFlow",
            "Feast",
        ],
        "category": "AI_AND_ML",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
    },
    "Artificial Intelligence Bias Testing": {
        "keywords": [
            "bias testing",
            "fairness testing",
            "model bias",
            "ai fairness",
            "bias detection",
            "fairness metrics",
            "IBM AI Fairness 360",
            "Microsoft Fairlearn",
            "Themis-ML",
            "SHAP",
            "LIME",
            "Uchicago Aequitas",
            "Google What-If Tool",
            "Responsibly",
            "ReBias",
            "Fiddler AI",
            "Arthur AI",
            "TruEra",
            "Credo AI",
            "AWS Sagemaker Clarify",
            "Parity AI",
        ],
        "category": "AI_AND_ML",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
    },
    "Artificial Intelligence Model Refinement": {
        "keywords": [
            "model refinement",
            "model improvement",
            "fine-tuning",
            "model optimization",
            "performance enhancement",
            "FinetuneDB",
            "Entry Point AI",
            "OpenAI API",
            "Google AI Platform Vizier",
            "AWS Sagemaker",
            "NVIDIA RTX AI Toolkit",
            "LMFlow",
            "Optuna",
            "Hyperopt",
            "MLFlow",
            "Deepchecks",
            "Granica Signal",
            "SuperAnnotate",
            "Kili Technology",
            "Cohere",
            "Scale AI",
            "LabelBox",
        ],
        "category": "AI_AND_ML",
        "risk_level": "medium",
        "compliance_frameworks": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
    },
    "Artificial Intelligence Performance Testing": {
        "keywords": [
            "performance testing",
            "model evaluation",
            "accuracy testing",
            "robustness testing",
            "efficiency testing",
            "Deepchecks",
            "AITEST",
            "MLPerf",
            "HPC AI500",
            "AIPerf",
            "MLCommons",
            "AILuminate",
            "Chatbot Arena",
            "HELM",
            "BIG-bench",
            "Decoding Trust Benchmark",
        ],
        "category": "AI_AND_ML",
        "risk_level": "medium",
        "compliance_frameworks": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
    },
    "Artificial Intelligence Security Testing": {
        "keywords": [
            "security testing",
            "penetration testing",
            "adversarial testing",
            "model security",
            "vulnerability testing",
            "IBM Adversarial Robustness Toolbox",
            "Microsoft Counterfit",
            "Garak",
            "Privacy Meter",
            "ai-exploits",
            "PenTest AI",
            "HCL App Scan",
            "Purple Llama",
            "Aptori",
            "AI Jack",
            "PenTest GPT",
            "DeVAIC",
            "Darktrace",
            "Synack",
            "ShellGPT",
        ],
        "category": "AI_AND_ML",
        "risk_level": "low",
        "compliance_frameworks": [
            "GDPR",
            "EU_AI_ACT",
            "NIST_AI_RMF",
            "ISO_27001",
            "SOC_2",
        ],
    },
    "Artificial Intelligence Compliance Management": {
        "keywords": [
            "compliance",
            "risk management",
            "governance",
            "regulatory compliance",
            "ethics",
            "accountability",
            "CentralEyes",
            "Compliance.ai",
            "IBM Watson",
            "AuditBoard",
            "TrustLayer",
            "Robust Intelligence",
            "FairNow",
            "LogicGate",
            "ValidMind",
            "Credo.ai",
            "Saidot",
            "HolisticAI",
            "OneTrust",
            "Fairly.ai",
            "Anch.ai",
            "Fiddler AI",
        ],
        "category": "AI_AND_ML",
        "risk_level": "low",
        "compliance_frameworks": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
    },
    "General Product and Service Delivery": {
        "keywords": [
            "service",
            "delivery",
            "product",
            "fulfill",
            "provide",
            "technical operations",
            "online services",
            "AWS",
            "Google Cloud",
            "Microsoft Azure",
            "Apache Web Server",
            "Shopify",
            "Webflow",
            "WordPress",
        ],
        "category": "OPERATIONAL",
        "risk_level": "low",
        "compliance_frameworks": ["GDPR"],
    },
    "Customer Service and Support": {
        "keywords": [
            "support",
            "customer",
            "help",
            "chat",
            "email",
            "inquiry",
            "ticket",
            "assistance",
            "Zendesk",
            "Freshdesk",
            "Intercom",
            "Salesforce ServiceCloud",
            "HelpScout",
            "LiveAgent",
        ],
        "category": "OPERATIONAL",
        "risk_level": "low",
        "compliance_frameworks": ["GDPR"],
    },
    "Customization of Products and Services": {
        "keywords": [
            "customization",
            "preferences",
            "settings",
            "user choice",
            "theme",
            "UI",
            "personalization",
        ],
        "category": "OPERATIONAL",
        "risk_level": "low",
        "compliance_frameworks": ["GDPR"],
    },
    "User Identity and Login Management": {
        "keywords": [
            "authentication",
            "login",
            "account",
            "profile",
            "credentials",
            "password",
            "user ID",
            "SSN",
            "Google Identity",
            "Facebook Login",
            "Apple Sign-In",
            "Okta",
            "Microsoft Active Directory",
            "ForgeRock",
        ],
        "category": "OPERATIONAL",
        "risk_level": "medium",
        "compliance_frameworks": ["GDPR"],
    },
    "Payment, Billing, and Invoicing": {
        "keywords": [
            "payment",
            "transaction",
            "billing",
            "purchase",
            "subscription",
            "order",
            "financial",
            "Stripe",
            "PayPal",
            "Adyen",
            "Square",
            "Braintree",
            "Worldpay",
            "Klarna",
            "Recurly",
        ],
        "category": "OPERATIONAL",
        "risk_level": "medium",
        "compliance_frameworks": ["GDPR", "PCI_DSS", "SOX"],
    },
    "Behavioral Data Analysis for Product Improvement": {
        "keywords": [
            "analytics",
            "tracking",
            "monitor",
            "measure",
            "behavior",
            "survey",
            "product improvement",
            "Adobe Analytics",
            "Snowflake",
            "Hotjar",
            "Piwik Pro",
            "Matomo",
            "Heap",
            "FullStory",
        ],
        "category": "ANALYTICS",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "CCPA", "CPRA"],
    },
    "Dynamic Personalization of Products and Services": {
        "keywords": [
            "personalization",
            "recommendation",
            "history",
            "mirror audience",
            "preferences",
            "targeting",
            "Braze",
            "Twilio",
            "Optimizely",
            "Dynamic Yield",
            "Adobe Target",
            "Coveo Relevance Cloud",
        ],
        "category": "MARKETING_AND_ADVERTISING",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "CCPA", "CPRA"],
    },
    "Consumer Marketing Within Owned Products": {
        "keywords": [
            "marketing",
            "promotion",
            "advertising",
            "notification",
            "email campaign",
            "loyalty program",
            "Braze",
            "SAP Emarsys",
            "Salesforce Marketing Cloud",
            "Klaviyo",
            "Omnisend",
            "Mailchimp",
            "Sendgrid",
            "Mailjet",
            "OneSignal",
        ],
        "category": "MARKETING_AND_ADVERTISING",
        "risk_level": "medium",
        "compliance_frameworks": ["GDPR", "CCPA", "CPRA"],
    },
    "Targeted Marketing via Third-Party Platforms": {
        "keywords": [
            "advertising",
            "targeting",
            "third-party marketing",
            "tracking",
            "custom audience",
            "retargeting",
            "Meta",
            "Snap",
            "Google Ads 360",
            "TikTok",
            "Twitter",
            "LinkedIn Ads",
        ],
        "category": "MARKETING_AND_ADVERTISING",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "CCPA", "CPRA"],
    },
    "Third-Party Marketing via Owned Products": {
        "keywords": [
            "partner marketing",
            "third-party advertising",
            "sponsored content",
            "custom audience",
            "Meta",
            "Snap",
            "Google Ads 360",
            "TikTok",
            "Third-party advertisers",
        ],
        "category": "MARKETING_AND_ADVERTISING",
        "risk_level": "high",
        "compliance_frameworks": ["GDPR", "CCPA", "CPRA"],
    },
    "Security, Fraud Prevention, and Abuse Detection": {
        "keywords": [
            "security",
            "fraud",
            "protection",
            "abuse",
            "compliance",
            "policy enforcement",
            "verification",
            "Scamalytics",
            "SEON",
            "Netcraft",
            "ThreatMark",
            "ComplyAdvantage",
            "Veriff",
            "Feedzai",
        ],
        "category": "SECURITY",
        "risk_level": "low",
        "compliance_frameworks": ["GDPR", "ISO_27001", "SOC_2"],
    },
}


class ProcessingPurposesRuleset(Ruleset):
    """Class-based processing purposes detection ruleset with logging support.

    This class provides structured access to processing purposes patterns
    with built-in logging capabilities for debugging and monitoring.

    Processing purposes help identify what business activities or data uses
    are mentioned in content, which is crucial for privacy compliance,
    consent management, and understanding data processing activities.
    """

    def __init__(self, ruleset_name: str = "processing_purposes") -> None:
        """Initialize the processing purposes ruleset.

        Args:
            ruleset_name: Name of the ruleset for logging purposes
        """
        super().__init__(ruleset_name)
        self.logger.debug(f"Initialized {self.__class__.__name__} ruleset")

    @override
    def get_patterns(self) -> dict[str, Any]:
        """Get the processing purposes patterns.

        Returns:
            Dictionary containing all processing purpose patterns with metadata
        """
        patterns = self._transform_to_pattern_format(PROCESSING_PURPOSES)
        self.logger.debug(
            f"Returning {len(patterns)} processing purpose pattern categories"
        )
        return patterns

    def _transform_to_pattern_format(
        self, raw_purposes: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Transform raw processing purposes into pattern format.

        Args:
            raw_purposes: Dictionary of processing purposes with metadata

        Returns:
            Dictionary formatted for pattern matching with metadata
        """
        patterns = {}

        for purpose_name, purpose_data in raw_purposes.items():
            keywords = purpose_data["keywords"]

            # Create case-insensitive regex patterns from keywords
            regex_patterns = []
            for keyword in keywords:
                # Escape special regex characters and create word boundary pattern
                escaped_keyword = re.escape(keyword.lower())
                # Use word boundaries for exact matches to avoid false positives
                pattern = rf"\b{escaped_keyword}\b"
                regex_patterns.append(pattern)

            patterns[purpose_name] = {
                "patterns": regex_patterns,
                "purpose_category": purpose_data["category"],
                "risk_level": purpose_data["risk_level"],
                "compliance_relevance": purpose_data["compliance_frameworks"],
                "keywords": keywords,  # Keep original keywords for reference
            }

        return patterns

    def get_patterns_by_risk_level(self, risk_level: str) -> dict[str, Any]:
        """Get processing purpose patterns by risk level.

        Args:
            risk_level: Risk level to filter by ("high", "medium", "low")

        Returns:
            Dictionary containing patterns matching the specified risk level
        """
        all_patterns = self.get_patterns()
        risk_patterns = {
            name: pattern
            for name, pattern in all_patterns.items()
            if pattern["risk_level"] == risk_level.lower()
        }

        self.logger.debug(
            f"Returning {len(risk_patterns)} patterns for risk level {risk_level}"
        )
        return risk_patterns

    def get_patterns_by_category(self, category: str) -> dict[str, Any]:
        """Get processing purpose patterns by category.

        Args:
            category: Category to filter by (AI_AND_ML, MARKETING_AND_ADVERTISING, etc.)

        Returns:
            Dictionary containing patterns matching the specified category
        """
        all_patterns = self.get_patterns()
        category_patterns = {
            name: pattern
            for name, pattern in all_patterns.items()
            if pattern["purpose_category"] == category.upper()
        }

        self.logger.debug(
            f"Returning {len(category_patterns)} patterns for category {category}"
        )
        return category_patterns

    def get_patterns_by_framework(self, framework: str) -> dict[str, Any]:
        """Get processing purpose patterns relevant to a compliance framework.

        Args:
            framework: Compliance framework (GDPR, CCPA, EU_AI_ACT, etc.)

        Returns:
            Dictionary containing patterns relevant to the specified framework
        """
        all_patterns = self.get_patterns()
        framework_patterns = {
            name: pattern
            for name, pattern in all_patterns.items()
            if framework.upper() in pattern["compliance_relevance"]
        }

        self.logger.debug(
            f"Returning {len(framework_patterns)} patterns for framework {framework}"
        )
        return framework_patterns

    def validate_patterns(self) -> bool:
        """Validate that all patterns have required fields and proper structure.

        Returns:
            True if all patterns are valid, False otherwise
        """
        required_fields = {
            "patterns",
            "purpose_category",
            "risk_level",
            "compliance_relevance",
            "keywords",
        }
        invalid_patterns = []

        all_patterns = self.get_patterns()
        for name, pattern in all_patterns.items():
            # Check required fields
            if not all(field in pattern for field in required_fields):
                invalid_patterns.append(f"{name}: missing required fields")
                continue

            # Validate patterns are non-empty
            if not pattern["patterns"] or not isinstance(pattern["patterns"], list):
                invalid_patterns.append(f"{name}: invalid patterns field")

            # Validate risk level
            if pattern["risk_level"] not in ["high", "medium", "low"]:
                invalid_patterns.append(f"{name}: invalid risk level")

            # Validate compliance relevance is a list
            if not isinstance(pattern["compliance_relevance"], list):
                invalid_patterns.append(f"{name}: compliance_relevance must be list")

        if invalid_patterns:
            self.logger.warning(
                f"Found {len(invalid_patterns)} invalid patterns: {invalid_patterns}"
            )
            return False

        self.logger.info(
            f"All {len(all_patterns)} processing purpose patterns are valid"
        )
        return True

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the processing purposes ruleset.

        Returns:
            Dictionary containing ruleset statistics
        """
        # Use raw data directly for more efficient stats calculation
        category_counts: dict[str, int] = {}
        risk_counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        framework_counts: dict[str, int] = {}

        total_keywords = 0
        for purpose_data in PROCESSING_PURPOSES.values():
            category: str = purpose_data["category"]  # type: ignore[assignment]
            category_counts[category] = category_counts.get(category, 0) + 1

            risk_level: str = purpose_data["risk_level"]  # type: ignore[assignment]
            risk_counts[risk_level] += 1

            total_keywords += len(purpose_data["keywords"])

            # Count frameworks
            frameworks: list[str] = purpose_data["compliance_frameworks"]  # type: ignore[assignment]
            for framework in frameworks:
                framework_counts[framework] = framework_counts.get(framework, 0) + 1

        stats = {
            "total_purposes": len(PROCESSING_PURPOSES),
            "total_keywords": total_keywords,
            "categories": category_counts,
            "risk_levels": risk_counts,
            "compliance_frameworks": framework_counts,
            "average_keywords_per_purpose": total_keywords / len(PROCESSING_PURPOSES)
            if PROCESSING_PURPOSES
            else 0,
        }

        self.logger.debug(f"Generated statistics: {stats}")
        return stats
