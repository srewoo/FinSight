"""
Market Regime Detection
Classifies market conditions as Trending (Bull/Bear), Ranging, or Volatile.
Uses statistical analysis of price data.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index (trend strength)."""
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Average True Range (volatility)."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.rolling(window=period).mean()


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def detect_market_regime(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect market regime from price data.
    
    Regimes:
    - Strong Bull: ADX > 25, +DI > -DI, RSI > 50, Price > SMA50 > SMA200
    - Strong Bear: ADX > 25, -DI > +DI, RSI < 50, Price < SMA50 < SMA200
    - Weak Bull: ADX < 25, Price > SMA20, RSI 50-60
    - Weak Bear: ADX < 25, Price < SMA20, RSI 40-50
    - Ranging: ADX < 20, Price oscillating around SMA20
    - Volatile: ATR > 1.5x average ATR, Wide price swings
    
    Returns:
        Dict with regime classification and confidence
    """
    if len(df) < 200:
        return {
            "regime": "Unknown",
            "confidence": 0,
            "reason": "Insufficient data (need 200+ periods)"
        }
    
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # Calculate indicators
    adx = calculate_adx(high, low, close)
    atr = calculate_atr(high, low, close)
    rsi = calculate_rsi(close)
    
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean()
    sma200 = close.rolling(window=200).mean()
    
    # Get current values
    current_adx = adx.iloc[-1]
    current_atr = atr.iloc[-1]
    current_rsi = rsi.iloc[-1]
    current_price = close.iloc[-1]
    
    avg_atr = atr.rolling(window=50).mean().iloc[-1]
    
    # Calculate +DI and -DI for trend direction
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_calc = tr.rolling(window=14).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr_calc)
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr_calc)
    
    current_plus_di = plus_di.iloc[-1]
    current_minus_di = minus_di.iloc[-1]
    
    # Scoring system
    regime_scores = {
        "Strong Bull": 0,
        "Strong Bear": 0,
        "Weak Bull": 0,
        "Weak Bear": 0,
        "Ranging": 0,
        "Volatile": 0,
    }
    
    # Trend strength (ADX)
    if current_adx > 25:
        regime_scores["Strong Bull"] += 2
        regime_scores["Strong Bear"] += 2
    elif current_adx < 20:
        regime_scores["Ranging"] += 3
        regime_scores["Weak Bull"] += 1
        regime_scores["Weak Bear"] += 1
    
    # Trend direction (DI)
    if current_plus_di > current_minus_di:
        regime_scores["Strong Bull"] += 3
        regime_scores["Weak Bull"] += 2
    else:
        regime_scores["Strong Bear"] += 3
        regime_scores["Weak Bear"] += 2
    
    # RSI position
    if current_rsi > 60:
        regime_scores["Strong Bull"] += 2
        regime_scores["Weak Bull"] += 1
    elif current_rsi < 40:
        regime_scores["Strong Bear"] += 2
        regime_scores["Weak Bear"] += 1
    elif 45 <= current_rsi <= 55:
        regime_scores["Ranging"] += 2
    
    # Moving average alignment
    if current_price > sma20.iloc[-1] > sma50.iloc[-1] > sma200.iloc[-1]:
        regime_scores["Strong Bull"] += 4
    elif current_price < sma20.iloc[-1] < sma50.iloc[-1] < sma200.iloc[-1]:
        regime_scores["Strong Bear"] += 4
    elif abs(current_price - sma20.iloc[-1]) / sma20.iloc[-1] < 0.02:
        regime_scores["Ranging"] += 2
    
    # Volatility check
    if current_atr > 1.5 * avg_atr:
        regime_scores["Volatile"] += 5
    
    # Price range check for ranging market
    recent_high = high.tail(20).max()
    recent_low = low.tail(20).min()
    range_pct = (recent_high - recent_low) / recent_low
    
    if range_pct < 0.05:  # Less than 5% range in 20 periods
        regime_scores["Ranging"] += 3
    
    # Determine regime
    best_regime = max(regime_scores, key=regime_scores.get)
    best_score = regime_scores[best_regime]
    
    # Calculate confidence (0-100)
    total_score = sum(regime_scores.values())
    confidence = int((best_score / max(total_score, 1)) * 100)
    
    # Generate description
    descriptions = {
        "Strong Bull": "Strong uptrend with high conviction. Consider buying on dips.",
        "Strong Bear": "Strong downtrend with high conviction. Consider selling on rallies.",
        "Weak Bull": "Moderate uptrend, low conviction. Watch for confirmation.",
        "Weak Bear": "Moderate downtrend, low conviction. Watch for confirmation.",
        "Ranging": "Sideways market with no clear direction. Trade range boundaries.",
        "Volatile": "High volatility environment. Use wider stops, reduce position size.",
    }
    
    return {
        "regime": best_regime,
        "confidence": confidence,
        "description": descriptions.get(best_regime, ""),
        "metrics": {
            "adx": round(current_adx, 2) if not pd.isna(current_adx) else None,
            "rsi": round(current_rsi, 2) if not pd.isna(current_rsi) else None,
            "atr": round(current_atr, 2) if not pd.isna(current_atr) else None,
            "plus_di": round(current_plus_di, 2) if not pd.isna(current_plus_di) else None,
            "minus_di": round(current_minus_di, 2) if not pd.isna(current_minus_di) else None,
            "price_vs_sma20": round((current_price - sma20.iloc[-1]) / sma20.iloc[-1] * 100, 2) if not pd.isna(sma20.iloc[-1]) else None,
            "price_vs_sma50": round((current_price - sma50.iloc[-1]) / sma50.iloc[-1] * 100, 2) if not pd.isna(sma50.iloc[-1]) else None,
            "price_vs_sma200": round((current_price - sma200.iloc[-1]) / sma200.iloc[-1] * 100, 2) if not pd.isna(sma200.iloc[-1]) else None,
        },
        "regime_scores": regime_scores,
    }


def detect_multi_timeframe_regime(
    df_daily: pd.DataFrame,
    df_weekly: Optional[pd.DataFrame] = None,
    df_intraday: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Detect market regime across multiple timeframes for confluence analysis.
    
    Returns:
        Dict with regime for each timeframe and overall confluence
    """
    result = {
        "daily": detect_market_regime(df_daily),
        "weekly": None,
        "intraday": None,
        "confluence": None,
        "overall_regime": None,
    }
    
    if df_weekly is not None and len(df_weekly) >= 50:
        result["weekly"] = detect_market_regime(df_weekly)
    
    if df_intraday is not None and len(df_intraday) >= 50:
        result["intraday"] = detect_market_regime(df_intraday)
    
    # Calculate confluence
    regimes = [result["daily"]["regime"]]
    if result["weekly"]:
        regimes.append(result["weekly"]["regime"])
    if result["intraday"]:
        regimes.append(result["intraday"]["regime"])
    
    # Check if all timeframes agree
    if len(set(regimes)) == 1:
        result["confluence"] = "Strong"
        result["overall_regime"] = regimes[0]
    elif regimes.count(regimes[0]) > len(regimes) / 2:
        result["confluence"] = "Moderate"
        result["overall_regime"] = regimes[0]
    else:
        result["confluence"] = "Mixed"
        # Use daily as primary
        result["overall_regime"] = result["daily"]["regime"]
    
    return result
