import base64
import importlib.resources
import logging
import time
from pathlib import Path

import instructor
from instructor.core.exceptions import InstructorRetryException
from litellm import completion
from litellm.exceptions import APIConnectionError, RateLimitError, ServiceUnavailableError, Timeout
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_TRANSIENT_API_ERRORS = (ServiceUnavailableError, RateLimitError, Timeout, APIConnectionError)
_DEFAULT_REQUEST_TIMEOUT = 120


def _is_transient_api_error(exc: BaseException) -> bool:
    """Return True when exc (or its cause chain) is a retryable provider error."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, _TRANSIENT_API_ERRORS):
            return True
        current = current.__cause__ or current.__context__
    return False


# Initialize the Instructor-wrapped LiteLLM client
# In newer instructor versions, Mode.JSON is used for standard JSON schemas
client = instructor.from_litellm(completion, mode=instructor.Mode.JSON)


def load_prompt(prompt_name: str) -> str:
    """Loads prompt template from the packaged prompts directory."""
    ref = importlib.resources.files("mexipes.prompts") / prompt_name
    return ref.read_text(encoding="utf-8")


def call_llm(
    model: str,
    response_model: type[BaseModel],
    prompt: str,
    context: str = "",
    pdf_bytes: bytes | None = None,
    image_path: Path | None = None,
    temperature: float = 0.1,
    max_retries: int = 3,
) -> BaseModel:
    """Wrapper that calls LiteLLM using Instructor for structured output.

    Handles retries and schema validation automatically.
    """
    messages = []
    if context:
        messages.append({"role": "system", "content": context})

    # Prepare user content
    if pdf_bytes:
        if len(pdf_bytes) > 10 * 1024 * 1024:
            logger.info(
                f"PDF bytes exceed 10MB ({len(pdf_bytes) / (1024 * 1024):.1f} MB). "
                f"Converting pages to JPEGs to prevent API payload errors."
            )
            import fitz

            user_content = [{"type": "text", "text": prompt}]
            with fitz.open("pdf", pdf_bytes) as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("jpeg")
                    b64_str = base64.b64encode(img_bytes).decode("utf-8")
                    user_content.append(
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_str}"}}
                    )
        else:
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "file", "file": {"file_data": f"data:application/pdf;base64,{base64_pdf}"}},
            ]
        messages.append({"role": "user", "content": user_content})
    elif image_path:
        with open(image_path, "rb") as img_f:
            base64_image = base64.b64encode(img_f.read()).decode("utf-8")
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
        ]
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": prompt})

    logger.debug(
        f"Calling LLM {model} with prompt length {len(prompt)}, "
        f"has_pdf={pdf_bytes is not None}, has_image={image_path is not None}"
    )

    # Disable Gemini "thinking" mode for structured output to prevent
    # instructor from hitting 'list index out of range' on thinking-only responses.
    # Also pass drop_params=True so non-Gemini providers ignore unknown params.
    create_kwargs = {
        "model": model,
        "response_model": response_model,
        "messages": messages,
        "temperature": temperature,
        "max_retries": max_retries,
        "thinking": {"type": "disabled"},
        "drop_params": True,
        "timeout": _DEFAULT_REQUEST_TIMEOUT,
    }

    last_error: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**create_kwargs)
        except InstructorRetryException as exc:
            last_error = exc
            if attempt >= max_retries - 1 or not _is_transient_api_error(exc):
                raise
        except _TRANSIENT_API_ERRORS as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                raise

        wait_seconds = min(60, 5 * (2**attempt))
        logger.warning(
            "Transient LLM API error on attempt %d/%d (%s). Retrying in %ds...",
            attempt + 1,
            max_retries,
            last_error,
            wait_seconds,
        )
        time.sleep(wait_seconds)

    assert last_error is not None
    raise last_error
