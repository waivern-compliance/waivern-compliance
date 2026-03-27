"""Dispatch abstractions for the Distributed Processor Protocol.

This module defines the generic dispatch types that enable processors to declare
external I/O needs as typed request objects. The DAG executor interprets these
requests via registered dispatchers, enabling cross-processor coordination and
batch consolidation.

Core types:
    - ``DispatchRequest`` / ``DispatchResult``: Base types for all dispatchable
      request/result pairs. Service-specific subtypes (e.g., ``LLMRequest``) live
      in their respective service packages.
    - ``PrepareResult``: Returned by ``DistributedProcessor.prepare()`` — carries
      processor-specific intermediate state and a dict of dispatch requests.
    - ``RequestDispatcher``: Protocol for dispatching grouped requests to a service.
    - ``DistributedProcessor``: Protocol for processors that separate domain logic
      (prepare/finalise) from external I/O (dispatch).

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from waivern_core.message import Message
from waivern_core.schemas import Schema


class DispatchRequest(BaseModel):
    """Base type for all dispatchable requests.

    Every request carries a ``request_id`` set by the caller. The
    dispatcher passes it through to the corresponding ``DispatchResult``
    so the caller can match results back to requests.

    Service-specific request types extend this with their own fields.
    For example, ``LLMRequest`` in ``waivern-llm`` adds groups, prompt
    builder, response model, etc.
    """

    request_id: str
    """Caller-defined identifier for matching results back to requests."""


class DispatchResult(BaseModel):
    """Base type for all dispatch results.

    Every result carries the ``request_id`` of the originating request
    so the caller can match results back without relying on ordering.

    Service-specific result types extend this with their own fields.
    For example, ``LLMDispatchResult`` in ``waivern-llm`` adds responses
    and skipped findings.
    """

    request_id: str
    """Identifier copied from the originating ``DispatchRequest``."""


class PrepareResult[S: BaseModel](BaseModel):
    """Result of ``DistributedProcessor.prepare()``.

    Carries the processor's intermediate state and a list of dispatch
    requests. The executor inspects ``requests`` to determine the
    dispatch path:

    - Empty ``requests``: no dispatch needed — executor calls
      ``finalise()`` immediately with an empty results list.
    - Non-empty ``requests``: executor routes each request to the
      matching ``RequestDispatcher``, then calls ``finalise()`` with
      the results.

    Attributes:
        state: Processor-specific intermediate state, opaque to the
            executor.
        requests: Dispatch requests. Each request carries a
            ``request_id`` set by the processor to label its intent
            (e.g., ``"assessment"``, ``"classification"``). The executor
            may prefix these with the artifact ID to ensure global
            uniqueness before dispatching.

    """

    state: S
    requests: list[DispatchRequest]


class RequestDispatcher[R: DispatchRequest, V: DispatchResult](Protocol):
    """Protocol for dispatching grouped requests to a service.

    Dispatchers consolidate execution across multiple requests of the
    same type. For example, ``LLMDispatcher`` collects cache misses
    from all requests and executes them in a single batch submission.

    Each request carries a ``request_id``. The dispatcher copies it to
    the corresponding ``DispatchResult`` so the caller can match results
    back to requests. The dispatcher does not interpret the IDs.

    """

    @property
    def request_type(self) -> type[R]:
        """The concrete ``DispatchRequest`` subclass this dispatcher handles."""
        ...

    async def dispatch(self, requests: Sequence[R]) -> Sequence[V]:
        """Dispatch a batch of requests and return results.

        Args:
            requests: Requests to dispatch. Each carries a
                ``request_id`` for result matching.

        Returns:
            Results, each carrying the ``request_id`` of the
            originating request.

        """
        ...


@runtime_checkable
class DistributedProcessor[S: BaseModel](Protocol):
    """Protocol for processors with executor-coordinated external I/O.

    A ``DistributedProcessor`` exposes two phases:

    1. ``prepare()`` — synchronous, no I/O. Analyses inputs, builds
       intermediate state, and declares what external requests are needed.
    2. ``finalise()`` — synchronous, no I/O. Receives dispatch results
       and produces the final output ``Message``.

    The executor drives the lifecycle: prepare → dispatch → finalise.

    This is a **separate protocol** from ``Processor``. A concrete class
    can implement both. The executor prefers the ``DistributedProcessor``
    path when available; ``Processor.process()`` serves as a standalone
    fallback.

    Multi-round pattern:
        ``finalise()`` may return a new ``PrepareResult`` instead of a
        ``Message``, signalling that another dispatch round is needed.
        The executor runs another dispatch → finalise cycle for that
        processor. Most processors complete in one round.

    """

    def prepare(self, inputs: list[Message], output_schema: Schema) -> PrepareResult[S]:
        """Analyse inputs and declare external I/O needs.

        This method must be synchronous with no internal I/O. All data
        needed must arrive via ``inputs``. If external data is required,
        it should be a separate upstream connector or processor.

        Args:
            inputs: Input messages from upstream artifacts.
            output_schema: The schema for the output message.

        Returns:
            A ``PrepareResult`` carrying intermediate state and dispatch
            requests (empty list if no dispatch is needed).

        """
        ...

    def finalise(
        self,
        state: S,
        results: Sequence[DispatchResult],
        output_schema: Schema,
    ) -> Message | PrepareResult[S]:
        """Produce output from intermediate state and dispatch results.

        This method must be synchronous with no internal I/O. It receives
        the state from ``prepare()`` and the results from dispatch (empty
        sequence if no dispatch occurred).

        Args:
            state: The intermediate state from ``prepare()``.
            results: Dispatch results, each carrying a ``request_id``
                matching the originating request. Empty sequence if no
                dispatch occurred.
            output_schema: The schema for the output message.

        Returns:
            A ``Message`` if processing is complete, or a new
            ``PrepareResult`` if another dispatch round is needed.

        """
        ...
