"""
backend/options.py — F&O: Black-Scholes Greeks, Max Pain, NSE option chain fetch.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# India risk-free rate (RBI repo rate proxy)
INDIA_RISK_FREE_RATE = 0.065


# ---------------------------------------------------------------------------
# Black-Scholes Greeks
# ---------------------------------------------------------------------------

def black_scholes_greeks(
    S: float,        # Underlying price
    K: float,        # Strike price
    T: float,        # Time to expiry in years
    r: float,        # Risk-free rate (annualised)
    sigma: float,    # Implied volatility (annualised)
    option_type: str # "CE" or "PE"
) -> dict:
    """
    Calculate Black-Scholes option price and Greeks.
    Handles edge cases: T=0, sigma=0.
    """
    try:
        from scipy.stats import norm  # type: ignore
    except ImportError:
        raise RuntimeError("scipy not installed. Run: pip install scipy")

    if T <= 0:
        # At expiry — intrinsic value only
        intrinsic = max(0, S - K) if option_type == "CE" else max(0, K - S)
        return {
            "delta":  1.0 if option_type == "CE" and S > K else (-1.0 if option_type == "PE" and S < K else 0.0),
            "gamma":  0.0,
            "theta":  0.0,
            "vega":   0.0,
            "price":  round(intrinsic, 2),
        }

    if sigma <= 0:
        sigma = 1e-6  # avoid division by zero

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "CE":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        delta = norm.cdf(d1)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        delta = norm.cdf(d1) - 1

    gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
    vega  = S * norm.pdf(d1) * math.sqrt(T) / 100       # per 1% IV move
    theta = (
        -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
        - r * K * math.exp(-r * T) * (norm.cdf(d2) if option_type == "CE" else norm.cdf(-d2))
    ) / 365  # per day

    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega":  round(vega, 4),
        "price": round(price, 2),
    }


# ---------------------------------------------------------------------------
# Max Pain Calculation
# ---------------------------------------------------------------------------

def calculate_max_pain(option_chain: list) -> Optional[float]:
    """
    Find the strike at which total option holder losses are maximised.
    option_chain: list of {strike_price, option_type, open_interest}
    Returns max pain strike price as float, or None.
    """
    if not option_chain:
        return None

    strikes = sorted(set(row["strike_price"] for row in option_chain))
    if len(strikes) < 2:
        return None

    total_loss_at_strike: dict = {}

    for test_strike in strikes:
        total_loss = 0.0
        for row in option_chain:
            K  = row["strike_price"]
            oi = row.get("open_interest", 0) or 0
            if row.get("option_type") == "CE":
                loss = max(0, test_strike - K) * oi
            else:
                loss = max(0, K - test_strike) * oi
            total_loss += loss
        total_loss_at_strike[test_strike] = total_loss

    max_pain_strike = min(total_loss_at_strike, key=total_loss_at_strike.get)
    return float(max_pain_strike)


# ---------------------------------------------------------------------------
# Option Chain Fetch — NSE primary, yfinance fallback
# ---------------------------------------------------------------------------

def fetch_option_chain_yfinance(symbol: str) -> tuple[float, list[str], list]:
    """
    Fallback: fetch option chain via yfinance.
    Returns (underlying_price, expiry_dates, chain_rows)
    """
    import yfinance as yf  # type: ignore

    ticker = yf.Ticker(symbol)
    info   = ticker.info or {}
    underlying_price = float(info.get("regularMarketPrice") or info.get("currentPrice", 0))

    expiry_dates = list(ticker.options) if ticker.options else []
    chain_rows: list = []

    for expiry in expiry_dates[:3]:  # limit to 3 nearest expiries to stay fast
        try:
            chain = ticker.option_chain(expiry)
            for _, row in chain.calls.iterrows():
                chain_rows.append({
                    "strike_price":    float(row.get("strike", 0)),
                    "option_type":     "CE",
                    "expiry_date":     expiry,
                    "open_interest":   int(row.get("openInterest", 0)),
                    "change_in_oi":    0,
                    "volume":          int(row.get("volume", 0) or 0),
                    "implied_volatility": round(float(row.get("impliedVolatility", 0)) * 100, 2),
                    "ltp":             float(row.get("lastPrice", 0)),
                    "bid":             float(row.get("bid", 0)),
                    "ask":             float(row.get("ask", 0)),
                })
            for _, row in chain.puts.iterrows():
                chain_rows.append({
                    "strike_price":    float(row.get("strike", 0)),
                    "option_type":     "PE",
                    "expiry_date":     expiry,
                    "open_interest":   int(row.get("openInterest", 0)),
                    "change_in_oi":    0,
                    "volume":          int(row.get("volume", 0) or 0),
                    "implied_volatility": round(float(row.get("impliedVolatility", 0)) * 100, 2),
                    "ltp":             float(row.get("lastPrice", 0)),
                    "bid":             float(row.get("bid", 0)),
                    "ask":             float(row.get("ask", 0)),
                })
        except Exception as e:
            logger.warning(f"yfinance option chain error for {expiry}: {e}")
            continue

    return underlying_price, expiry_dates, chain_rows


def fetch_option_chain_nse(symbol: str) -> tuple[float, list[str], list]:
    """
    Primary: fetch option chain from NSE India API.
    Falls back to yfinance on failure.
    """
    import requests  # type: ignore

    base_sym = symbol.replace(".NS", "").replace(".BO", "")
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={base_sym}"
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":          "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.nseindia.com/",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        session = requests.Session()
        # Warm up NSE session (cookie fetch)
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        underlying_price = float(
            data.get("records", {}).get("underlyingValue", 0)
        )
        expiry_dates = data.get("records", {}).get("expiryDates", [])
        raw_data     = data.get("records", {}).get("data", [])

        chain_rows = []
        for entry in raw_data:
            for opt_type, key in [("CE", "CE"), ("PE", "PE")]:
                opt = entry.get(key)
                if not opt:
                    continue
                chain_rows.append({
                    "strike_price":    float(entry.get("strikePrice", 0)),
                    "option_type":     opt_type,
                    "expiry_date":     entry.get("expiryDate", ""),
                    "open_interest":   int(opt.get("openInterest", 0)),
                    "change_in_oi":    int(opt.get("changeinOpenInterest", 0)),
                    "volume":          int(opt.get("totalTradedVolume", 0)),
                    "implied_volatility": float(opt.get("impliedVolatility", 0)),
                    "ltp":             float(opt.get("lastPrice", 0)),
                    "bid":             float(opt.get("bidprice", 0)),
                    "ask":             float(opt.get("askPrice", 0)),
                })
        return underlying_price, expiry_dates, chain_rows

    except Exception as e:
        logger.warning(f"NSE option chain failed for {base_sym}: {e}. Falling back to yfinance.")
        return fetch_option_chain_yfinance(symbol)


def analyse_oi(chain_rows: list) -> dict:
    """Compute PCR, OI totals, and directional signal from option chain."""
    call_oi = sum(r["open_interest"] for r in chain_rows if r["option_type"] == "CE")
    put_oi  = sum(r["open_interest"] for r in chain_rows if r["option_type"] == "PE")
    pcr     = round(put_oi / call_oi, 2) if call_oi else 0
    if pcr > 1.2:
        signal = "Bullish (high put OI — hedging)"
    elif pcr < 0.7:
        signal = "Bearish (high call OI — resistance)"
    else:
        signal = "Neutral"
    return {
        "total_call_oi": call_oi,
        "total_put_oi":  put_oi,
        "pcr":           pcr,
        "pcr_signal":    signal,
    }
