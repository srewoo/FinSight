"""
Financial Modeling Prep API Integration
Alternative data source to yfinance for more reliable stock data.
Docs: https://site.financialmodelingprep.com/developer/docs

Supports user-specific API keys with fallback to environment variable.
"""
import logging
import os
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# FMP API Configuration
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"


def get_fmp_api_key(user_profile: Optional[Dict] = None) -> Optional[str]:
    """Get FMP API key from user profile or environment."""
    if user_profile:
        try:
            from encryption import _safe_decrypt
            stored = user_profile.get("api_keys", {})
            enc_key = stored.get("fmp_enc", "")
            user_key = _safe_decrypt(enc_key) if enc_key else ""
            if user_key:
                return user_key
        except Exception as e:
            logger.warning(f"Failed to get user FMP key: {e}")

    # Fallback to environment
    return os.environ.get("FMP_API_KEY", "")


def _make_request(endpoint: str, params: Optional[Dict] = None, user_profile: Optional[Dict] = None) -> Optional[Dict]:
    """Make authenticated request to FMP API with user-specific key."""
    api_key = get_fmp_api_key(user_profile)

    if not api_key:
        logger.warning("FMP_API_KEY not configured (user or env)")
        return None

    try:
        url = f"{FMP_BASE_URL}/{endpoint}"
        query_params = {"apikey": api_key, **(params or {})}

        response = requests.get(url, params=query_params, timeout=10)
        response.raise_for_status()

        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"FMP API request failed: {e}")
        return None


def get_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get real-time stock quote.
    Returns: {symbol, price, changesPercentage, change, dayLow, dayHigh, yearHigh, yearLow, marketCap, volume, avgVolume, open, previousClose, pe, eps}
    """
    # FMP uses symbol without .NS suffix for Indian stocks
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    data = _make_request(f"quote/{clean_symbol}.NS")
    if data and isinstance(data, list) and len(data) > 0:
        quote = data[0]
        return {
            "symbol": symbol,
            "price": quote.get("price"),
            "change": quote.get("change"),
            "change_percent": quote.get("changesPercentage"),
            "day_high": quote.get("dayHigh"),
            "day_low": quote.get("dayLow"),
            "year_high": quote.get("yearHigh"),
            "year_low": quote.get("yearLow"),
            "market_cap": quote.get("marketCap"),
            "volume": quote.get("volume"),
            "avg_volume": quote.get("avgVolume"),
            "open": quote.get("open"),
            "previous_close": quote.get("previousClose"),
            "pe_ratio": quote.get("pe"),
            "eps": quote.get("eps"),
        }
    return None


def get_fundamentals(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive fundamental data.
    Returns valuation, profitability, and financial health metrics.
    """
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    # Get key metrics
    metrics = _make_request(f"key-metrics/{clean_symbol}.NS")
    if not metrics or not isinstance(metrics, list) or len(metrics) == 0:
        return None
    
    latest = metrics[0]  # Most recent
    
    return {
        "market_cap": latest.get("marketCap"),
        "pe_ratio": latest.get("peRatio"),
        "pb_ratio": latest.get("pbRatio"),
        "roe": latest.get("roe"),
        "roa": latest.get("roa"),
        "debt_to_equity": latest.get("debtToEquity"),
        "current_ratio": latest.get("currentRatio"),
        "dividend_yield": latest.get("dividendYield"),
        "eps": latest.get("eps"),
        "book_value_per_share": latest.get("bookValuePerShare"),
        "operating_cash_flow_per_share": latest.get("operatingCashFlowPerShare"),
        "free_cash_flow_per_share": latest.get("freeCashFlowPerShare"),
    }


def get_historical_prices(
    symbol: str,
    period: str = "1M",
    interval: str = "1day"
) -> Optional[List[Dict[str, Any]]]:
    """
    Get historical price data.
    period: 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y
    interval: 1min, 5min, 15min, 30min, 1hour, 4hour, 1day, 1week, 1month
    """
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    # Map period to FMP timeseries parameter
    period_map = {
        "5d": 5,
        "1mo": 22,
        "3mo": 65,
        "6mo": 130,
        "1y": 252,
        "2y": 504,
        "5y": 1260,
    }
    
    timeseries = period_map.get(period.lower(), 252)
    
    data = _make_request(
        f"historical-price-full/{clean_symbol}.NS",
        {"timeseries": timeseries}
    )
    
    if data and "historical" in data:
        return [
            {
                "date": item.get("date"),
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
            }
            for item in reversed(data["historical"])  # Oldest first
        ]
    return None


def get_income_statement(symbol: str) -> Optional[Dict[str, Any]]:
    """Get latest income statement."""
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    data = _make_request(f"income-statement/{clean_symbol}.NS")
    if data and isinstance(data, list) and len(data) > 0:
        stmt = data[0]
        return {
            "revenue": stmt.get("revenue"),
            "cost_of_revenue": stmt.get("costOfRevenue"),
            "gross_profit": stmt.get("grossProfit"),
            "operating_expenses": stmt.get("operatingExpenses"),
            "operating_income": stmt.get("operatingIncome"),
            "net_income": stmt.get("netIncome"),
            "eps": stmt.get("eps"),
            "eps_diluted": stmt.get("epsDiluted"),
        }
    return None


