"""Data models for language extraction results."""

from pydantic import BaseModel


class ParameterModel(BaseModel):
    """A parameter of a callable."""

    name: str
    type: str | None = None
    default_value: str | None = None


class CallableModel(BaseModel):
    """A callable construct (function, method, lambda, etc.)."""

    name: str
    kind: str  # "function", "method", "arrow_function", "lambda", "closure"
    line_start: int
    line_end: int
    parameters: list[ParameterModel] = []
    return_type: str | None = None
    visibility: str | None = None  # "public", "private", "protected"
    is_static: bool = False
    is_async: bool = False
    docstring: str | None = None


class MemberModel(BaseModel):
    """A member of a type definition (property, field, enum variant)."""

    name: str
    kind: str  # "property", "field", "enum_variant"
    type: str | None = None
    visibility: str | None = None
    is_static: bool = False
    default_value: str | None = None


class TypeDefinitionModel(BaseModel):
    """A type definition (class, interface, enum, struct, trait, etc.)."""

    name: str
    kind: str  # "class", "interface", "enum", "struct", "trait", "type_alias"
    line_start: int
    line_end: int
    extends: str | None = None
    implements: list[str] = []
    members: list[MemberModel] = []
    methods: list[CallableModel] = []
    docstring: str | None = None


class LanguageExtractionResult(BaseModel):
    """Result of extracting constructs from source code."""

    callables: list[CallableModel] = []
    type_definitions: list[TypeDefinitionModel] = []
