from pathlib import Path
from typing import Annotated, Literal

from annotated_types import MinLen
from pydantic import BaseModel, ConfigDict


class Source(BaseModel):
    """A source of information to be consumed by connectors."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    type: str


class PathsSource(Source):
    """A source of files or directories.

    Each path in the `paths` field can be a file or a directory.
    Consumers of this source should decide whether to recursively search for files
    in the directories or not.

    Example:

    ```yaml
    type: paths
    paths:
    - path/to/file1.txt
    - path/to/file2.txt
    - path/to/directory/
    ```
    """

    type: Literal["paths"]
    paths: Annotated[
        tuple[Path, ...],
        MinLen(1),
    ]