def get_balance_sheet(symbol: str) -> Optional[Dict[str, Any]]:
    """Get latest balance sheet."""
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    data = _make_request(f"balance-sheet-statement/{clean_symbol}.NS")
    if data and isinstance(data, list) and len(data) > 0:
        stmt = data[0]
        return {
            "total_assets": stmt.get("totalAssets"),
            "total_liabilities": stmt.get("totalLiabilities"),
            "total_equity": stmt.get("totalStockholdersEquity"),
            "cash_and_equivalents": stmt.get("cashAndCashEquivalents"),
            "total_debt": stmt.get("totalDebt"),
            "net_debt": stmt.get("totalDebt") - stmt.get("cashAndCashEquivalents") if stmt.get("totalDebt") and stmt.get("cashAndCashEquivalents") else None,
        }
    return None


def get_cash_flow(symbol: str) -> Optional[Dict[str, Any]]:
    """Get latest cash flow statement."""
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    data = _make_request(f"cash-flow-statement/{clean_symbol}.NS")
    if data and isinstance(data, list) and len(data) > 0:
        stmt = data[0]
        return {
            "operating_cash_flow": stmt.get("operatingCashFlow"),
            "investing_cash_flow": stmt.get("investingCashFlow"),
            "financing_cash_flow": stmt.get("financingCashFlow"),
            "free_cash_flow": stmt.get("freeCashFlow"),
            "capital_expenditure": stmt.get("capitalExpenditure"),
        }
    return None


def get_analyst_ratings(symbol: str) -> Optional[Dict[str, Any]]:
    """Get analyst ratings and price targets."""
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
    
    data = _make_request(f"analyst-stock-recommendations/{clean_symbol}.NS")
    if data and isinstance(data, list) and len(data) > 0:
        latest = data[0]
        return {
            "buy": latest.get("strongBuy", 0) + latest.get("buy", 0),
            "hold": latest.get("hold", 0),
            "sell": latest.get("sell", 0) + latest.get("strongSell", 0),
            "consensus": latest.get("ratingRecommendation"),
        }
    return None


def get_stock_screener(
    exchange: str = "NSE",
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    pe_min: Optional[float] = None,
    pe_max: Optional[float] = None,
    roe_min: Optional[float] = None,
    dividend_yield_min: Optional[float] = None,
    volume_min: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Screen stocks based on fundamental criteria.
    
    Args:
        exchange: "NSE" or "BSE"
        market_cap_min: Minimum market cap in INR
        market_cap_max: Maximum market cap in INR
        pe_min: Minimum P/E ratio
        pe_max: Maximum P/E ratio
        roe_min: Minimum ROE percentage
        dividend_yield_min: Minimum dividend yield percentage
        volume_min: Minimum average volume
        limit: Maximum results to return
    
    Returns:
        List of stocks matching criteria
    """
    # Build query parameters
    params = {"limit": limit}
    
    # Note: FMP's screener API may have different parameter names
    # This is a simplified implementation
    results = []
    
    # FMP doesn't have direct INR screening, so we fetch and filter
    all_stocks = _make_request("stock-screener", {"limit": 500})
    
    if not all_stocks:
        return []
    
    for stock in all_stocks:
        # Filter by exchange (symbol suffix)
        if exchange == "NSE" and not stock.get("symbol", "").endswith(".NS"):
            continue
        if exchange == "BSE" and not stock.get("symbol", "").endswith(".BO"):
            continue
        
        # Apply filters
        if market_cap_min and stock.get("marketCap", 0) < market_cap_min:
            continue
        if market_cap_max and stock.get("marketCap", float('inf')) > market_cap_max:
            continue
        if pe_min and stock.get("pe", 0) < pe_min:
            continue
        if pe_max and stock.get("pe", float('inf')) > pe_max:
            continue
        if roe_min and stock.get("roe", 0) < roe_min:
            continue
        if dividend_yield_min and stock.get("dividendYield", 0) < dividend_yield_min:
            continue
        if volume_min and stock.get("volume", 0) < volume_min:
            continue
        
        results.append({
            "symbol": stock.get("symbol"),
            "name": stock.get("name"),
            "price": stock.get("price"),
            "market_cap": stock.get("marketCap"),
            "pe_ratio": stock.get("pe"),
            "roe": stock.get("roe"),
            "dividend_yield": stock.get("dividendYield"),
            "volume": stock.get("volume"),
        })
    
    return results[:limit]


def search_symbol(query: str) -> List[Dict[str, str]]:
    """Search for stocks by symbol or name."""
    data = _make_request("search", {"query": query, "limit": 20, "exchange": "NSE"})
    
    if not data:
        return []
    
    return [
        {
            "symbol": item.get("symbol"),
            "name": item.get("name"),
            "exchange": item.get("exchangeSymbol"),
        }
        for item in data
    ]
