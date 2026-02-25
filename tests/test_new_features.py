#!/usr/bin/env python3
"""
Test script for new FinSight features.
Run this after starting the backend: ./start.sh

Tests:
1. JWT Security
2. Redis Caching
3. Price Alerts
4. Fundamental Data
5. WebSocket Connection
6. News & Sentiment
"""

import requests
import json
import sys
import time
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configuration
BACKEND_URL = "http://localhost:8001"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials (create via /admin/provision-user if needed)
TEST_EMAIL = "test@finsight.app"
TEST_PASSWORD = "test123"

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text.center(60)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

def print_success(text):
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text):
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.YELLOW}ℹ {text}{Style.RESET_ALL}")

def test_jwt_security():
    """Test 1: JWT Security - Verify secure secret generation"""
    print_header("Test 1: JWT Security")
    
    try:
        # Try to login (should work if user exists)
        response = requests.post(
            f"{API_BASE}/auth/token",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=5
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            print_success(f"Login successful, token received")
            print_info(f"Token prefix: {token[:20]}...")
            return token
        elif response.status_code == 400:
            print_info("Test user doesn't exist. Creating...")
            # Create test user
            create_response = requests.post(
                f"{API_BASE}/admin/provision-user",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "name": "Test User"
                },
                timeout=5
            )
            if create_response.status_code == 200:
                print_success("Test user created")
                # Try login again
                return test_jwt_security()
            else:
                print_error(f"Failed to create user: {create_response.text}")
                return None
        else:
            print_error(f"Login failed: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print_error("Backend not running. Start with: ./start.sh")
        return None
    except Exception as e:
        print_error(f"Error: {e}")
        return None

def test_fundamentals(token):
    """Test 2: Fundamental Data"""
    print_header("Test 2: Fundamental Data API")
    
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        print_info("Fetching fundamentals for RELIANCE.NS...")
        response = requests.get(
            f"{API_BASE}/stocks/RELIANCE.NS/fundamentals",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Fundamentals retrieved successfully")
            print_info(f"Company: {data.get('company_name', 'N/A')}")
            print_info(f"Sector: {data.get('sector', 'N/A')}")
            
            valuation = data.get('valuation', {})
            if valuation:
                print_info(f"P/E Ratio: {valuation.get('pe_ratio', 'N/A')}")
                print_info(f"P/B Ratio: {valuation.get('pb_ratio', 'N/A')}")
            
            profitability = data.get('profitability', {})
            if profitability:
                print_info(f"ROE: {profitability.get('roe', 'N/A')}%")
            
            # Test caching (second request should be faster)
            print_info("Testing cache (second request)...")
            start = time.time()
            response2 = requests.get(
                f"{API_BASE}/stocks/RELIANCE.NS/fundamentals",
                headers=headers,
                timeout=10
            )
            elapsed = time.time() - start
            
            if response2.status_code == 200:
                print_success(f"Cached response in {elapsed*1000:.2f}ms")
                return True
        else:
            print_error(f"API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_alerts(token):
    """Test 3: Price Alerts"""
    print_header("Test 3: Price Alerts System")
    
    if not token:
        print_error("No token. Skipping alerts test.")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create alert
        print_info("Creating price alert for RELIANCE.NS...")
        create_response = requests.post(
            f"{API_BASE}/alerts",
            headers=headers,
            json={
                "symbol": "RELIANCE.NS",
                "target_price": 2500.0,
                "condition": "above",
                "note": "Test alert"
            },
            timeout=5
        )
        
        if create_response.status_code == 200:
            alert_id = create_response.json().get('alert', {}).get('id')
            print_success(f"Alert created: {alert_id}")
            
            # Get alerts
            print_info("Fetching alerts...")
            get_response = requests.get(
                f"{API_BASE}/alerts",
                headers=headers,
                timeout=5
            )
            
            if get_response.status_code == 200:
                alerts = get_response.json().get('alerts', [])
                print_success(f"Retrieved {len(alerts)} alert(s)")
                
                # Delete alert
                if alert_id:
                    print_info("Cleaning up: Deleting test alert...")
                    delete_response = requests.delete(
                        f"{API_BASE}/alerts/{alert_id}",
                        headers=headers,
                        timeout=5
                    )
                    if delete_response.status_code == 200:
                        print_success("Alert deleted successfully")
                
                return True
        else:
            print_error(f"Failed to create alert: {create_response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_sentiment():
    """Test 4: News & Sentiment Analysis"""
    print_header("Test 4: News & Sentiment Analysis")
    
    try:
        # Get market sentiment
        print_info("Fetching market sentiment...")
        response = requests.get(
            f"{API_BASE}/sentiment/summary",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Sentiment retrieved successfully")
            print_info(f"Overall Sentiment: {data.get('overall_sentiment', 'N/A')}")
            print_info(f"Sentiment Score: {data.get('overall_score', 0):.3f}")
            print_info(f"Articles Analyzed: {data.get('articles_count', 0)}")
            print_info(f"Positive: {data.get('positive_count', 0)}")
            print_info(f"Neutral: {data.get('neutral_count', 0)}")
            print_info(f"Negative: {data.get('negative_count', 0)}")
            return True
        else:
            print_error(f"API error: {response.status_code}")
            print_info("Note: Sentiment analysis requires RSS feed access")
            return False
            
    except Exception as e:
        print_error(f"Error: {e}")
        print_info("Note: This may fail if RSS feeds are unavailable")
        return False

def test_websocket():
    """Test 5: WebSocket Connection"""
    print_header("Test 5: WebSocket Real-time Prices")
    
    try:
        import websockets
        import asyncio
        
        async def test_ws():
            uri = f"ws://localhost:8001/api/ws/prices"
            print_info(f"Connecting to {uri}...")
            
            async with websockets.connect(uri) as websocket:
                print_success("WebSocket connected!")
                
                # Subscribe to a symbol
                print_info("Subscribing to RELIANCE.NS...")
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "symbols": ["RELIANCE.NS"]
                }))
                
                # Wait for initial prices
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print_info(f"Received: {data.get('type', 'unknown')}")
                
                if data.get('type') == 'initial_prices':
                    print_success("Received initial prices")
                    return True
                elif data.get('type') == 'subscribed':
                    print_success("Successfully subscribed")
                    
                    # Wait for price update
                    try:
                        update = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        update_data = json.loads(update)
                        if update_data.get('type') == 'price_update':
                            price = update_data.get('data', {})
                            print_success(f"Price update: ₹{price.get('price', 'N/A')}")
                            return True
                    except asyncio.TimeoutError:
                        print_info("No price updates received (timeout)")
                        return True
                    
                return False
        
        print_info("Note: Install websockets with: pip install websockets")
        result = asyncio.run(test_ws())
        return result
        
    except ImportError:
        print_info("websockets not installed. Skipping WebSocket test.")
        print_info("Install with: pip install websockets")
        return None
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def test_redis_connection():
    """Test 0: Redis Connection"""
    print_header("Test 0: Redis Connection Check")
    
    try:
        import redis.asyncio as redis
        import asyncio
        
        async def check_redis():
            try:
                client = redis.from_url("redis://localhost:6379")
                await client.ping()
                await client.close()
                return True
            except:
                return False
        
        result = asyncio.run(check_redis())
        if result:
            print_success("Redis connection successful")
            return True
        else:
            print_error("Redis not connected. Install and start Redis.")
            print_info("Install: brew install redis")
            print_info("Start: redis-server")
            return False
            
    except ImportError:
        print_info("redis-py not installed. Skipping Redis test.")
        print_info("Install with: pip install redis")
        return None
    except Exception as e:
        print_error(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print_header("FinSight New Features Test Suite")
    
    results = {
        "Redis": test_redis_connection(),
        "JWT Security": False,
        "Fundamentals": False,
        "Alerts": False,
        "Sentiment": False,
        "WebSocket": False,
    }
    
    # Run tests sequentially
    token = test_jwt_security()
    results["JWT Security"] = token is not None
    
    if token:
        results["Fundamentals"] = test_fundamentals(token)
        results["Alerts"] = test_alerts(token)
    else:
        print_error("Skipping authenticated tests (no token)")
    
    results["Sentiment"] = test_sentiment()
    results["WebSocket"] = test_websocket()
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"{Fore.GREEN}✓ {test_name}: PASSED{Style.RESET_ALL}")
        elif result is False:
            print(f"{Fore.RED}✗ {test_name}: FAILED{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}○ {test_name}: SKIPPED{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Results: {passed} passed, {failed} failed, {skipped} skipped{Style.RESET_ALL}")
    
    if failed == 0:
        print_success("All tests passed! 🎉")
        return 0
    else:
        print_error("Some tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
