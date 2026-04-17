"""Tests for Processor base class default process() behaviour.

Processor.process() is a non-abstract default that raises NotImplementedError.
Subclasses implementing the synchronous path override it; subclasses
implementing the DistributedProcessor protocol inherit the default and are
invoked via prepare/finalise by the executor instead.
"""

from typing import override

import pytest

from waivern_core import InputRequirement, Schema
from waivern_core.base_processor import Processor


class _DistributedOnlyProcessor(Processor):
    """Satisfies all class-level abstracts but does not override process().

    Mirrors a real DistributedProcessor implementation that relies on the
    executor's prepare/finalise path. The synchronous process() method
    inherits the base-class default.
    """

    @classmethod
    @override
    def get_name(cls) -> str:
        return "distributed_only"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("standard_input", "1.0.0")]


class TestProcessorDefaultProcess:
    """Tests for Processor.process() default behaviour."""

    def test_subclass_without_process_override_can_be_instantiated(self) -> None:
        """A subclass satisfying only the class-level abstracts must be instantiable.

        Guards against re-adding ``@abc.abstractmethod`` to ``Processor.process()``,
        which would make Python's ABC machinery refuse instantiation.
        """
        processor = _DistributedOnlyProcessor()

        assert isinstance(processor, Processor)

    def test_default_process_raises_with_guidance(self) -> None:
        """Calling the default process() must raise with a DistributedProcessor hint.

        Pins the developer-facing error message so future renames or message
        edits have to consciously update the guidance.
        """
        processor = _DistributedOnlyProcessor()

        with pytest.raises(NotImplementedError, match="DistributedProcessor"):
            processor.process(
                inputs=[], output_schema=Schema("standard_input", "1.0.0")
            )
