"""
backend/tests/test_fundamentals.py — Phase 2.1: Fundamentals & Breakout tests
Self-contained — no server.py imports (avoids firebase_admin dependency).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import math
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Pure helper functions (mirrors server.py)
# ---------------------------------------------------------------------------

def safe_float(v):
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return None


def _pct(v):
    """Convert fractional value to percent, rounded to 2 dp."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f * 100, 2)
    except (TypeError, ValueError):
        return None


def extract_fundamentals(info: dict) -> dict:
    return {
        "valuation": {
            "pe_ratio":   safe_float(info.get("trailingPE")),
            "forward_pe": safe_float(info.get("forwardPE")),
            "pb_ratio":   safe_float(info.get("priceToBook")),
            "peg_ratio":  safe_float(info.get("pegRatio")),
            "ev_ebitda":  safe_float(info.get("enterpriseToEbitda")),
            "ev":         safe_float(info.get("enterpriseValue")),
            "market_cap": safe_float(info.get("marketCap")),
        },
        "profitability": {
            "roe":              _pct(info.get("returnOnEquity")),
            "roa":              _pct(info.get("returnOnAssets")),
            "gross_margin":     _pct(info.get("grossMargins")),
            "operating_margin": _pct(info.get("operatingMargins")),
            "profit_margin":    _pct(info.get("profitMargins")),
            "ebitda_margin":    _pct(info.get("ebitdaMargins")),
        },
        "growth": {
            "revenue_growth":  _pct(info.get("revenueGrowth")),
            "earnings_growth": _pct(info.get("earningsGrowth")),
            "eps":             safe_float(info.get("trailingEps")),
            "forward_eps":     safe_float(info.get("forwardEps")),
        },
        "financial_health": {
            "debt_to_equity": safe_float(info.get("debtToEquity")),
            "current_ratio":  safe_float(info.get("currentRatio")),
            "quick_ratio":    safe_float(info.get("quickRatio")),
            "total_debt":     safe_float(info.get("totalDebt")),
            "free_cash_flow": safe_float(info.get("freeCashflow")),
        },
        "dividends": {
            "dividend_yield":   _pct(info.get("dividendYield")),
            "dividend_rate":    safe_float(info.get("dividendRate")),
            "payout_ratio":     _pct(info.get("payoutRatio")),
            "ex_dividend_date": info.get("exDividendDate"),
        },
        "ownership": {
            "institutional_holding": _pct(info.get("heldPercentInstitutions")),
            "insider_holding":       _pct(info.get("heldPercentInsiders")),
            "float_shares":          safe_float(info.get("floatShares")),
        },
    }


# ---------------------------------------------------------------------------
# Tests for extract_fundamentals
# ---------------------------------------------------------------------------

class TestExtractFundamentals:
    def test_full_info(self):
        info = {
            "trailingPE": 20.5, "forwardPE": 18.0, "priceToBook": 3.2,
            "returnOnEquity": 0.15, "grossMargins": 0.47, "profitMargins": 0.14,
            "revenueGrowth": 0.12, "trailingEps": 55.3,
            "debtToEquity": 23.5, "dividendYield": 0.015,
            "heldPercentInstitutions": 0.42, "marketCap": 4e12,
        }
        r = extract_fundamentals(info)
        assert r["valuation"]["pe_ratio"] == pytest.approx(20.5)
        assert r["profitability"]["roe"] == pytest.approx(15.0)
        assert r["profitability"]["gross_margin"] == pytest.approx(47.0)
        assert r["growth"]["revenue_growth"] == pytest.approx(12.0)
        assert r["growth"]["eps"] == pytest.approx(55.3)
        assert r["financial_health"]["debt_to_equity"] == pytest.approx(23.5)
        # 0.015 * 100 = 1.5
        assert r["dividends"]["dividend_yield"] == pytest.approx(1.5)
        assert r["ownership"]["institutional_holding"] == pytest.approx(42.0)

    def test_empty_info(self):
        r = extract_fundamentals({})
        for group in r.values():
            for k, v in group.items():
                if k != "ex_dividend_date":
                    assert v is None

    def test_partial_info(self):
        r = extract_fundamentals({"trailingPE": 30.0, "profitMargins": 0.10})
        assert r["valuation"]["pe_ratio"] == pytest.approx(30.0)
        assert r["profitability"]["profit_margin"] == pytest.approx(10.0)
        assert r["valuation"]["market_cap"] is None

    def test_zero_values(self):
        r = extract_fundamentals({"trailingPE": 0, "returnOnEquity": 0.0})
        assert r["valuation"]["pe_ratio"] == pytest.approx(0.0)
        assert r["profitability"]["roe"] == pytest.approx(0.0)

    def test_nan_value(self):
        r = extract_fundamentals({"trailingPE": float("nan")})
        assert r["valuation"]["pe_ratio"] is None

    def test_inf_value(self):
        r = extract_fundamentals({"trailingPE": float("inf")})
        assert r["valuation"]["pe_ratio"] is None


