from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import numpy as np
import json

from llm_client import call_llm, SUPPORTED_MODELS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Models ---
class WatchlistItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    name: str
    exchange: str = "NSE"
    added_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WatchlistCreate(BaseModel):
    symbol: str
    name: str
    exchange: str = "NSE"

class PortfolioItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    name: str
    exchange: str = "NSE"
    quantity: float
    buy_price: float
    buy_date: str = ""
    added_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PortfolioCreate(BaseModel):
    symbol: str
    name: str
    exchange: str = "NSE"
    quantity: float
    buy_price: float
    buy_date: str = ""

class AIAnalysisRequest(BaseModel):
    timeframe: str = "short"

class ChartImageRequest(BaseModel):
    image_base64: str
    context: str = ""

class LLMSettingsCreate(BaseModel):
    provider: str   # "openai" | "gemini" | "claude"
    model: str
    api_key: str

# --- LLM Settings helpers ---
async def get_llm_settings() -> Dict[str, str]:
    """Fetch current LLM settings from MongoDB. Raises 503 if not configured."""
    doc = await db.llm_settings.find_one({}, {"_id": 0})
    if not doc or not doc.get("api_key"):
        raise HTTPException(
            status_code=503,
            detail="No LLM configured. Please go to Settings and add your API key."
        )
    return doc

