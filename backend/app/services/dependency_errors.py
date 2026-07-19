"""Safe, structured logging for failures from external dependencies."""

from __future__ import annotations

import logging
from typing import Optional

import httpx


def classify_http_failure(status_code: Optional[int]) -> str:
    if status_code == 429:
        return "RATE_LIMIT_OR_QUOTA"
    if status_code in (401, 403):
        return "AUTHORIZATION_OR_INVALID_KEY"
    if status_code is not None and 500 <= status_code <= 599:
        return "UPSTREAM_SERVER_ERROR"
    if status_code is not None and 400 <= status_code <= 499:
        return "INVALID_REQUEST"
    return "UNKNOWN_HTTP_FAILURE"


def log_dependency_failure(
    logger: logging.Logger,
    provider: str,
    exc: Exception,
    *,
    operation: str,
    model: Optional[str] = None,
) -> None:
    """Log provider, operation and classification without logging API credentials."""
    status_code = None
    retry_after = None

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        retry_after = exc.response.headers.get("retry-after")
        category = classify_http_failure(status_code)
    elif isinstance(exc, httpx.TimeoutException):
        category = "TIMEOUT"
    elif isinstance(exc, httpx.RequestError):
        category = "NETWORK_ERROR"
    else:
        category = "PROCESSING_ERROR"

    fields = [
        "DEPENDENCY_FAILURE",
        f"provider={provider}",
        f"operation={operation}",
        f"category={category}",
        f"status_code={status_code if status_code is not None else 'n/a'}",
        f"retry_after={retry_after or 'n/a'}",
    ]
    if model:
        fields.append(f"model={model}")
    fields.append(f"error_type={type(exc).__name__}")
    logger.error(" ".join(fields), exc_info=not isinstance(exc, httpx.HTTPStatusError))
