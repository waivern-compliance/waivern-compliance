"""Tests for language extraction data models."""

from waivern_source_code_analyser.languages.models import (
    CallableModel,
    LanguageExtractionResult,
    MemberModel,
    ParameterModel,
    TypeDefinitionModel,
)


class TestParameterModel:
    """Tests for ParameterModel."""

    def test_parameter_model_basic_creation(self) -> None:
        """Test creating a ParameterModel with name only."""
        param = ParameterModel(name="user_id")

        assert param.name == "user_id"
        assert param.type is None
        assert param.default_value is None

    def test_parameter_model_with_type_and_default(self) -> None:
        """Test creating a ParameterModel with all optional fields."""
        param = ParameterModel(
            name="count",
            type="int",
            default_value="0",
        )

        assert param.name == "count"
        assert param.type == "int"
        assert param.default_value == "0"


class TestCallableModel:
    """Tests for CallableModel."""

    def test_callable_model_minimal(self) -> None:
        """Test creating a CallableModel with required fields only."""
        callable_model = CallableModel(
            name="processData",
            kind="function",
            line_start=10,
            line_end=20,
        )

        assert callable_model.name == "processData"
        assert callable_model.kind == "function"
        assert callable_model.line_start == 10
        assert callable_model.line_end == 20

    def test_callable_model_full(self) -> None:
        """Test creating a CallableModel with all fields including nested parameters."""
        params = [
            ParameterModel(name="user_id", type="int"),
            ParameterModel(name="options", type="array", default_value="[]"),
        ]
        callable_model = CallableModel(
            name="getUserData",
            kind="method",
            line_start=15,
            line_end=30,
            parameters=params,
            return_type="UserData",
            visibility="public",
            is_static=True,
            is_async=True,
            docstring="Retrieves user data from the database.",
        )

        assert callable_model.name == "getUserData"
        assert callable_model.kind == "method"
        assert callable_model.line_start == 15
        assert callable_model.line_end == 30
        assert len(callable_model.parameters) == 2
        assert callable_model.parameters[0].name == "user_id"
        assert callable_model.parameters[1].default_value == "[]"
        assert callable_model.return_type == "UserData"
        assert callable_model.visibility == "public"
        assert callable_model.is_static is True
        assert callable_model.is_async is True
        assert callable_model.docstring == "Retrieves user data from the database."

    def test_callable_model_default_values(self) -> None:
        """Test that CallableModel has correct default values."""
        callable_model = CallableModel(
            name="simple",
            kind="function",
            line_start=1,
            line_end=5,
        )

        assert callable_model.parameters == []
        assert callable_model.return_type is None
        assert callable_model.visibility is None
        assert callable_model.is_static is False
        assert callable_model.is_async is False
        assert callable_model.docstring is None


class TestMemberModel:
    """Tests for MemberModel."""

    def test_member_model_basic(self) -> None:
        """Test creating a MemberModel with required fields."""
        member = MemberModel(
            name="userId",
            kind="property",
        )

        assert member.name == "userId"
        assert member.kind == "property"
        assert member.type is None
        assert member.visibility is None
        assert member.is_static is False
        assert member.default_value is None


class TestTypeDefinitionModel:
    """Tests for TypeDefinitionModel."""

    def test_type_definition_minimal(self) -> None:
        """Test creating a TypeDefinitionModel with required fields only."""
        type_def = TypeDefinitionModel(
            name="UserProcessor",
            kind="class",
            line_start=5,
            line_end=50,
        )

        assert type_def.name == "UserProcessor"
        assert type_def.kind == "class"
        assert type_def.line_start == 5
        assert type_def.line_end == 50
        assert type_def.extends is None
        assert type_def.implements == []
        assert type_def.members == []
        assert type_def.methods == []
        assert type_def.docstring is None

    def test_type_definition_with_members_and_methods(self) -> None:
        """Test creating a TypeDefinitionModel with nested members and methods."""
        members = [
            MemberModel(name="id", kind="property", type="int", visibility="private"),
            MemberModel(
                name="name", kind="property", type="string", visibility="public"
            ),
        ]
        methods = [
            CallableModel(
                name="getId",
                kind="method",
                line_start=10,
                line_end=12,
                return_type="int",
                visibility="public",
            ),
        ]
        type_def = TypeDefinitionModel(
            name="User",
            kind="class",
            line_start=1,
            line_end=20,
            extends="BaseEntity",
            implements=["Serializable", "Comparable"],
            members=members,
            methods=methods,
            docstring="Represents a user entity.",
        )

        assert type_def.name == "User"
        assert type_def.kind == "class"
        assert type_def.extends == "BaseEntity"
        assert type_def.implements == ["Serializable", "Comparable"]
        assert len(type_def.members) == 2
        assert type_def.members[0].name == "id"
        assert len(type_def.methods) == 1
        assert type_def.methods[0].name == "getId"
        assert type_def.docstring == "Represents a user entity."


class TestLanguageExtractionResult:
    """Tests for LanguageExtractionResult."""

    def test_language_extraction_result_empty(self) -> None:
        """Test creating an empty LanguageExtractionResult with default lists."""
        result = LanguageExtractionResult()

        assert result.callables == []
        assert result.type_definitions == []

    def test_language_extraction_result_with_data(self) -> None:
        """Test creating a LanguageExtractionResult with callables and type definitions."""
        callables = [
            CallableModel(name="main", kind="function", line_start=1, line_end=10),
        ]
        type_defs = [
            TypeDefinitionModel(
                name="Config", kind="class", line_start=15, line_end=30
            ),
        ]
        result = LanguageExtractionResult(
            callables=callables,
            type_definitions=type_defs,
        )

        assert len(result.callables) == 1
        assert result.callables[0].name == "main"
        assert len(result.type_definitions) == 1
        assert result.type_definitions[0].name == "Config"