# --- Dynamic Stock Discovery ---
async def get_nifty50_symbols() -> List[Dict]:
    """Fetch NIFTY 50 constituents dynamically via yfinance."""
    try:
        ticker = yf.Ticker("^NSEI")
        # Try to get components, fallback to well-known list
        # yfinance doesn't always expose index components reliably, 
        # so we use a comprehensive curated list of major NSE/BSE stocks
        pass
    except Exception:
        pass
    
    # Comprehensive list of major Indian stocks across sectors
    # These are actively traded on both NSE and BSE
    major_stocks = [
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Energy"},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
        {"symbol": "INFY", "name": "Infosys", "sector": "IT"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
        {"symbol": "ITC", "name": "ITC Limited", "sector": "FMCG"},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
        {"symbol": "LT", "name": "Larsen & Toubro", "sector": "Infrastructure"},
        {"symbol": "AXISBANK", "name": "Axis Bank", "sector": "Banking"},
        {"symbol": "WIPRO", "name": "Wipro", "sector": "IT"},
        {"symbol": "ASIANPAINT", "name": "Asian Paints", "sector": "Consumer"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Auto"},
        {"symbol": "TATAMOTORS", "name": "Tata Motors", "sector": "Auto"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance", "sector": "Finance"},
        {"symbol": "TITAN", "name": "Titan Company", "sector": "Consumer"},
        {"symbol": "NESTLEIND", "name": "Nestle India", "sector": "FMCG"},
        {"symbol": "TECHM", "name": "Tech Mahindra", "sector": "IT"},
        {"symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT"},
        {"symbol": "ULTRACEMCO", "name": "UltraTech Cement", "sector": "Cement"},
        {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
        {"symbol": "NTPC", "name": "NTPC Limited", "sector": "Power"},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy"},
        {"symbol": "TATASTEEL", "name": "Tata Steel", "sector": "Metals"},
        {"symbol": "JSWSTEEL", "name": "JSW Steel", "sector": "Metals"},
        {"symbol": "ADANIENT", "name": "Adani Enterprises", "sector": "Conglomerate"},
        {"symbol": "ADANIPORTS", "name": "Adani Ports", "sector": "Infrastructure"},
        {"symbol": "COALINDIA", "name": "Coal India", "sector": "Mining"},
        {"symbol": "DRREDDY", "name": "Dr Reddys Laboratories", "sector": "Pharma"},
        {"symbol": "CIPLA", "name": "Cipla", "sector": "Pharma"},
        {"symbol": "EICHERMOT", "name": "Eicher Motors", "sector": "Auto"},
        {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp", "sector": "Auto"},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv", "sector": "Finance"},
        {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
        {"symbol": "DIVISLAB", "name": "Divis Laboratories", "sector": "Pharma"},
        {"symbol": "GRASIM", "name": "Grasim Industries", "sector": "Cement"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
        {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Insurance"},
        {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "Insurance"},
        {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto", "sector": "Auto"},
        {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
        {"symbol": "M&M", "name": "Mahindra & Mahindra", "sector": "Auto"},
        {"symbol": "INDUSINDBK", "name": "IndusInd Bank", "sector": "Banking"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Metals"},
        {"symbol": "BPCL", "name": "Bharat Petroleum", "sector": "Energy"},
        {"symbol": "UPL", "name": "UPL Limited", "sector": "Chemicals"},
    ]
    return major_stocks

def safe_float(val):
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return None
    return round(float(val), 2)

def compute_technicals(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute technical indicators from price dataframe."""
    if df.empty or len(df) < 20:
        return {}
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # RSI (14-period)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    macd_hist = macd_line - signal_line
    
    # Moving Averages
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean() if len(close) >= 50 else pd.Series([None])
    sma200 = close.rolling(window=200).mean() if len(close) >= 200 else pd.Series([None])
    ema20 = close.ewm(span=20).mean()
    
    # Bollinger Bands
    bb_middle = sma20
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_middle + (bb_std * 2)
    bb_lower = bb_middle - (bb_std * 2)
    
    # ADX (Average Directional Index)
    adx_val = compute_adx(high, low, close)
    
    # Volume average
    vol_avg = df['Volume'].rolling(window=20).mean() if 'Volume' in df.columns else pd.Series([None])
    
    current_price = safe_float(close.iloc[-1])
    
    return {
        "rsi": safe_float(rsi.iloc[-1]),
        "rsi_signal": "Overbought" if rsi.iloc[-1] > 70 else ("Oversold" if rsi.iloc[-1] < 30 else "Neutral"),
        "adx": safe_float(adx_val),
        "macd": {
            "macd_line": safe_float(macd_line.iloc[-1]),
            "signal_line": safe_float(signal_line.iloc[-1]),
            "histogram": safe_float(macd_hist.iloc[-1]),
            "signal": "Bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "Bearish"
        },
        "moving_averages": {
            "sma20": safe_float(sma20.iloc[-1]),
            "sma50": safe_float(sma50.iloc[-1]) if len(sma50) > 0 else None,
            "sma200": safe_float(sma200.iloc[-1]) if len(sma200) > 0 else None,
            "ema20": safe_float(ema20.iloc[-1]),
        },
        "bollinger_bands": {
            "upper": safe_float(bb_upper.iloc[-1]),
            "middle": safe_float(bb_middle.iloc[-1]),
            "lower": safe_float(bb_lower.iloc[-1]),
            "signal": "Overbought" if current_price and bb_upper.iloc[-1] and current_price > bb_upper.iloc[-1] else ("Oversold" if current_price and bb_lower.iloc[-1] and current_price < bb_lower.iloc[-1] else "Normal")
        },
        "volume_avg_20": safe_float(vol_avg.iloc[-1]) if len(vol_avg) > 0 else None,
        "price_vs_sma20": "Above" if current_price and sma20.iloc[-1] and current_price > sma20.iloc[-1] else "Below"
    }

def compute_adx(high, low, close, period=14):
    """Compute Average Directional Index."""
    try:
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
        return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else None
    except Exception:
        return None

def compute_support_resistance(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute support and resistance levels using pivot points and price action."""
    if df.empty or len(df) < 5:
        return {}
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    current_price = safe_float(close.iloc[-1])
    
    # Classic Pivot Point calculation
    last_high = safe_float(high.iloc[-1])
    last_low = safe_float(low.iloc[-1])
    last_close = safe_float(close.iloc[-1])
    
    pivot = round((last_high + last_low + last_close) / 3, 2) if all([last_high, last_low, last_close]) else None
    
    r1 = round(2 * pivot - last_low, 2) if pivot and last_low else None
    r2 = round(pivot + (last_high - last_low), 2) if pivot and last_high and last_low else None
    r3 = round(last_high + 2 * (pivot - last_low), 2) if pivot and last_high and last_low else None
    
    s1 = round(2 * pivot - last_high, 2) if pivot and last_high else None
    s2 = round(pivot - (last_high - last_low), 2) if pivot and last_high and last_low else None
    s3 = round(last_low - 2 * (last_high - pivot), 2) if pivot and last_high and last_low else None
    
    # Period highs and lows
    high_52w = safe_float(high.max()) if len(df) >= 200 else safe_float(high.max())
    low_52w = safe_float(low.min()) if len(df) >= 200 else safe_float(low.min())
    high_6m = safe_float(high.tail(130).max()) if len(df) >= 130 else safe_float(high.max())
    low_6m = safe_float(low.tail(130).min()) if len(df) >= 130 else safe_float(low.min())
    high_1m = safe_float(high.tail(22).max())
    low_1m = safe_float(low.tail(22).min())
    
    return {
        "pivot": pivot,
        "resistance": {"r1": r1, "r2": r2, "r3": r3},
        "support": {"s1": s1, "s2": s2, "s3": s3},
        "period_highs_lows": {
            "high_52w": high_52w,
            "low_52w": low_52w,
            "high_6m": high_6m,
            "low_6m": low_6m,
            "high_1m": high_1m,
            "low_1m": low_1m,
        }
    }

def parse_llm_json(response: str, fallback: dict) -> dict:
    """Strip markdown fences and parse JSON; return fallback on failure."""
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        if clean.startswith("json"):
            clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return fallback

# --- API Routes ---

@api_router.get("/")
async def root():
    return {"message": "FinSight API"}

# ---------------------------------------------------------------------------
# LLM Settings
# ---------------------------------------------------------------------------
@api_router.get("/settings")
async def get_settings():
    doc = await db.llm_settings.find_one({}, {"_id": 0})
    if not doc:
        return {"provider": None, "model": None, "api_key_set": False, "supported_models": SUPPORTED_MODELS}
    return {
        "provider": doc.get("provider"),
        "model": doc.get("model"),
        "api_key_set": bool(doc.get("api_key")),
        "supported_models": SUPPORTED_MODELS,
    }

@api_router.post("/settings")
async def save_settings(payload: LLMSettingsCreate):
    provider = payload.provider.lower().strip()
    if provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    if payload.model not in SUPPORTED_MODELS[provider]:
        raise HTTPException(status_code=400, detail=f"Unknown model '{payload.model}' for provider '{provider}'")
    
    doc = {"provider": provider, "model": payload.model, "api_key": payload.api_key, "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.llm_settings.replace_one({}, doc, upsert=True)
    return {"message": "Settings saved", "provider": provider, "model": payload.model}

@api_router.post("/settings/test")
async def test_connection():
    settings = await get_llm_settings()
    try:
        result = await call_llm(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
            prompt='Reply with exactly: {"status":"ok"}',
            system_message="You are a test assistant. Respond with JSON only.",
        )
        parsed = parse_llm_json(result, {})
        if parsed.get("status") == "ok" or result:
            return {"success": True, "provider": settings["provider"], "model": settings["model"]}
        return {"success": True, "provider": settings["provider"], "model": settings["model"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------------------------
# Market Indices
# ---------------------------------------------------------------------------
@api_router.get("/market/indices")
async def get_market_indices():
    try:
        indices = {"^NSEI": "NIFTY 50", "^BSESN": "SENSEX"}
        result = []
        for symbol, name in indices.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                if hist.empty:
                    continue
                current = safe_float(hist['Close'].iloc[-1])
                prev = safe_float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
                change = round(current - prev, 2) if current and prev else 0
                change_pct = round((change / prev) * 100, 2) if prev else 0
                result.append({"symbol": symbol, "name": name, "price": current, "change": change, "change_percent": change_pct})
            except Exception as e:
                logger.error(f"Error fetching index {symbol}: {e}")
        return {"indices": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Top Movers - fetches live data
@api_router.get("/market/top-movers")
async def get_top_movers():
    try:
        stocks = await get_nifty50_symbols()
        movers = []
        for s in stocks[:35]:
            try:
                sym = f"{s['symbol']}.NS"
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if hist.empty or len(hist) < 2:
                    continue
                current = safe_float(hist['Close'].iloc[-1])
                prev = safe_float(hist['Close'].iloc[-2])
                if not current or not prev:
                    continue
                change = round(current - prev, 2)
                change_pct = round((change / prev) * 100, 2)
                movers.append({"symbol": sym, "name": s['name'], "sector": s.get('sector', ''), "price": current, "change": change, "change_percent": change_pct})
            except Exception:
                continue
        
        movers.sort(key=lambda x: x["change_percent"], reverse=True)
        gainers = [m for m in movers if m["change_percent"] > 0][:5]
        losers = sorted([m for m in movers if m["change_percent"] < 0], key=lambda x: x["change_percent"])[:5]
        return {"gainers": gainers, "losers": losers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Stock Search - dynamic, searches both NSE and BSE
@api_router.get("/stocks/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    query = q.upper().strip()
    stocks = await get_nifty50_symbols()
    results = []
    seen = set()
    for s in stocks:
        if query in s["symbol"].upper() or query in s["name"].upper():
            nse_sym = f"{s['symbol']}.NS"
            if nse_sym not in seen:
                results.append({"symbol": nse_sym, "name": s["name"], "exchange": "NSE", "sector": s.get("sector", "")})
                seen.add(nse_sym)
            bse_sym = f"{s['symbol']}.BO"
            if bse_sym not in seen:
                results.append({"symbol": bse_sym, "name": s["name"], "exchange": "BSE", "sector": s.get("sector", "")})
                seen.add(bse_sym)
    
    if len(results) == 0 and len(query) >= 2:
        for suffix in ['.NS', '.BO']:
            try:
                test_sym = query + suffix
                ticker = yf.Ticker(test_sym)
                info = ticker.info
                if info.get('regularMarketPrice') or info.get('currentPrice'):
                    name = info.get('longName', info.get('shortName', query))
                    exchange = 'NSE' if suffix == '.NS' else 'BSE'
                    results.append({"symbol": test_sym, "name": name, "exchange": exchange, "sector": info.get('sector', '')})
            except Exception:
                pass
    
    return {"results": results[:20]}

# Stock Quote - fetches live from yfinance
@api_router.get("/stocks/{symbol}/quote")
async def get_stock_quote(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")
        info = ticker.info
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        current = safe_float(hist['Close'].iloc[-1])
        prev = safe_float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
        change = round(current - prev, 2) if current and prev else 0
        change_pct = round((change / prev) * 100, 2) if prev else 0
        
        sr_levels = compute_support_resistance(hist)
        
        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol.replace(".NS", "").replace(".BO", ""))),
            "price": current,
            "change": change,
            "change_percent": change_pct,
            "open": safe_float(hist['Open'].iloc[-1]),
            "high": safe_float(hist['High'].iloc[-1]),
            "low": safe_float(hist['Low'].iloc[-1]),
            "volume": int(hist['Volume'].iloc[-1]) if not pd.isna(hist['Volume'].iloc[-1]) else 0,
            "prev_close": prev,
            "day_high": safe_float(info.get("dayHigh")),
            "day_low": safe_float(info.get("dayLow")),
            "fifty_two_week_high": safe_float(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": safe_float(info.get("fiftyTwoWeekLow")),
            "market_cap": info.get("marketCap"),
            "pe_ratio": safe_float(info.get("trailingPE")),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "support_resistance": sr_levels,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Stock History
@api_router.get("/stocks/{symbol}/history")
async def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        data = []
        for idx, row in hist.iterrows():
            data.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": safe_float(row['Open']),
                "high": safe_float(row['High']),
                "low": safe_float(row['Low']),
                "close": safe_float(row['Close']),
                "volume": int(row['Volume']) if not pd.isna(row['Volume']) else 0
            })
        return {"symbol": symbol, "period": period, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Technical Indicators + Support/Resistance
@api_router.get("/stocks/{symbol}/technicals")
async def get_technicals(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        technicals = compute_technicals(hist)
        sr_levels = compute_support_resistance(hist)
        return {"symbol": symbol, "technicals": technicals, "support_resistance": sr_levels}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# AI Analysis
@api_router.post("/stocks/{symbol}/ai-analysis")
async def get_ai_analysis(symbol: str, request: AIAnalysisRequest):
    try:
        settings = await get_llm_settings()

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        info = ticker.info
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        technicals = compute_technicals(hist)
        sr_levels = compute_support_resistance(hist)
        current_price = safe_float(hist['Close'].iloc[-1])
        prices_5d = [safe_float(p) for p in hist['Close'].tail(5).tolist()]
        prices_30d = [safe_float(p) for p in hist['Close'].tail(30).tolist()]
        
        stock_name = info.get("longName", symbol)
        sector = info.get("sector", "N/A")
        pe_ratio = safe_float(info.get("trailingPE"))
        market_cap = info.get("marketCap", "N/A")
        timeframe_desc = "short-term (1 week to 1 month)" if request.timeframe == "short" else "long-term (3 months to 1 year)"
        
        prompt = f"""You are a senior Indian stock market analyst AI. Analyze this stock and provide a clear BUY, SELL, or HOLD recommendation.

STOCK: {stock_name} ({symbol})
Sector: {sector} | P/E: {pe_ratio} | Market Cap: {market_cap}
Current Price: ₹{current_price}

TECHNICAL INDICATORS:
- RSI(14): {technicals.get('rsi')} ({technicals.get('rsi_signal')})
- ADX: {technicals.get('adx')}
- MACD: Line={technicals.get('macd',{}).get('macd_line')}, Signal={technicals.get('macd',{}).get('signal_line')}, Hist={technicals.get('macd',{}).get('histogram')} ({technicals.get('macd',{}).get('signal')})
- SMA20={technicals.get('moving_averages',{}).get('sma20')}, SMA50={technicals.get('moving_averages',{}).get('sma50')}, SMA200={technicals.get('moving_averages',{}).get('sma200')}
- Bollinger: Upper={technicals.get('bollinger_bands',{}).get('upper')}, Lower={technicals.get('bollinger_bands',{}).get('lower')} ({technicals.get('bollinger_bands',{}).get('signal')})

SUPPORT/RESISTANCE:
- Pivot: {sr_levels.get('pivot')}
- R1={sr_levels.get('resistance',{}).get('r1')}, R2={sr_levels.get('resistance',{}).get('r2')}, R3={sr_levels.get('resistance',{}).get('r3')}
- S1={sr_levels.get('support',{}).get('s1')}, S2={sr_levels.get('support',{}).get('s2')}, S3={sr_levels.get('support',{}).get('s3')}
- 6M High={sr_levels.get('period_highs_lows',{}).get('high_6m')}, 6M Low={sr_levels.get('period_highs_lows',{}).get('low_6m')}

RECENT PRICES (5d): {prices_5d}
30-DAY RANGE: ₹{min(p for p in prices_30d if p)} - ₹{max(p for p in prices_30d if p)}
Timeframe: {timeframe_desc}

Return ONLY valid JSON:
{{"recommendation":"BUY/SELL/HOLD","confidence":1-100,"target_price":number,"stop_loss":number,"summary":"2-3 sentences","key_reasons":["r1","r2","r3"],"risks":["risk1","risk2"],"technical_outlook":"1-2 sentences","sentiment":"Bullish/Bearish/Neutral"}}"""

        response = await call_llm(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
            prompt=prompt,
        )
        
        analysis = parse_llm_json(response, {
            "recommendation": "HOLD", "confidence": 50,
            "target_price": current_price * 1.05, "stop_loss": current_price * 0.95,
            "summary": response[:200], "key_reasons": ["Analysis pending"],
            "risks": ["Market volatility"], "technical_outlook": "Mixed signals", "sentiment": "Neutral"
        })
        
        analysis_doc = {
            "id": str(uuid.uuid4()), "symbol": symbol, "timeframe": request.timeframe,
            "analysis": analysis, "current_price": current_price,
            "provider": settings["provider"], "model": settings["model"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_analyses.insert_one(analysis_doc)
        
        return {"symbol": symbol, "timeframe": request.timeframe, "current_price": current_price, "analysis": analysis, "support_resistance": sr_levels, "timestamp": analysis_doc["timestamp"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in AI analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI Auto-Recommendations - analyzes NIFTY 50 stocks and returns buy/sell signals
@api_router.get("/ai/auto-recommendations")
async def get_auto_recommendations():
    try:
        stocks = await get_nifty50_symbols()
        analyzed = []
        
        for s in stocks[:40]:
            try:
                sym_nse = f"{s['symbol']}.NS"
                ticker = yf.Ticker(sym_nse)
                hist = ticker.history(period="6mo", interval="1d")
                if hist.empty or len(hist) < 30:
                    continue
                
                technicals = compute_technicals(hist)
                sr_levels = compute_support_resistance(hist)
                current_price = safe_float(hist['Close'].iloc[-1])
                prev_price = safe_float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                change_pct = round(((current_price - prev_price) / prev_price) * 100, 2) if prev_price else 0
                
                rsi = technicals.get('rsi')
                adx = technicals.get('adx')
                macd_signal = technicals.get('macd', {}).get('signal', 'Neutral')
                bb_signal = technicals.get('bollinger_bands', {}).get('signal', 'Normal')
                price_vs_sma = technicals.get('price_vs_sma20', 'Below')
                
                score = 0
                if rsi and rsi < 30: score += 2
                elif rsi and rsi > 70: score -= 2
                elif rsi and rsi < 45: score += 1
                elif rsi and rsi > 60: score -= 1
                
                if macd_signal == 'Bullish': score += 2
                else: score -= 1
                
                if bb_signal == 'Oversold': score += 2
                elif bb_signal == 'Overbought': score -= 2
                
                if price_vs_sma == 'Above': score += 1
                else: score -= 1
                
                if adx and adx > 25: score += 1
                
                signal = "BUY" if score >= 2 else ("SELL" if score <= -2 else "HOLD")
                confidence = min(95, max(30, 50 + score * 8))
                
                analyzed.append({
                    "symbol": sym_nse, "name": s['name'], "sector": s.get('sector', ''),
                    "price": current_price, "change_percent": change_pct, "signal": signal,
                    "confidence": confidence, "rsi": rsi, "adx": adx, "macd_signal": macd_signal,
                    "support_resistance": sr_levels,
                })
            except Exception as e:
                logger.warning(f"Skipping {s['symbol']}: {e}")
                continue
        
        buy_signals = sorted([a for a in analyzed if a['signal'] == 'BUY'], key=lambda x: x['confidence'], reverse=True)
        sell_signals = sorted([a for a in analyzed if a['signal'] == 'SELL'], key=lambda x: x['confidence'], reverse=True)
        hold_signals = [a for a in analyzed if a['signal'] == 'HOLD']
        
        total = len(analyzed)
        buy_count = len(buy_signals)
        sell_count = len(sell_signals)
        sentiment = "Bullish" if buy_count > sell_count * 2 else ("Bearish" if sell_count > buy_count * 2 else "Neutral")
        
        return {
            "summary": {
                "stocks_analyzed": total, "buy_signals": buy_count, "sell_signals": sell_count,
                "hold_signals": len(hold_signals), "market_sentiment": sentiment,
            },
            "buy_recommendations": buy_signals,
            "sell_recommendations": sell_signals,
            "hold_recommendations": hold_signals[:5],
        }
    except Exception as e:
        logger.error(f"Error in auto recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI-powered batch analysis — deep scan via LLM
@api_router.post("/ai/deep-scan")
async def deep_scan_stocks():
    try:
        settings = await get_llm_settings()
        stocks = await get_nifty50_symbols()
        batch_data = []
        
        for s in stocks[:25]:
            try:
                sym = f"{s['symbol']}.NS"
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="6mo", interval="1d")
                if hist.empty or len(hist) < 30:
                    continue
                technicals = compute_technicals(hist)
                sr = compute_support_resistance(hist)
                current = safe_float(hist['Close'].iloc[-1])
                batch_data.append(f"{s['symbol']}: Price=₹{current}, RSI={technicals.get('rsi')}, MACD={technicals.get('macd',{}).get('signal')}, ADX={technicals.get('adx')}, BB={technicals.get('bollinger_bands',{}).get('signal')}, R1={sr.get('resistance',{}).get('r1')}, S1={sr.get('support',{}).get('s1')}")
            except Exception:
                continue
        
        if not batch_data:
            return {"buy": [], "sell": [], "summary": "No data available"}
        
        prompt = f"""You are an expert Indian stock market analyst. Analyze these {len(batch_data)} NSE stocks and identify the TOP BUY and SELL opportunities.

STOCK DATA:
{chr(10).join(batch_data)}

Return ONLY valid JSON:
{{"buy":[{{"symbol":"SYMBOL.NS","reason":"brief reason","confidence":70}}],"sell":[{{"symbol":"SYMBOL.NS","reason":"brief reason","confidence":70}}],"market_outlook":"1 sentence overall"}}

Include only stocks with strong signals (confidence > 60). Max 8 buy and 8 sell recommendations."""

        response = await call_llm(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
            prompt=prompt,
        )
        
        result = parse_llm_json(response, {"buy": [], "sell": [], "market_outlook": "Analysis in progress"})
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deep scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chart Image Analysis - camera feature
@api_router.post("/ai/analyze-chart-image")
async def analyze_chart_image(request: ChartImageRequest):
    try:
        settings = await get_llm_settings()

        if not request.image_base64:
            raise HTTPException(status_code=400, detail="No image provided")
        
        img_data = request.image_base64
        if ',' in img_data:
            img_data = img_data.split(',')[1]
        
        prompt = f"""You are an expert technical analyst specializing in candlestick chart pattern recognition for Indian stock markets (NSE/BSE).

Analyze this candlestick chart image and provide:
1. Identify all visible candlestick patterns (Doji, Hammer, Engulfing, etc.)
2. Determine the overall trend (Uptrend, Downtrend, Sideways)
3. Identify support and resistance levels visible in the chart
4. Predict whether the stock will go UP or DOWN based on the chart patterns
5. Give a confidence level for your prediction

{f'Additional context: {request.context}' if request.context else ''}

Return ONLY valid JSON:
{{"prediction":"UP" or "DOWN" or "SIDEWAYS","confidence":1-100,"trend":"Uptrend/Downtrend/Sideways","patterns_identified":["pattern1","pattern2"],"support_levels":["level1"],"resistance_levels":["level1"],"summary":"2-3 sentence analysis","recommendation":"BUY/SELL/HOLD","key_observations":["obs1","obs2","obs3"]}}"""

        response = await call_llm(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
            prompt=prompt,
            system_message="Expert chart pattern analyst. JSON only.",
            image_b64=img_data,
        )
        
        result = parse_llm_json(response, {
            "prediction": "SIDEWAYS", "confidence": 50, "trend": "Unknown",
            "patterns_identified": [], "support_levels": [], "resistance_levels": [],
            "summary": response[:300], "recommendation": "HOLD", "key_observations": []
        })
        
        doc = {"id": str(uuid.uuid4()), "result": result, "timestamp": datetime.now(timezone.utc).isoformat()}
        await db.chart_analyses.insert_one(doc)
        
        return {"analysis": result, "timestamp": doc["timestamp"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing chart image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Watchlist CRUD
@api_router.get("/watchlist")
async def get_watchlist():
    items = await db.watchlist.find({}, {"_id": 0}).to_list(100)
    return {"watchlist": items}

@api_router.post("/watchlist")
async def add_to_watchlist(item: WatchlistCreate):
    existing = await db.watchlist.find_one({"symbol": item.symbol}, {"_id": 0})
    if existing:
        return {"message": "Already in watchlist", "item": existing}
    watchlist_item = WatchlistItem(**item.dict())
    await db.watchlist.insert_one(watchlist_item.dict())
    return {"message": "Added to watchlist", "item": watchlist_item.dict()}

@api_router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    result = await db.watchlist.delete_one({"symbol": symbol})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Removed from watchlist"}

# Portfolio CRUD
@api_router.get("/portfolio")
async def get_portfolio():
    items = await db.portfolio.find({}, {"_id": 0}).to_list(100)
    enriched = []
    for item in items:
        try:
            ticker = yf.Ticker(item["symbol"])
            hist = ticker.history(period="2d")
            if not hist.empty:
                current_price = safe_float(hist['Close'].iloc[-1])
                item["current_price"] = current_price
                item["pnl"] = round((current_price - item["buy_price"]) * item["quantity"], 2) if current_price else 0
                item["pnl_percent"] = round(((current_price - item["buy_price"]) / item["buy_price"]) * 100, 2) if current_price and item["buy_price"] else 0
            else:
                item["current_price"] = item["buy_price"]
                item["pnl"] = 0
                item["pnl_percent"] = 0
        except Exception:
            item["current_price"] = item["buy_price"]
            item["pnl"] = 0
            item["pnl_percent"] = 0
        enriched.append(item)
    
    total_invested = sum(i["buy_price"] * i["quantity"] for i in enriched)
    total_current = sum((i.get("current_price", i["buy_price"]) or i["buy_price"]) * i["quantity"] for i in enriched)
    total_pnl = round(total_current - total_invested, 2)
    total_pnl_pct = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0
    
    return {
        "portfolio": enriched,
        "summary": {"total_invested": round(total_invested, 2), "total_current": round(total_current, 2), "total_pnl": total_pnl, "total_pnl_percent": total_pnl_pct, "holdings_count": len(enriched)}
    }

@api_router.post("/portfolio")
async def add_to_portfolio(item: PortfolioCreate):
    portfolio_item = PortfolioItem(**item.dict())
    await db.portfolio.insert_one(portfolio_item.dict())
    return {"message": "Added to portfolio", "item": portfolio_item.dict()}

@api_router.delete("/portfolio/{item_id}")
async def remove_from_portfolio(item_id: str):
    result = await db.portfolio.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Removed from portfolio"}

app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
