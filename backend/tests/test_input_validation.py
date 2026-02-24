"""Tests for input validation (stock symbol sanitizer, image size)."""
import pytest
import base64


def test_valid_symbols():
    """Standard stock symbols should pass validation."""
    from server import sanitize_symbol
    assert sanitize_symbol("RELIANCE") == "RELIANCE"
    assert sanitize_symbol("M&M") == "M&M"
    assert sanitize_symbol("BAJAJ-AUTO") == "BAJAJ-AUTO"
    assert sanitize_symbol("RELIANCE.NS") == "RELIANCE.NS"
    assert sanitize_symbol("TCS") == "TCS"


def test_symbol_with_spaces_stripped():
    """Whitespace should be stripped."""
    from server import sanitize_symbol
    assert sanitize_symbol("  TCS  ") == "TCS"


def test_symbol_with_special_chars_rejected():
    """Symbols with injection characters should be rejected."""
    from server import sanitize_symbol
    from fastapi import HTTPException

    bad_symbols = [
        "'; DROP TABLE",
        "RELIANCE<script>",
        "../etc/passwd",
        "STOCK$INJECT",
        "A/B",
        "TEST;CMD",
    ]
    for sym in bad_symbols:
        with pytest.raises(HTTPException) as exc_info:
            sanitize_symbol(sym)
        assert exc_info.value.status_code == 400


def test_symbol_too_long_rejected():
    """Symbols exceeding max length should be rejected."""
    from server import sanitize_symbol
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        sanitize_symbol("A" * 31)
    assert exc_info.value.status_code == 400


def test_empty_symbol_rejected():
    """Empty or whitespace-only symbols should be rejected."""
    from server import sanitize_symbol
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        sanitize_symbol("")
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        sanitize_symbol("   ")
    assert exc_info.value.status_code == 400


def test_image_size_validation():
    """Image validation should reject oversized images."""
    from server import validate_chart_image

    # Small valid image (10 bytes) — should pass
    small_img = base64.b64encode(b"0123456789").decode()
    validate_chart_image(small_img)  # Should not raise

    # Large image (>10MB) — should fail
    from fastapi import HTTPException
    large_data = b"x" * (11 * 1024 * 1024)
    large_img = base64.b64encode(large_data).decode()
    with pytest.raises(HTTPException) as exc_info:
        validate_chart_image(large_img)
    assert exc_info.value.status_code == 400
    assert "too large" in str(exc_info.value.detail).lower()


def test_invalid_base64_rejected():
    """Invalid base64 data should be rejected."""
    from server import validate_chart_image
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        validate_chart_image("not!!valid==base64$$")
    assert exc_info.value.status_code == 400
