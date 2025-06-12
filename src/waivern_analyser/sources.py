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


class FilesSource(Source):
    """A source of files.

    The `files` field can be a single file or a list of files.
    Directories are recursively searched for files, so

    ```yaml
    type: files
    files:
    - path/to/file1.txt
    - path/to/file2.txt
    - path/to/directory/
    ```

    will search for `file1.txt`, `file2.txt`, and all files in the `directory` directory.
    """

    type: Literal["files"]
    files: list[Path] | Path


class Sources(BaseModel):
    sources: list[Source]
