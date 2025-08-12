"""Known processing purposes to search for during analysis."""

import logging
from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

logger = logging.getLogger(__name__)

# Version constant for this ruleset (private)
_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "processing_purposes"

_PROCESSING_PURPOSES: Final[dict[str, RuleData]] = {
    "Artificial Intelligence Model Training": {
        "description": "Training AI/ML models using personal data",
        "patterns": (
            "model training",
            "machine learning",
            "ai training",
            "training data",
            "ml model",
            "learning model",
            "predictive model",
            "google vertex ai",
            "aws sagemaker",
            "microsoft azure machine learning",
            "ibm watson machine learning",
            "datarobot",
            "tensorflow extended",
            "hugging face transformers",
            "hopsworks",
            "snorkel ai",
            "kubeflow",
            "feast",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        },
    },
    "Artificial Intelligence Bias Testing": {
        "description": "Testing AI/ML models for bias and fairness issues",
        "patterns": (
            "bias testing",
            "fairness testing",
            "model bias",
            "ai fairness",
            "bias detection",
            "fairness metrics",
            "ibm ai fairness 360",
            "microsoft fairlearn",
            "themis-ml",
            "shap",
            "lime",
            "uchicago aequitas",
            "google what-if tool",
            "responsibly",
            "rebias",
            "fiddler ai",
            "arthur ai",
            "truera",
            "credo ai",
            "aws sagemaker clarify",
            "parity ai",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        },
    },
    "Artificial Intelligence Model Refinement": {
        "description": "Refining and improving AI/ML models for better performance",
        "patterns": (
            "model refinement",
            "model improvement",
            "fine-tuning",
            "model optimisation",
            "performance enhancement",
            "finetunedb",
            "entry point ai",
            "openai api",
            "google ai platform vizier",
            "aws sagemaker",
            "nvidia rtx ai toolkit",
            "lmflow",
            "optuna",
            "hyperopt",
            "mlflow",
            "deepchecks",
            "granica signal",
            "superannotate",
            "kili technology",
            "cohere",
            "scale ai",
            "labelbox",
        ),
        "risk_level": "medium",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        },
    },
    "Artificial Intelligence Performance Testing": {
        "description": "Testing AI/ML model performance, accuracy, and robustness",
        "patterns": (
            "performance testing",
            "model evaluation",
            "accuracy testing",
            "robustness testing",
            "efficiency testing",
            "deepchecks",
            "aitest",
            "mlperf",
            "hpc ai500",
            "aiperf",
            "mlcommons",
            "ailuminate",
            "chatbot arena",
            "helm",
            "big-bench",
            "decoding trust benchmark",
        ),
        "risk_level": "medium",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        },
    },
    "Artificial Intelligence Security Testing": {
        "description": "Testing AI/ML models for security vulnerabilities and threats",
        "patterns": (
            "security testing",
            "penetration testing",
            "adversarial testing",
            "model security",
            "vulnerability testing",
            "ibm adversarial robustness toolbox",
            "microsoft counterfit",
            "garak",
            "privacy meter",
            "ai-exploits",
            "pentest ai",
            "hcl app scan",
            "purple llama",
            "aptori",
            "ai jack",
            "pentest gpt",
            "devaic",
            "darktrace",
            "synack",
            "shellgpt",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": [
                "GDPR",
                "EU_AI_ACT",
                "NIST_AI_RMF",
                "ISO_27001",
                "SOC_2",
            ],
        },
    },
    "Artificial Intelligence Compliance Management": {
        "description": "Managing AI/ML compliance, governance, and regulatory requirements",
        "patterns": (
            "compliance",
            "risk management",
            "governance",
            "regulatory compliance",
            "ethics",
            "accountability",
            "centraleyes",
            "compliance.ai",
            "ibm watson",
            "auditboard",
            "trustlayer",
            "robust intelligence",
            "fairnow",
            "logicgate",
            "validmind",
            "credo.ai",
            "saidot",
            "holisticai",
            "onetrust",
            "fairly.ai",
            "anch.ai",
            "fiddler ai",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "AI_AND_ML",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF"],
        },
    },
    "General Product and Service Delivery": {
        "description": "Delivering products and services to customers and users",
        "patterns": (
            "service",
            "delivery",
            "product",
            "fulfill",
            "provide",
            "technical operations",
            "online services",
            "aws",
            "google cloud",
            "microsoft azure",
            "apache web server",
            "shopify",
            "webflow",
            "wordpress",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
        },
    },
    "Customer Service and Support": {
        "description": "Providing customer service, support, and assistance",
        "patterns": (
            "support",
            "customer",
            "help",
            "chat",
            "email",
            "inquiry",
            "ticket",
            "assistance",
            "zendesk",
            "freshdesk",
            "intercom",
            "salesforce servicecloud",
            "helpscout",
            "liveagent",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
        },
    },
    "Customization of Products and Services": {
        "description": "Customising products and services based on user preferences",
        "patterns": (
            "customisation",
            "preferences",
            "settings",
            "user choice",
            "theme",
            "ui",
            "personalization",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
        },
    },
    "User Identity and Login Management": {
        "description": "Managing user identity, authentication, and login processes",
        "patterns": (
            "authentication",
            "login",
            "account",
            "profile",
            "credentials",
            "password",
            "user id",
            "ssn",
            "google identity",
            "facebook login",
            "apple sign-in",
            "okta",
            "microsoft active directory",
            "forgerock",
        ),
        "risk_level": "medium",
        "metadata": {
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
        },
    },
    "Payment, Billing, and Invoicing": {
        "description": "Processing payments, billing, and financial transactions",
        "patterns": (
            "payment",
            "transaction",
            "billing",
            "purchase",
            "subscription",
            "order",
            "financial",
            "stripe",
            "paypal",
            "adyen",
            "square",
            "braintree",
            "worldpay",
            "klarna",
            "recurly",
        ),
        "risk_level": "medium",
        "metadata": {
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR", "PCI_DSS", "SOX"],
        },
    },
    "Behavioral Data Analysis for Product Improvement": {
        "description": "Analysing user behaviour and data to improve products and services",
        "patterns": (
            "analytics",
            "tracking",
            "monitor",
            "measure",
            "behavior",
            "survey",
            "product improvement",
            "adobe analytics",
            "snowflake",
            "hotjar",
            "piwik pro",
            "matomo",
            "heap",
            "fullstory",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "ANALYTICS",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
        },
    },
    "Dynamic Personalization of Products and Services": {
        "description": "Dynamically personalising products and services based on user data",
        "patterns": (
            "personalization",
            "recommendation",
            "history",
            "mirror audience",
            "preferences",
            "targeting",
            "braze",
            "twilio",
            "optimizely",
            "dynamic yield",
            "adobe target",
            "coveo relevance cloud",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "MARKETING_AND_ADVERTISING",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
        },
    },
    "Consumer Marketing Within Owned Products": {
        "description": "Marketing and promotional activities within company-owned products and platforms",
        "patterns": (
            "marketing",
            "promotion",
            "advertising",
            "notification",
            "email campaign",
            "loyalty program",
            "braze",
            "sap emarsys",
            "salesforce marketing cloud",
            "klaviyo",
            "omnisend",
            "mailchimp",
            "sendgrid",
            "mailjet",
            "onesignal",
        ),
        "risk_level": "medium",
        "metadata": {
            "purpose_category": "MARKETING_AND_ADVERTISING",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
        },
    },
    "Targeted Marketing via Third-Party Platforms": {
        "description": "Targeted marketing and advertising through third-party platforms and networks",
        "patterns": (
            "advertising",
            "targeting",
            "third-party marketing",
            "tracking",
            "custom audience",
            "retargeting",
            "meta",
            "snap",
            "google ads 360",
            "tiktok",
            "twitter",
            "linkedin ads",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "MARKETING_AND_ADVERTISING",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
        },
    },
    "Third-Party Marketing via Owned Products": {
        "description": "Third-party marketing and advertising activities conducted through company-owned products",
        "patterns": (
            "partner marketing",
            "third-party advertising",
            "sponsored content",
            "custom audience",
            "meta",
            "snap",
            "google ads 360",
            "tiktok",
            "third-party advertisers",
        ),
        "risk_level": "high",
        "metadata": {
            "purpose_category": "MARKETING_AND_ADVERTISING",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
        },
    },
    "Security, Fraud Prevention, and Abuse Detection": {
        "description": "Protecting against security threats, fraud, and platform abuse",
        "patterns": (
            "security",
            "fraud",
            "protection",
            "abuse",
            "compliance",
            "policy enforcement",
            "verification",
            "scamalytics",
            "seon",
            "netcraft",
            "threatmark",
            "complyadvantage",
            "veriff",
            "feedzai",
        ),
        "risk_level": "low",
        "metadata": {
            "purpose_category": "SECURITY",
            "compliance_relevance": ["GDPR", "ISO_27001", "SOC_2"],
        },
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

    def __init__(self) -> None:
        """Initialise the processing purposes ruleset."""
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
        """Get the processing purposes rules.

        Returns:
            Immutable tuple of Rule objects containing all processing purpose patterns with metadata
        """
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _PROCESSING_PURPOSES.items():
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
            logger.debug(f"Generated {len(self.rules)} processing purpose rules")

        return self.rules