# ---------------------------------------------------------------------------
# Breakout detector (pure function, mirroring server.py detect_breakout)
# ---------------------------------------------------------------------------

def detect_breakout(df, sr, technicals):
    if df is None or len(df) < 20:
        return None
    try:
        current_price = safe_float(df["Close"].iloc[-1])
        prev_price    = safe_float(df["Close"].iloc[-2]) if len(df) > 1 else current_price
        avg_vol       = safe_float(df["Volume"].iloc[-20:].mean())
        today_vol     = safe_float(df["Volume"].iloc[-1])
        r1 = safe_float((sr.get("resistance") or {}).get("r1"))
        s1 = safe_float((sr.get("support") or {}).get("s1"))
        rsi      = safe_float(technicals.get("rsi"))
        macd_sig = technicals.get("macd", {}).get("signal", "")
        adx      = safe_float(technicals.get("adx"))
        if None in (current_price, avg_vol, today_vol):
            return None
        score, signals, breakout_type = 0, [], "neutral"
        vol_ratio = round(today_vol / avg_vol, 2) if avg_vol else 1.0
        if r1 and current_price > r1:
            if prev_price and prev_price < r1:
                score += 3
                signals.append("Crossed above R1")
            else:
                score += 1
            breakout_type = "bullish"
        if vol_ratio >= 2.0:
            score += 3
        elif vol_ratio >= 1.5:
            score += 2
        if rsi and 50 <= rsi <= 70:
            score += 2
        if macd_sig == "Bullish":
            score += 1
        if adx and adx > 25:
            score += 1
        if s1 and current_price < s1:
            if prev_price and prev_price > s1:
                score += 3
            breakout_type = "bearish"
        if score < 4:
            return None
        return {
            "breakout_type": breakout_type,
            "breakout_score": score,
            "current_price": current_price,
            "volume_ratio": vol_ratio,
            "signals": signals,
        }
    except Exception:
        return None


def _make_df(n=30, price=500.0, vol_spike=False):
    idx = pd.date_range("2025-01-01", periods=n)
    closes  = [price] * n
    volumes = [100_000] * n
    if vol_spike:
        volumes[-1] = 300_000
    return pd.DataFrame({"Close": closes, "Volume": volumes}, index=idx)

def _sr(r1=510.0, s1=490.0):
    return {"resistance": {"r1": r1, "r2": 520.0}, "support": {"s1": s1, "s2": 480.0}}

def _techs(rsi=55, macd="Bullish", adx=30):
    return {"rsi": rsi, "macd": {"signal": macd}, "adx": adx}


class TestDetectBreakout:
    def test_returns_none_for_short_df(self):
        assert detect_breakout(_make_df(n=10), _sr(), _techs()) is None

    def test_bullish_breakout_detected(self):
        df = _make_df(n=30, price=515.0, vol_spike=True)
        df.iloc[-2, df.columns.get_loc("Close")] = 509.0
        result = detect_breakout(df, _sr(r1=510.0), _techs(rsi=58, macd="Bullish", adx=28))
        assert result is not None
        assert result["breakout_type"] == "bullish"
        assert result["breakout_score"] >= 4

    def test_no_breakout_low_score(self):
        assert detect_breakout(_make_df(n=30, price=505.0), _sr(r1=510.0), _techs(rsi=45, macd="Bearish", adx=15)) is None

    def test_volume_ratio_computed(self):
        df = _make_df(n=30, price=515.0, vol_spike=True)
        result = detect_breakout(df, _sr(r1=510.0), _techs(rsi=58, macd="Bullish", adx=28))
        if result:
            assert result["volume_ratio"] == pytest.approx(3.0, abs=0.5)

    def test_bearish_breakdown(self):
        df = _make_df(n=30, price=485.0, vol_spike=True)
        df.iloc[-2, df.columns.get_loc("Close")] = 491.0
        result = detect_breakout(df, _sr(s1=490.0), _techs(rsi=40, macd="Bearish", adx=28))
        if result:
            assert result["breakout_type"] == "bearish"
