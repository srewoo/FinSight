import pytest
import requests
import os

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')

@pytest.fixture
def api_client():
    """Shared requests session for API testing"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def base_url():
    """Base URL for API endpoints"""
    return BASE_URL
