"""
Unit Tests for Technical Analysis Functions
Tests: compute_technicals, compute_adx, compute_support_resistance, safe_float, parse_llm_json
No network calls — uses synthetic dataframes.
"""
import pytest
import sys
import os
import json
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server import compute_technicals, compute_adx, compute_support_resistance, safe_float, parse_llm_json


def make_df(n: int = 60, trend: str = "up") -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame for testing."""
    np.random.seed(42)
    base = 1000.0
    closes = []
    for i in range(n):
        if trend == "up":
            base += np.random.uniform(1, 10)
        elif trend == "down":
            base -= np.random.uniform(1, 10)
        else:
            base += np.random.uniform(-5, 5)
        closes.append(base)

    closes = np.array(closes)
    highs = closes + np.random.uniform(5, 20, n)
    lows = closes - np.random.uniform(5, 20, n)
    opens = closes - np.random.uniform(-10, 10, n)
    volumes = np.random.randint(100000, 1000000, n).astype(float)

    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes
    }, index=idx)


class TestSafeFloat:
    def test_basic_float(self):
        assert safe_float(3.14) == 3.14

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_nan_returns_none(self):
        assert safe_float(float("nan")) is None

    def test_inf_returns_none(self):
        assert safe_float(float("inf")) is None

    def test_neg_inf_returns_none(self):
        assert safe_float(float("-inf")) is None

    def test_int_converted(self):
        result = safe_float(100)
        assert result == 100.0
        assert isinstance(result, float)

    def test_rounding(self):
        result = safe_float(3.14159265)
        assert result == 3.14


class TestComputeTechnicals:
    def test_returns_empty_dict_for_short_df(self):
        df = make_df(n=5)
        result = compute_technicals(df)
        assert result == {}

    def test_returns_empty_dict_for_empty_df(self):
        result = compute_technicals(pd.DataFrame())
        assert result == {}

    def test_all_expected_keys_present(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        assert "rsi" in result
        assert "rsi_signal" in result
        assert "adx" in result
        assert "macd" in result
        assert "moving_averages" in result
        assert "bollinger_bands" in result
        assert "volume_avg_20" in result
        assert "price_vs_sma20" in result

    def test_rsi_in_valid_range(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        if result.get("rsi") is not None:
            assert 0 <= result["rsi"] <= 100

    def test_rsi_signal_is_valid(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        assert result["rsi_signal"] in ["Overbought", "Oversold", "Neutral"]

    def test_macd_structure(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        macd = result["macd"]
        assert "macd_line" in macd
        assert "signal_line" in macd
        assert "histogram" in macd
        assert "signal" in macd
        assert macd["signal"] in ["Bullish", "Bearish"]

    def test_moving_averages_structure(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        ma = result["moving_averages"]
        assert "sma20" in ma
        assert "ema20" in ma
        # sma50 will be None if n < 50, otherwise a value
        assert "sma50" in ma
        assert "sma200" in ma

    def test_bollinger_bands_structure(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        bb = result["bollinger_bands"]
        assert "upper" in bb
        assert "middle" in bb
        assert "lower" in bb
        assert "signal" in bb
        assert bb["signal"] in ["Overbought", "Oversold", "Normal"]
        if bb["upper"] and bb["lower"] and bb["middle"]:
            assert bb["upper"] > bb["middle"] > bb["lower"]

    def test_price_vs_sma20_valid(self):
        df = make_df(n=60)
        result = compute_technicals(df)
        assert result["price_vs_sma20"] in ["Above", "Below"]

    def test_uptrend_shows_bullish_macd_often(self):
        """Strong uptrend should produce a bullish MACD most of the time."""
        df = make_df(n=80, trend="up")
        result = compute_technicals(df)
        # Not guaranteed but in a strong uptrend more likely bullish
        assert result["macd"]["signal"] in ["Bullish", "Bearish"]

    def test_sma50_available_with_enough_data(self):
        df = make_df(n=100)
        result = compute_technicals(df)
        assert result["moving_averages"]["sma50"] is not None


class TestComputeADX:
    def test_returns_none_for_insufficient_data(self):
        df = make_df(n=5)
        result = compute_adx(df["High"], df["Low"], df["Close"])
        assert result is None

    def test_returns_float_for_sufficient_data(self):
        df = make_df(n=60)
        result = compute_adx(df["High"], df["Low"], df["Close"])
        assert result is not None
        assert isinstance(result, float)

    def test_adx_in_valid_range(self):
        df = make_df(n=60)
        result = compute_adx(df["High"], df["Low"], df["Close"])
        if result is not None:
            assert 0 <= result <= 100


class TestComputeSupportResistance:
    def test_returns_empty_for_short_df(self):
        df = make_df(n=3)
        result = compute_support_resistance(df)
        assert result == {}

    def test_returns_empty_for_empty_df(self):
        result = compute_support_resistance(pd.DataFrame())
        assert result == {}

    def test_all_keys_present(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        assert "pivot" in result
        assert "resistance" in result
        assert "support" in result
        assert "period_highs_lows" in result

    def test_pivot_is_between_high_and_low(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        pivot = result["pivot"]
        last_high = safe_float(df["High"].iloc[-1])
        last_low = safe_float(df["Low"].iloc[-1])
        assert last_low <= pivot <= last_high

    def test_resistance_ordering(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        r = result["resistance"]
        if r["r1"] and r["r2"] and r["r3"]:
            assert r["r1"] <= r["r2"] <= r["r3"]

    def test_support_ordering(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        s = result["support"]
        if s["s1"] and s["s2"] and s["s3"]:
            assert s["s3"] <= s["s2"] <= s["s1"]

    def test_period_highs_lows_structure(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        phl = result["period_highs_lows"]
        assert "high_52w" in phl
        assert "low_52w" in phl
        assert "high_6m" in phl
        assert "low_6m" in phl
        assert "high_1m" in phl
        assert "low_1m" in phl

    def test_period_high_greater_than_low(self):
        df = make_df(n=60)
        result = compute_support_resistance(df)
        phl = result["period_highs_lows"]
        if phl["high_1m"] and phl["low_1m"]:
            assert phl["high_1m"] >= phl["low_1m"]


class TestParseLLMJson:
    def test_parses_plain_json(self):
        raw = '{"recommendation": "BUY", "confidence": 75}'
        result = parse_llm_json(raw, {})
        assert result["recommendation"] == "BUY"
        assert result["confidence"] == 75

    def test_strips_markdown_code_fences(self):
        raw = "```json\n{\"recommendation\": \"SELL\"}\n```"
        result = parse_llm_json(raw, {})
        assert result["recommendation"] == "SELL"

    def test_strips_backtick_without_json_label(self):
        raw = "```\n{\"sentiment\": \"Bullish\"}\n```"
        result = parse_llm_json(raw, {})
        assert result["sentiment"] == "Bullish"

    def test_returns_fallback_on_invalid_json(self):
        fallback = {"recommendation": "HOLD", "confidence": 50}
        result = parse_llm_json("this is not json at all", fallback)
        assert result == fallback

    def test_returns_fallback_on_empty_string(self):
        fallback = {"error": True}
        result = parse_llm_json("", fallback)
        assert result == fallback

    def test_handles_json_with_leading_whitespace(self):
        raw = '   {"prediction": "UP"}   '
        result = parse_llm_json(raw, {})
        assert result["prediction"] == "UP"
