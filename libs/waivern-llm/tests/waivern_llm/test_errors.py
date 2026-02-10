"""Tests for LLM service error types."""

from waivern_llm.errors import LLMServiceError, PendingBatchError


class TestPendingBatchError:
    """Tests for PendingBatchError exception."""

    def test_stores_run_id_and_batch_ids(self) -> None:
        error = PendingBatchError(run_id="run-123", batch_ids=["batch-a", "batch-b"])

        assert error.run_id == "run-123"
        assert error.batch_ids == ["batch-a", "batch-b"]

    def test_produces_descriptive_message(self) -> None:
        error = PendingBatchError(
            run_id="run-456", batch_ids=["batch-x", "batch-y", "batch-z"]
        )

        message = str(error)
        assert "run-456" in message
        assert "3" in message

    def test_is_llm_service_error_subclass(self) -> None:
        error = PendingBatchError(run_id="run-789", batch_ids=["batch-1"])

        assert isinstance(error, LLMServiceError)
