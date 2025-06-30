from dataclasses import dataclass
from typing import Final, Literal

from wct.analysers.base import Analyser

DEFAULT_PERSONAL_DATA_PATTERNS: Final = {
    "basic_profile": {
        "patterns": [
            "first_name",
            "last_name",
            "middle_name",
            "address",
            "telephone",
            "email",
            "title",
            "account_id",
        ],
        "risk_level": "normal",
        "special_category": "N",
    },
    "account_data": {
        "patterns": ["transaction", "subscription", "purchase", "cancellation"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "payment_data": {
        "patterns": ["payment_method", "invoice", "receipt"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "financial_data": {
        "patterns": ["credit_rating", "payment_history"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "behavioral_event_data": {
        "patterns": [
            "page_view",
            "click",
            "scroll",
            "form_completion",
            "timestamp",
            "app_usage",
        ],
        "risk_level": "normal",
        "special_category": "N",
    },
    "technical_device_and_network_data": {
        "patterns": [
            "device_id",
            "ip_address",
            "cookie",
            "language",
            "screen",
            "network",
        ],
        "risk_level": "normal",
        "special_category": "N",
    },
    "inferred_profile_data": {
        "patterns": [
            "predicted",
            "inferred",
            "calculated",
            "profiling",
            "machine_learning",
        ],
        "risk_level": "normal",
        "special_category": "N",
    },
    "User_enriched_profile_data": {
        "patterns": ["interests", "preferences", "declared", "user_provided"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "location_data": {
        "patterns": ["country", "region", "city", "suburb"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "user_generated_content": {
        "patterns": ["comment", "review", "feedback", "message"],
        "risk_level": "normal",
        "special_category": "N",
    },
    "accurate_location": {
        "patterns": [
            "precise_location",
            "exact_location",
            "gps",
            "coordinates",
            "latitude",
            "longitude",
        ],
        "risk_level": "high",
        "special_category": "Y",
    },
    "health_data": {
        "patterns": ["health", "medical", "illness", "condition", "diagnosis"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "political_data": {
        "patterns": ["political", "trade_union", "affiliation"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "racial_ethnic_data": {
        "patterns": ["race", "ethnic", "origin", "nationality"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "religious_philosophical_data": {
        "patterns": ["religion", "belief", "philosophy", "faith"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "genetic_data": {
        "patterns": ["genetic", "dna", "genome", "sequence"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "biometric_data": {
        "patterns": ["biometric", "fingerprint", "iris", "facial_recognition"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "sexual_orientation_data": {
        "patterns": ["sexual", "orientation", "sex_life", "gender_identity"],
        "risk_level": "high",
        "special_category": "Y",
    },
}


@dataclass(frozen=True, slots=True)
class PersonalDataPattern:
    """A pattern for a personal data type."""

    name: str
    patterns: list[str]
    risk_level: Literal["low", "medium", "high"]
    is_special_category: bool


@dataclass(frozen=True, slots=True)
class PersonalDataFinding:
    """A finding of a personal data."""

    type: str
    risk_level: str
    special_category: str
    matched_pattern: str
    source: str | None


class PersonalDataAnalyser(Analyser):
    """An analyser for personal data."""

    def analyse(self, data: dict[str, Any]) -> list[PersonalDataFinding]:
        pass
