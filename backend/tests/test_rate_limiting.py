"""Tests for rate limiting configuration."""
import pytest


def test_rate_limit_key_extracts_user_from_token():
    """Rate limit key function should extract user_id from Bearer token."""
    # This tests the key function logic, not the actual rate limiting
    # Rate limiting integration tests require a running server
    from unittest.mock import MagicMock, patch

    mock_request = MagicMock()
    mock_request.headers = {"authorization": "Bearer valid_token"}
    mock_request.client.host = "127.0.0.1"

    with patch("server.firebase_auth") as mock_fb:
        mock_fb.verify_id_token.return_value = {"uid": "user123"}
        from server import get_rate_limit_key
        key = get_rate_limit_key(mock_request)
        assert key == "user:user123"


def test_rate_limit_key_falls_back_to_ip():
    """Rate limit key should fall back to IP when no auth token."""
    from unittest.mock import MagicMock, patch

    mock_request = MagicMock()
    mock_request.headers = {}
    mock_request.client.host = "192.168.1.1"

    from server import get_rate_limit_key
    key = get_rate_limit_key(mock_request)
    assert key == "ip:192.168.1.1"


def test_rate_limit_key_falls_back_on_invalid_token():
    """Rate limit key should fall back to IP on invalid token."""
    from unittest.mock import MagicMock, patch

    mock_request = MagicMock()
    mock_request.headers = {"authorization": "Bearer invalid_token"}
    mock_request.client.host = "10.0.0.1"

    with patch("server.firebase_auth") as mock_fb:
        mock_fb.verify_id_token.side_effect = Exception("Invalid token")
        from server import get_rate_limit_key
        key = get_rate_limit_key(mock_request)
        assert key == "ip:10.0.0.1"
