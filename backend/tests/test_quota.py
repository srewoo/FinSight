"""Tests for the AI quota system."""
import pytest
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.usage_tracking = MagicMock()
    db.usage_tracking.find_one = AsyncMock(return_value=None)
    db.usage_tracking.insert_one = AsyncMock()
    db.usage_tracking.update_one = AsyncMock()
    return db


@pytest.fixture(autouse=True)
def set_quota_limit(monkeypatch):
    """Set a low quota for testing."""
    monkeypatch.setenv("AI_FREE_TIER_DAILY_LIMIT", "3")


@pytest.mark.asyncio
async def test_first_request_creates_usage_record(mock_db, monkeypatch):
    """First AI request for a user should create a new usage_tracking document."""
    monkeypatch.setattr("server.db", mock_db)
    from server import check_and_increment_quota

    result = await check_and_increment_quota("user123", "ai_analysis")
    assert result["used"] == 1
    assert result["remaining"] == 2
    assert result["limit"] == 3


@pytest.mark.asyncio
async def test_quota_increments_on_each_request(mock_db, monkeypatch):
    """Quota count should increment with each request."""
    mock_db.usage_tracking.find_one = AsyncMock(return_value={
        "user_id": "user123",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ai_analysis_count": 1,
    })
    monkeypatch.setattr("server.db", mock_db)
    from server import check_and_increment_quota

    result = await check_and_increment_quota("user123", "ai_analysis")
    assert result["used"] == 2
    assert result["remaining"] == 1


@pytest.mark.asyncio
async def test_quota_rejects_after_daily_limit(mock_db, monkeypatch):
    """Should raise HTTPException 429 when daily limit is reached."""
    mock_db.usage_tracking.find_one = AsyncMock(return_value={
        "user_id": "user123",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ai_analysis_count": 3,
    })
    monkeypatch.setattr("server.db", mock_db)
    from server import check_and_increment_quota
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await check_and_increment_quota("user123", "ai_analysis")
    assert exc_info.value.status_code == 429
    assert "Daily AI analysis limit reached" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_quota_different_features_tracked_separately(mock_db, monkeypatch):
    """Different feature types should have separate counters."""
    mock_db.usage_tracking.find_one = AsyncMock(return_value={
        "user_id": "user123",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ai_analysis_count": 3,
        "chart_scan_count": 0,
    })
    monkeypatch.setattr("server.db", mock_db)
    from server import check_and_increment_quota

    # chart_scan should still work even though ai_analysis is maxed
    result = await check_and_increment_quota("user123", "chart_scan")
    assert result["used"] == 1
    assert result["remaining"] == 2
