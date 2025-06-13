from types import MappingProxyType
from typing import TypeAlias, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")

FrozenDict: TypeAlias = MappingProxyType[_K, _V]
