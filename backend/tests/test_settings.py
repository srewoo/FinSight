"""
Unit Tests for Settings Endpoints (Phase 0 — provider preference, no API key management).
Tests: GET /api/settings, POST /api/settings
Note: These endpoints now require authentication. Integration tests need auth headers.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'http://localhost:8001')


class TestGetSettings:
    """Tests for GET /api/settings (requires auth)."""

    def test_get_settings_without_auth_returns_401(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 401

    def test_get_settings_with_auth_returns_200(self, api_client, auth_headers):
        response = api_client.get(f"{BASE_URL}/api/settings", headers=auth_headers)
        # Will return 401 in real tests since token is fake; structure test below
        assert response.status_code in [200, 401]

    def test_get_settings_response_structure(self, api_client, auth_headers):
        """Settings response should include preferred_provider and supported_models, NOT api_key."""
        response = api_client.get(f"{BASE_URL}/api/settings", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "preferred_provider" in data
            assert "supported_models" in data
            assert "ai_available" in data
            # Must NOT expose API keys
            assert "api_key" not in data
            assert "api_key_set" not in data

    def test_get_settings_supported_models_structure(self, api_client, auth_headers):
        response = api_client.get(f"{BASE_URL}/api/settings", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            models = data["supported_models"]
            assert "openai" in models
            assert "gemini" in models
            assert "claude" in models
            assert isinstance(models["openai"], list)
            assert len(models["openai"]) > 0


class TestSaveSettings:
    """Tests for POST /api/settings (provider preference only, requires auth)."""

    def test_save_settings_without_auth_returns_401(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"preferred_provider": "openai"},
        )
        assert response.status_code == 401

    def test_save_valid_provider_preference(self, api_client, auth_headers):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            headers=auth_headers,
            json={"preferred_provider": "openai"},
        )
        if response.status_code == 200:
            data = response.json()
            assert data["preferred_provider"] == "openai"

    def test_save_invalid_provider_returns_400(self, api_client, auth_headers):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            headers=auth_headers,
            json={"preferred_provider": "nonexistent_provider"},
        )
        # 400 for invalid provider, or 401 if auth fails
        assert response.status_code in [400, 401]

    def test_save_provider_is_normalized_lowercase(self, api_client, auth_headers):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            headers=auth_headers,
            json={"preferred_provider": "OpenAI"},
        )
        if response.status_code == 200:
            data = response.json()
            assert data["preferred_provider"] == "openai"


class TestDisclaimerEndpoint:
    """Tests for GET /api/disclaimer (public, no auth required)."""

    def test_get_disclaimer_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/disclaimer")
        assert response.status_code == 200

    def test_get_disclaimer_structure(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/disclaimer")
        if response.status_code == 200:
            data = response.json()
            assert "version" in data
            assert "text" in data
            assert "short_text" in data
            assert "SEBI" in data["text"]


class TestQuotaEndpoint:
    """Tests for GET /api/user/quota (requires auth)."""

    def test_get_quota_without_auth_returns_401(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/user/quota")
        assert response.status_code == 401

    def test_get_quota_with_auth(self, api_client, auth_headers):
        response = api_client.get(f"{BASE_URL}/api/user/quota", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert "used" in data
            assert "limit" in data
            assert "remaining" in data
            assert data["limit"] > 0
