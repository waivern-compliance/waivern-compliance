"""Utility functions for Waivern Compliance Framework."""

from datetime import UTC, datetime
from typing import Any

from waivern_core.message import Message


def update_analyses_chain(
    input_message: Message, analyser_name: str
) -> list[dict[str, Any]]:
    """Extract existing analysis chain and add new entry with correct order.

    This function works with generic dictionary representations of chain entries,
    making it independent of specific data models. Applications can define
    their own typed models and convert to/from dicts as needed.

    Args:
        input_message: Input message that may contain existing analysis metadata
        analyser_name: Name of the current analyser to add to the chain

    Returns:
        Updated analysis chain as a list of dictionaries with the new analyser entry.
        Each dict should contain at minimum: {"order": int, "analyser": str}

    """
    existing_chain: list[dict[str, Any]] = []

    # Extract existing analysis chain from input message if present
    if hasattr(input_message.content, "get") and input_message.content.get(
        "analysis_metadata"
    ):
        metadata = input_message.content["analysis_metadata"]
        if "analyses_chain" in metadata:
            existing_chain = list(metadata["analyses_chain"])

    # Calculate next order number
    next_order = (
        max(entry["order"] for entry in existing_chain) + 1 if existing_chain else 1
    )

    # Create new entry and extend chain
    new_entry: dict[str, Any] = {
        "order": next_order,
        "analyser": analyser_name,
        "execution_timestamp": datetime.now(UTC),
    }
    return existing_chain + [new_entry]
