"""
Backend API Tests for AI Stock Assistant
Tests: Market data, Stock search/quote/history/technicals, AI analysis, Watchlist, Portfolio
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')


class TestHealthCheck:
    """Basic health check"""
    
    def test_api_root(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestMarketEndpoints:
    """Market indices and top movers tests"""
    
    def test_get_market_indices(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/market/indices")
        assert response.status_code == 200
        
        data = response.json()
        assert "indices" in data
        assert len(data["indices"]) > 0
        
        # Verify NIFTY 50 and SENSEX are present
        symbols = [idx["symbol"] for idx in data["indices"]]
        assert "^NSEI" in symbols or "^BSESN" in symbols
        
        # Check data structure
        for idx in data["indices"]:
            assert "symbol" in idx
            assert "name" in idx
            assert "price" in idx
            assert "change" in idx
            assert "change_percent" in idx
            assert idx["price"] is not None
    
    def test_get_top_movers(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/market/top-movers")
        assert response.status_code == 200
        
        data = response.json()
        assert "gainers" in data
        assert "losers" in data
        
        # Check gainers structure
        if len(data["gainers"]) > 0:
            gainer = data["gainers"][0]
            assert "symbol" in gainer
            assert "name" in gainer
            assert "price" in gainer
            assert "change_percent" in gainer
            assert gainer["change_percent"] > 0  # Gainers should be positive
        
        # Check losers structure
        if len(data["losers"]) > 0:
            loser = data["losers"][0]
            assert "symbol" in loser
            assert "change_percent" in loser
            assert loser["change_percent"] < 0  # Losers should be negative


class TestStockEndpoints:
    """Stock search, quote, history, and technicals tests"""
    
    def test_search_stocks_reliance(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/search?q=RELIANCE")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
        
        # Verify RELIANCE is in results
        symbols = [s["symbol"] for s in data["results"]]
        assert any("RELIANCE" in sym for sym in symbols)
        
        # Check structure
        result = data["results"][0]
        assert "symbol" in result
        assert "name" in result
        assert "exchange" in result
    
    def test_search_stocks_tcs(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/search?q=TCS")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
    
    def test_search_stocks_infy(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/search?q=INFY")
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0
    
    def test_get_stock_quote_reliance(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/RELIANCE.NS/quote")
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert "name" in data
        assert "price" in data
        assert "change" in data
        assert "change_percent" in data
        assert "open" in data
        assert "high" in data
        assert "low" in data
        assert "volume" in data
        assert "market_cap" in data
        assert "sector" in data
        
        # Validate data types and values
        assert isinstance(data["price"], (int, float))
        assert data["price"] > 0
        assert isinstance(data["volume"], int)
    
    def test_get_stock_quote_tcs(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/TCS.NS/quote")
        assert response.status_code == 200
        
        data = response.json()
        assert data["symbol"] == "TCS.NS"
        assert data["price"] is not None
    
    def test_get_stock_history_1mo(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/RELIANCE.NS/history?period=1mo&interval=1d")
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert "data" in data
        assert len(data["data"]) > 0
        
        # Check data point structure
        point = data["data"][0]
        assert "date" in point
        assert "open" in point
        assert "high" in point
        assert "low" in point
        assert "close" in point
        assert "volume" in point
    
    def test_get_stock_history_1d(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/INFY.NS/history?period=1d&interval=15m")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
    
    def test_get_technicals(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/RELIANCE.NS/technicals")
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert "technicals" in data
        
        tech = data["technicals"]
        assert "rsi" in tech
        assert "rsi_signal" in tech
        assert "macd" in tech
        assert "moving_averages" in tech
        assert "bollinger_bands" in tech
        
        # Validate RSI
        if tech["rsi"] is not None:
            assert 0 <= tech["rsi"] <= 100
        
        # Validate MACD structure
        assert "macd_line" in tech["macd"]
        assert "signal_line" in tech["macd"]
        assert "histogram" in tech["macd"]
        assert "signal" in tech["macd"]
        
        # Validate moving averages
        assert "sma20" in tech["moving_averages"]
        assert "ema20" in tech["moving_averages"]
    
    def test_get_stock_not_found(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/INVALID99999.NS/quote")
        assert response.status_code == 404


class TestAIAnalysis:
    """AI analysis endpoint tests"""
    
    def test_ai_analysis_short_term(self, api_client):
        # AI analysis may take 10-15 seconds
        response = api_client.post(
            f"{BASE_URL}/api/stocks/RELIANCE.NS/ai-analysis",
            json={"timeframe": "short"},
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert "timeframe" in data
        assert "current_price" in data
        assert "analysis" in data
        
        # Validate analysis structure
        analysis = data["analysis"]
        assert "recommendation" in analysis
        assert analysis["recommendation"] in ["BUY", "SELL", "HOLD"]
        assert "confidence" in analysis
        assert 1 <= analysis["confidence"] <= 100
        assert "target_price" in analysis
        assert "stop_loss" in analysis
        assert "summary" in analysis
        assert "key_reasons" in analysis
        assert "risks" in analysis
        assert "technical_outlook" in analysis
        assert "sentiment" in analysis
        assert analysis["sentiment"] in ["Bullish", "Bearish", "Neutral"]
    
    def test_ai_analysis_long_term(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/stocks/INFY.NS/ai-analysis",
            json={"timeframe": "long"},
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["timeframe"] == "long"
        assert "analysis" in data


class TestWatchlist:
    """Watchlist CRUD tests"""
    
    def test_get_watchlist(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert response.status_code == 200
        
        data = response.json()
        assert "watchlist" in data
        assert isinstance(data["watchlist"], list)
    
    def test_add_to_watchlist_and_verify(self, api_client):
        # Add a test stock
        test_symbol = "TEST_RELIANCE.NS"
        add_response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={
                "symbol": test_symbol,
                "name": "Test Reliance Industries",
                "exchange": "NSE"
            }
        )
        assert add_response.status_code == 200
        
        add_data = add_response.json()
        assert "message" in add_data
        assert "item" in add_data
        assert add_data["item"]["symbol"] == test_symbol
        
        # Verify it's in the watchlist
        get_response = api_client.get(f"{BASE_URL}/api/watchlist")
        assert get_response.status_code == 200
        
        watchlist = get_response.json()["watchlist"]
        symbols = [w["symbol"] for w in watchlist]
        assert test_symbol in symbols
    
    def test_add_duplicate_to_watchlist(self, api_client):
        test_symbol = "TEST_TCS.NS"
        
        # Add first time
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={
                "symbol": test_symbol,
                "name": "Test TCS",
                "exchange": "NSE"
            }
        )
        
        # Add duplicate
        dup_response = api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={
                "symbol": test_symbol,
                "name": "Test TCS",
                "exchange": "NSE"
            }
        )
        assert dup_response.status_code == 200
        assert "Already in watchlist" in dup_response.json()["message"]
    
    def test_remove_from_watchlist(self, api_client):
        test_symbol = "TEST_INFY.NS"
        
        # Add first
        api_client.post(
            f"{BASE_URL}/api/watchlist",
            json={
                "symbol": test_symbol,
                "name": "Test Infosys",
                "exchange": "NSE"
            }
        )
        
        # Remove
        delete_response = api_client.delete(f"{BASE_URL}/api/watchlist/{test_symbol}")
        assert delete_response.status_code == 200
        
        # Verify removed
        get_response = api_client.get(f"{BASE_URL}/api/watchlist")
        watchlist = get_response.json()["watchlist"]
        symbols = [w["symbol"] for w in watchlist]
        assert test_symbol not in symbols
    
    def test_remove_nonexistent_from_watchlist(self, api_client):
        response = api_client.delete(f"{BASE_URL}/api/watchlist/NONEXISTENT999.NS")
        assert response.status_code == 404


class TestPortfolio:
    """Portfolio CRUD tests"""
    
    def test_get_portfolio(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/portfolio")
        assert response.status_code == 200
        
        data = response.json()
        assert "portfolio" in data
        assert "summary" in data
        assert isinstance(data["portfolio"], list)
        
        # Check summary structure
        summary = data["summary"]
        assert "total_invested" in summary
        assert "total_current" in summary
        assert "total_pnl" in summary
        assert "total_pnl_percent" in summary
        assert "holdings_count" in summary
    
    def test_add_to_portfolio_and_verify(self, api_client):
        # Add a test holding
        test_data = {
            "symbol": "TEST_RELIANCE_PORT.NS",
            "name": "Test Reliance Portfolio",
            "exchange": "NSE",
            "quantity": 10,
            "buy_price": 2500.50
        }
        
        add_response = api_client.post(
            f"{BASE_URL}/api/portfolio",
            json=test_data
        )
        assert add_response.status_code == 200
        
        add_data = add_response.json()
        assert "message" in add_data
        assert "item" in add_data
        assert add_data["item"]["symbol"] == test_data["symbol"]
        assert add_data["item"]["quantity"] == test_data["quantity"]
        assert add_data["item"]["buy_price"] == test_data["buy_price"]
        
        # Verify in portfolio
        get_response = api_client.get(f"{BASE_URL}/api/portfolio")
        assert get_response.status_code == 200
        
        portfolio = get_response.json()["portfolio"]
        symbols = [p["symbol"] for p in portfolio]
        assert test_data["symbol"] in symbols
        
        # Verify P&L fields are present
        for holding in portfolio:
            if holding["symbol"] == test_data["symbol"]:
                assert "current_price" in holding
                assert "pnl" in holding
                assert "pnl_percent" in holding
    
    def test_remove_from_portfolio(self, api_client):
        # Add a holding first
        test_data = {
            "symbol": "TEST_TCS_PORT.NS",
            "name": "Test TCS Portfolio",
            "exchange": "NSE",
            "quantity": 5,
            "buy_price": 3500.00
        }
        
        add_response = api_client.post(f"{BASE_URL}/api/portfolio", json=test_data)
        item_id = add_response.json()["item"]["id"]
        
        # Remove it
        delete_response = api_client.delete(f"{BASE_URL}/api/portfolio/{item_id}")
        assert delete_response.status_code == 200
        
        # Verify removed
        get_response = api_client.get(f"{BASE_URL}/api/portfolio")
        portfolio = get_response.json()["portfolio"]
        ids = [p["id"] for p in portfolio]
        assert item_id not in ids
    
    def test_remove_nonexistent_from_portfolio(self, api_client):
        response = api_client.delete(f"{BASE_URL}/api/portfolio/nonexistent-id-999")
        assert response.status_code == 404


# Cleanup test data after all tests
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    yield
    # Cleanup after all tests
    session = requests.Session()
    try:
        # Clean watchlist
        wl_response = session.get(f"{BASE_URL}/api/watchlist")
        if wl_response.status_code == 200:
            watchlist = wl_response.json()["watchlist"]
            for item in watchlist:
                if item["symbol"].startswith("TEST_"):
                    session.delete(f"{BASE_URL}/api/watchlist/{item['symbol']}")
        
        # Clean portfolio
        port_response = session.get(f"{BASE_URL}/api/portfolio")
        if port_response.status_code == 200:
            portfolio = port_response.json()["portfolio"]
            for item in portfolio:
                if item["symbol"].startswith("TEST_"):
                    session.delete(f"{BASE_URL}/api/portfolio/{item['id']}")
    except Exception as e:
        print(f"Cleanup error: {e}")
