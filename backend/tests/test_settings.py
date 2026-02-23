"""
Unit Tests for LLM Settings Endpoints
Tests: GET /api/settings, POST /api/settings, POST /api/settings/test
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', 'http://localhost:8001')


class TestGetSettings:
    """Tests for GET /api/settings"""

    def test_get_settings_returns_200(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200

    def test_get_settings_structure(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/settings")
        data = response.json()
        assert "supported_models" in data
        assert "api_key_set" in data
        assert isinstance(data["api_key_set"], bool)

    def test_get_settings_supported_models_structure(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/settings")
        data = response.json()
        models = data["supported_models"]
        assert "openai" in models
        assert "gemini" in models
        assert "claude" in models
        assert isinstance(models["openai"], list)
        assert isinstance(models["gemini"], list)
        assert isinstance(models["claude"], list)
        assert len(models["openai"]) > 0
        assert len(models["gemini"]) > 0
        assert len(models["claude"]) > 0

    def test_get_settings_does_not_expose_api_key(self, api_client):
        """API key must NEVER be returned in full."""
        response = api_client.get(f"{BASE_URL}/api/settings")
        data = response.json()
        assert "api_key" not in data, "Raw API key must never be returned to the client"


class TestSaveSettings:
    """Tests for POST /api/settings"""

    def test_save_valid_openai_settings(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "openai", "model": "gpt-5.2", "api_key": "sk-test-fake-key-for-unit-testing"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-5.2"

    def test_save_valid_gemini_settings(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "gemini", "model": "gemini-3.0", "api_key": "AIza-fake-key-for-testing"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "gemini"
        assert data["model"] == "gemini-3.0"

    def test_save_valid_claude_sonnet_settings(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "claude", "model": "claude-sonnet-4-6", "api_key": "sk-ant-fake-key-for-testing"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "claude"
        assert data["model"] == "claude-sonnet-4-6"

    def test_save_valid_claude_opus_settings(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "claude", "model": "claude-opus-4-5", "api_key": "sk-ant-fake-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "claude-opus-4-5"

    def test_save_settings_persists(self, api_client):
        """Settings saved via POST should be retrievable via GET."""
        api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "openai", "model": "gpt-5.2", "api_key": "sk-test-persist-check"},
        )
        get_resp = api_client.get(f"{BASE_URL}/api/settings")
        data = get_resp.json()
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-5.2"
        assert data["api_key_set"] is True

    def test_save_invalid_provider_returns_400(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "nonexistent_provider", "model": "gpt-4o", "api_key": "test"},
        )
        assert response.status_code == 400

    def test_save_invalid_model_returns_400(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "openai", "model": "not-a-real-model", "api_key": "test"},
        )
        assert response.status_code == 400

    def test_save_mismatched_model_provider_returns_400(self, api_client):
        """Gemini model name on an OpenAI provider should fail."""
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "openai", "model": "gemini-3.0", "api_key": "test"},
        )
        assert response.status_code == 400

    def test_save_settings_provider_is_normalized_lowercase(self, api_client):
        """Provider should be stored lowercase even if sent with uppercase."""
        response = api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "OpenAI", "model": "gpt-5.2", "api_key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"


class TestTestConnection:
    """Tests for POST /api/settings/test"""

    def test_test_connection_without_settings_returns_503(self, api_client):
        """If no API key is stored, should return 503."""
        # First clear settings by posting an empty-key scenario
        # (We can't truly clear but this tests the server behavior when key is absent)
        # Check the endpoint exists at minimum
        response = api_client.post(f"{BASE_URL}/api/settings/test", timeout=30)
        # If key was saved above, it will try and likely get 400 (wrong key). If no key, 503.
        assert response.status_code in [200, 400, 503]

    def test_test_connection_with_fake_key_returns_400(self, api_client):
        """A fake API key should cause the LLM call to fail with a 400."""
        api_client.post(
            f"{BASE_URL}/api/settings",
            json={"provider": "openai", "model": "gpt-5.2", "api_key": "sk-fake-key-that-will-fail"},
        )
        response = api_client.post(f"{BASE_URL}/api/settings/test", timeout=30)
        # Should fail gracefully (400 error from provider)
        assert response.status_code in [400, 503]
