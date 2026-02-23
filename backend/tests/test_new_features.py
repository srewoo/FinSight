"""
Backend Tests for NEW Features in AI Stock Assistant
Tests: AI Auto-Recommendations, Chart Image Analysis, Support/Resistance, ADX, NSE/BSE
"""
import pytest
import requests
import os
import base64

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')


class TestAIAutoRecommendations:
    """Tests for GET /api/ai/auto-recommendations - NEW FEATURE"""
    
    def test_auto_recommendations_returns_data(self, api_client):
        # This endpoint analyzes 40+ stocks and takes 30-60 seconds
        print("\nTesting /api/ai/auto-recommendations (may take 30-60s)...")
        response = api_client.get(f"{BASE_URL}/api/ai/auto-recommendations", timeout=90)
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "buy_recommendations" in data
        assert "sell_recommendations" in data
        assert "hold_recommendations" in data
        
        # Validate summary structure
        summary = data["summary"]
        assert "stocks_analyzed" in summary
        assert "buy_signals" in summary
        assert "sell_signals" in summary
        assert "hold_signals" in summary
        assert "market_sentiment" in summary
        
        # Check that stocks were analyzed
        assert summary["stocks_analyzed"] > 0
        print(f"✓ Analyzed {summary['stocks_analyzed']} stocks")
        print(f"✓ Buy signals: {summary['buy_signals']}, Sell signals: {summary['sell_signals']}")
        print(f"✓ Market sentiment: {summary['market_sentiment']}")
        
        # Check sentiment is valid
        assert summary["market_sentiment"] in ["Bullish", "Bearish", "Neutral"]
    
    def test_auto_recommendations_buy_structure(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ai/auto-recommendations", timeout=90)
        assert response.status_code == 200
        
        data = response.json()
        buy_recs = data["buy_recommendations"]
        
        if len(buy_recs) > 0:
            rec = buy_recs[0]
            # Validate structure
            assert "symbol" in rec
            assert "name" in rec
            assert "sector" in rec
            assert "price" in rec
            assert "change_percent" in rec
            assert "signal" in rec
            assert rec["signal"] == "BUY"
            assert "confidence" in rec
            assert 1 <= rec["confidence"] <= 100
            assert "rsi" in rec
            assert "adx" in rec
            assert "macd_signal" in rec
            assert "support_resistance" in rec
            
            # Check support_resistance structure
            sr = rec["support_resistance"]
            assert "pivot" in sr
            assert "resistance" in sr
            assert "support" in sr
            assert "period_highs_lows" in sr
            
            print(f"✓ Buy recommendation structure validated for {rec['symbol']}")
        else:
            print("⚠ No buy recommendations in current market conditions")
    
    def test_auto_recommendations_sell_structure(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ai/auto-recommendations", timeout=90)
        assert response.status_code == 200
        
        data = response.json()
        sell_recs = data["sell_recommendations"]
        
        if len(sell_recs) > 0:
            rec = sell_recs[0]
            assert "signal" in rec
            assert rec["signal"] == "SELL"
            assert "confidence" in rec
            assert 1 <= rec["confidence"] <= 100
            print(f"✓ Sell recommendation structure validated for {rec['symbol']}")
        else:
            print("⚠ No sell recommendations in current market conditions")


class TestChartImageAnalysis:
    """Tests for POST /api/ai/analyze-chart-image - NEW FEATURE"""
    
    def test_analyze_chart_image_with_sample_base64(self, api_client):
        # Create a minimal 1x1 pixel PNG as base64
        # This is a valid PNG header + IDAT chunk for a 1x1 white pixel
        sample_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        print("\nTesting /api/ai/analyze-chart-image with sample image...")
        response = api_client.post(
            f"{BASE_URL}/api/ai/analyze-chart-image",
            json={
                "image_base64": sample_base64,
                "context": "Test candlestick chart"
            },
            timeout=30
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis" in data
        assert "timestamp" in data
        
        # Validate analysis structure
        analysis = data["analysis"]
        assert "prediction" in analysis
        assert analysis["prediction"] in ["UP", "DOWN", "SIDEWAYS"]
        assert "confidence" in analysis
        assert 1 <= analysis["confidence"] <= 100
        assert "trend" in analysis
        assert "patterns_identified" in analysis
        assert "support_levels" in analysis
        assert "resistance_levels" in analysis
        assert "summary" in analysis
        assert "recommendation" in analysis
        assert analysis["recommendation"] in ["BUY", "SELL", "HOLD"]
        assert "key_observations" in analysis
        
        print(f"✓ Chart analysis result: {analysis['prediction']} with {analysis['confidence']}% confidence")
        print(f"✓ Recommendation: {analysis['recommendation']}")
    
    def test_analyze_chart_image_missing_data(self, api_client):
        # Test with missing image
        response = api_client.post(
            f"{BASE_URL}/api/ai/analyze-chart-image",
            json={"image_base64": ""},
            timeout=30
        )
        assert response.status_code == 400
        print("✓ Correctly rejects empty image")


class TestSupportResistanceLevels:
    """Tests for Support/Resistance levels - NEW FEATURE"""
    
    def test_stock_quote_includes_support_resistance(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/RELIANCE.NS/quote")
        assert response.status_code == 200
        
        data = response.json()
        assert "support_resistance" in data
        
        sr = data["support_resistance"]
        assert "pivot" in sr
        assert sr["pivot"] is not None
        
        # Check resistance levels R1, R2, R3
        assert "resistance" in sr
        assert "r1" in sr["resistance"]
        assert "r2" in sr["resistance"]
        assert "r3" in sr["resistance"]
        
        # Check support levels S1, S2, S3
        assert "support" in sr
        assert "s1" in sr["support"]
        assert "s2" in sr["support"]
        assert "s3" in sr["support"]
        
        # Check period highs and lows
        assert "period_highs_lows" in sr
        phl = sr["period_highs_lows"]
        assert "high_1m" in phl
        assert "low_1m" in phl
        assert "high_6m" in phl
        assert "low_6m" in phl
        assert "high_52w" in phl
        assert "low_52w" in phl
        
        print(f"✓ Support/Resistance levels validated for RELIANCE.NS")
        print(f"  Pivot: {sr['pivot']}, R1: {sr['resistance']['r1']}, S1: {sr['support']['s1']}")
    
    def test_technicals_includes_support_resistance(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/INFY.NS/technicals")
        assert response.status_code == 200
        
        data = response.json()
        assert "support_resistance" in data
        
        sr = data["support_resistance"]
        assert "pivot" in sr
        assert "resistance" in sr
        assert "support" in sr
        print(f"✓ Technicals endpoint includes support_resistance")


class TestADXIndicator:
    """Tests for ADX indicator - NEW FEATURE"""
    
    def test_technicals_includes_adx(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/TCS.NS/technicals")
        assert response.status_code == 200
        
        data = response.json()
        assert "technicals" in data
        
        tech = data["technicals"]
        assert "adx" in tech
        
        # ADX value should be between 0 and 100 if present
        if tech["adx"] is not None:
            assert 0 <= tech["adx"] <= 100
            print(f"✓ ADX indicator present: {tech['adx']}")
        else:
            print("⚠ ADX is None (may need more data)")
    
    def test_adx_in_auto_recommendations(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ai/auto-recommendations", timeout=90)
        assert response.status_code == 200
        
        data = response.json()
        buy_recs = data["buy_recommendations"]
        
        if len(buy_recs) > 0:
            rec = buy_recs[0]
            assert "adx" in rec
            print(f"✓ ADX included in auto-recommendations: {rec['adx']}")


class TestNSEBSESupport:
    """Tests for NSE and BSE exchange support - ENHANCED FEATURE"""
    
    def test_search_returns_both_nse_and_bse(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/search?q=RELIANCE")
        assert response.status_code == 200
        
        data = response.json()
        results = data["results"]
        
        # Check if both NSE and BSE versions are present
        exchanges = [r["exchange"] for r in results]
        assert "NSE" in exchanges
        assert "BSE" in exchanges
        
        # Check symbols
        symbols = [r["symbol"] for r in results]
        nse_present = any(".NS" in sym for sym in symbols)
        bse_present = any(".BO" in sym for sym in symbols)
        
        assert nse_present, "NSE symbol (.NS) not found"
        assert bse_present, "BSE symbol (.BO) not found"
        
        print(f"✓ Search returns both NSE and BSE results")
        print(f"  NSE symbols: {[s for s in symbols if '.NS' in s]}")
        print(f"  BSE symbols: {[s for s in symbols if '.BO' in s]}")
    
    def test_bse_stock_quote(self, api_client):
        # Test a BSE stock quote
        response = api_client.get(f"{BASE_URL}/api/stocks/RELIANCE.BO/quote")
        assert response.status_code == 200
        
        data = response.json()
        assert "symbol" in data
        assert data["symbol"] == "RELIANCE.BO"
        assert "price" in data
        assert data["price"] is not None
        
        print(f"✓ BSE stock quote working: RELIANCE.BO at ₹{data['price']}")
    
    def test_bse_stock_technicals(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/stocks/TCS.BO/technicals")
        assert response.status_code == 200
        
        data = response.json()
        assert "technicals" in data
        assert "support_resistance" in data
        
        print(f"✓ BSE stock technicals working for TCS.BO")
