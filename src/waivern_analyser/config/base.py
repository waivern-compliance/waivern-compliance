from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    """Base class for all config entries."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )
