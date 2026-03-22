"""
Rate Limit Core Module Tests.
"""

import pytest
from app.core.rate_limit import (
    is_rate_limit_error,
    extract_retry_seconds,
    get_rate_limit_info,
)


class TestIsRateLimitError:
    """Test is_rate_limit_error function."""

    def test_is_rate_limit_error_rate_limit_in_message(self):
        """Test rate limit error detection with 'rate_limit' in message."""
        # The pattern "rate_limit" should match
        assert is_rate_limit_error("rate_limit_error occurred") is True
        # Note: exact string match depends on pattern implementation
        assert is_rate_limit_error("429 Too Many Requests") is True

    def test_is_rate_limit_error_429(self):
        """Test rate limit error detection with 429 status."""
        assert is_rate_limit_error("429 Too Many Requests") is True
        assert is_rate_limit_error("Error code 429") is True

    def test_is_rate_limit_error_empty_message(self):
        """Test empty message returns False."""
        assert is_rate_limit_error("") is False

    def test_is_rate_limit_error_not_rate_limited(self):
        """Test non-rate-limit errors return False."""
        assert is_rate_limit_error("Not found") is False
        assert is_rate_limit_error("Server error") is False


class TestExtractRetrySeconds:
    """Test extract_retry_seconds function."""

    def test_extract_retry_seconds_explicit(self):
        """Test extracting retry seconds when explicitly stated."""
        assert extract_retry_seconds("retry after 60 seconds") == 60
        assert extract_retry_seconds("Please retry after 30 seconds") == 30

    def test_extract_retry_seconds_wait(self):
        """Test extracting retry seconds with 'wait' keyword."""
        assert extract_retry_seconds("wait 45 seconds") == 45

    def test_extract_retry_seconds_try_again(self):
        """Test extracting retry seconds with 'try again' keyword."""
        assert extract_retry_seconds("try again in 15 seconds") == 15

    def test_extract_retry_seconds_default(self):
        """Test extracting retry seconds when no pattern matches returns default 60."""
        assert extract_retry_seconds("No retry info") == 60


class TestGetRateLimitInfo:
    """Test get_rate_limit_info function."""

    def test_get_rate_limit_info_rate_limited(self):
        """Test rate limit info when rate limited."""
        result = get_rate_limit_info("Rate limit exceeded: retry after 30 seconds")
        assert result["is_rate_limited"] is True
        assert result["retry_seconds"] == 30
        assert "Rate limit" in result["message"]

    def test_get_rate_limit_info_not_limited(self):
        """Test rate limit info when not rate limited."""
        result = get_rate_limit_info("Success")
        assert result["is_rate_limited"] is False
        assert result["retry_seconds"] == 0
        assert result["message"] == ""
