import abc
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class Source(BaseModel, abc.ABC):
    """A source of information to be consumed by connectors."""


class ProjectRootSource(Source):
    type: Literal["project_root"]
    path: Path
