"""Rate limit detection utilities for OpenClaw Gateway."""

import re
from typing import TypedDict


class RateLimitInfo(TypedDict):
    is_rate_limited: bool
    retry_seconds: int
    message: str


RATE_LIMIT_PATTERNS = [
    r"rate_limit_error",
    r"rate_limit",
    r"429",
    r"too_many_requests",
    r"too many requests",
    r"exceeded.*rate limit",
    r"retry\s*after",
]

DEFAULT_RETRY_SECONDS = 60


def is_rate_limit_error(error_message: str) -> bool:
    """Check if an error message indicates a rate limit violation."""
    if not error_message:
        return False
    error_lower = error_message.lower()
    return any(re.search(p, error_lower) for p in RATE_LIMIT_PATTERNS)


def extract_retry_seconds(error_message: str) -> int:
    """Extract retry-after seconds from an error message."""
    if not error_message:
        return DEFAULT_RETRY_SECONDS

    patterns = [
        r"retry\s*after\s*(\d+)\s*seconds?",
        r"wait\s*(\d+)\s*seconds?",
        r"try\s*again\s*in\s*(\d+)",
        r"(\d+)\s*second",
    ]

    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return DEFAULT_RETRY_SECONDS


def get_rate_limit_info(error_message: str) -> RateLimitInfo:
    """Get structured rate limit info from an error message."""
    if not is_rate_limit_error(error_message):
        return RateLimitInfo(
            is_rate_limited=False,
            retry_seconds=0,
            message="",
        )

    return RateLimitInfo(
        is_rate_limited=True,
        retry_seconds=extract_retry_seconds(error_message),
        message=error_message,
    )
