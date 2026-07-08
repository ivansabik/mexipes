from unittest.mock import patch

import pytest
from instructor.core.exceptions import InstructorRetryException
from litellm.exceptions import ServiceUnavailableError
from pydantic import BaseModel

from mexipes.llm import _is_transient_api_error, call_llm


class _SampleModel(BaseModel):
    value: str


def test_is_transient_api_error_follows_cause_chain():
    inner = ServiceUnavailableError(message="timeout", llm_provider="gemini", model="gemini/gemini-2.5-flash")
    outer = InstructorRetryException("wrapped", n_attempts=1, total_usage=None, messages=[], last_completion=None)
    outer.__cause__ = inner
    assert _is_transient_api_error(outer) is True


def test_is_transient_api_error_rejects_validation_failures():
    exc = InstructorRetryException("bad schema", n_attempts=3, total_usage=None, messages=[], last_completion=None)
    assert _is_transient_api_error(exc) is False


def test_call_llm_retries_transient_api_errors():
    inner = ServiceUnavailableError(message="503", llm_provider="gemini", model="gemini/gemini-2.5-flash")
    wrapped = InstructorRetryException("503", n_attempts=1, total_usage=None, messages=[], last_completion=None)
    wrapped.__cause__ = inner
    expected = _SampleModel(value="ok")

    with (
        patch("mexipes.llm.client.chat.completions.create") as mock_create,
        patch("mexipes.llm.time.sleep") as mock_sleep,
    ):
        mock_create.side_effect = [wrapped, expected]
        result = call_llm(
            model="gemini/gemini-2.5-flash",
            response_model=_SampleModel,
            prompt="test",
            max_retries=3,
        )

    assert result == expected
    assert mock_create.call_count == 2
    mock_sleep.assert_called_once_with(5)


def test_call_llm_does_not_retry_non_transient_errors():
    exc = InstructorRetryException("bad schema", n_attempts=1, total_usage=None, messages=[], last_completion=None)

    with (
        patch("mexipes.llm.client.chat.completions.create", side_effect=exc) as mock_create,
        pytest.raises(InstructorRetryException),
    ):
        call_llm(
            model="gemini/gemini-2.5-flash",
            response_model=_SampleModel,
            prompt="test",
            max_retries=3,
        )

    assert mock_create.call_count == 1
