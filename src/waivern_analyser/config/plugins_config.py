from collections import Counter

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationInfo,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from waivern_analyser._plugins import PluginRegistry
from waivern_analyser._plugins import load_plugins as _load_plugins


class PluginsConfig(BaseModel):
    """Configuration for the plugins."""

    # TODO: src/waivern_analyser/_plugins.py contains duplicate detection logic,
    # inexistent plugin detection logic etc.
    # We should move this logic to this class.

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    select: tuple[str, ...] | None = None
    exclude: tuple[str, ...] | None = None

    @field_validator("select", "exclude", mode="after")
    def validate_unique_plugins(
        cls,
        v: tuple[str, ...] | None,
        info: ValidationInfo,
    ) -> tuple[str, ...] | None:
        if v is not None:
            counter = Counter(v)
            if repeated := sorted(
                plugin for plugin, count in counter.items() if count > 1
            ):
                raise ValueError(
                    f"The following plugins are repeated in {info.field_name!r}:"
                    f" {sorted(repeated)}."
                    " Please remove the duplicates."
                )

        return v

    @model_validator(mode="after")
    def validate_select_and_exclude_plugins(self) -> Self:
        if self.select and self.exclude:
            raise ValueError("`select` and `exclude` are mutually exclusive")
        return self

    def load_plugins(self) -> PluginRegistry:
        # The type-ignore comments are necessary because `_load_plugins`
        # does not accept both `select` and `exclude` at the same time.
        # And we are not passing both, because the `validate_select_and_exclude_plugins`
        # validator ensures that at least one of them is `None`.
        # But of course, the type-checker does not know that, so we need to
        # suppress the type-checker warnings.
        return _load_plugins(
            select=self.select,  # type: ignore
            exclude=self.exclude,  # type: ignore
        )  # type: ignore
