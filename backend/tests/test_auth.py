"""Tests for Firebase authentication middleware."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Module under test
from auth import get_current_user, get_optional_user, AuthenticatedUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_credentials(token: str = "valid_token") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


DECODED_TOKEN = {
    "uid": "firebase_uid_123",
    "email": "user@example.com",
    "name": "Test User",
    "picture": "https://example.com/photo.jpg",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_auth_header_returns_401():
    """get_current_user must raise 401 when no credentials are provided."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


@pytest.mark.asyncio
@patch("auth.firebase_auth")
async def test_invalid_token_returns_401(mock_fb_auth):
    """get_current_user must raise 401 for an invalid token."""
    mock_fb_auth.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
    mock_fb_auth.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})
    mock_fb_auth.RevokedIdTokenError = type("RevokedIdTokenError", (Exception,), {})
    mock_fb_auth.verify_id_token.side_effect = mock_fb_auth.InvalidIdTokenError("bad")

    creds = _make_credentials("bad_token")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds)
    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


@pytest.mark.asyncio
@patch("auth.firebase_auth")
async def test_valid_token_extracts_user(mock_fb_auth):
    """get_current_user must return an AuthenticatedUser for a valid token."""
    mock_fb_auth.verify_id_token.return_value = DECODED_TOKEN

    creds = _make_credentials("valid_token")
    user = await get_current_user(credentials=creds)

    assert isinstance(user, AuthenticatedUser)
    assert user.uid == "firebase_uid_123"
    assert user.email == "user@example.com"
    assert user.name == "Test User"
    assert user.photo_url == "https://example.com/photo.jpg"
    mock_fb_auth.verify_id_token.assert_called_once_with("valid_token")


@pytest.mark.asyncio
async def test_optional_auth_returns_none_without_header():
    """get_optional_user must return None when no credentials are provided."""
    result = await get_optional_user(credentials=None)
    assert result is None
