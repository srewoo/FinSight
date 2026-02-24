"""Tests for the SEBI disclaimer system."""
import pytest
from disclaimer import (
    CURRENT_DISCLAIMER_VERSION,
    SEBI_DISCLAIMER_TEXT,
    SEBI_DISCLAIMER_SHORT,
    build_disclaimer_response_field,
)


def test_disclaimer_version_is_set():
    assert CURRENT_DISCLAIMER_VERSION == "1.0"


def test_disclaimer_text_mentions_sebi():
    assert "SEBI" in SEBI_DISCLAIMER_TEXT
    assert "Investment Advisers" in SEBI_DISCLAIMER_TEXT
    assert "2013" in SEBI_DISCLAIMER_TEXT


def test_disclaimer_short_text_is_concise():
    assert len(SEBI_DISCLAIMER_SHORT) < 200
    assert "SEBI" in SEBI_DISCLAIMER_SHORT


def test_build_disclaimer_response_field():
    field = build_disclaimer_response_field()
    assert field["version"] == CURRENT_DISCLAIMER_VERSION
    assert field["text"] == SEBI_DISCLAIMER_SHORT
    assert field["full_text_available"] is True


def test_disclaimer_texts_are_not_empty():
    assert len(SEBI_DISCLAIMER_TEXT) > 100
    assert len(SEBI_DISCLAIMER_SHORT) > 20
