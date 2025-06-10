from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Source(BaseModel):
    """A source of information to be consumed by connectors."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    type: str


class ProjectDirectorySource(Source):
    type: Literal["project_directory"]
    path: Path


class Sources(BaseModel):
    sources: list[Source]
