"""Protocols for finding types.

These protocols enable invariance-free type bounds in generic code,
solving the variance problem when using generics with type parameters.

The key insight: generics parameterise, they don't create subtype chains.
`BaseFindingModel[ChildMetadata]` is NOT a subtype of `BaseFindingModel[BaseMetadata]`.
Protocols use structural typing - any class with the required shape satisfies it.
"""

from typing import Protocol


class FindingMetadata(Protocol):
    """Minimal contract for finding metadata.

    Ensures source is always present, which is essential for LLMs
    to understand the context of findings during validation.
    """

    @property
    def source(self) -> str:
        """Source file or location where the data was found."""
        ...


class Finding(Protocol):
    """Minimal contract for findings used in generic validation code.

    This protocol allows generic code (like ValidationOrchestrator) to work
    with any finding type, regardless of its generic metadata parameter.
    """

    @property
    def id(self) -> str:
        """Unique identifier for this finding."""
        ...

    @property
    def metadata(self) -> FindingMetadata:
        """Metadata with source information."""
        ...
