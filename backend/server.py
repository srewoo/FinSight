from fastapi import FastAPI, APIRouter, HTTPException, Query, Depends, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import base64
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import numpy as np
import json
import re

from math_utils import compute_fibonacci_levels, compute_volume_profile_poc
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from llm_client import call_llm, SUPPORTED_MODELS
from auth import init_firebase, get_current_user, get_optional_user, AuthenticatedUser
from disclaimer import build_disclaimer_response_field, SEBI_DISCLAIMER_TEXT, SEBI_DISCLAIMER_SHORT, CURRENT_DISCLAIMER_VERSION

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
init_firebase()

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Rate Limiting ---
def get_rate_limit_key(request: Request) -> str:
    """Per-IP rate limiting (no auth)."""
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://"),
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- Input Validation ---
VALID_SYMBOL_PATTERN = re.compile(r'^[A-Za-z0-9&.\-\^]+$')
MAX_SYMBOL_LENGTH = 30
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

def sanitize_symbol(symbol: str) -> str:
    """Validate and sanitize stock symbol. Raises 400 if invalid."""
    symbol = symbol.strip()
    if not symbol or len(symbol) > MAX_SYMBOL_LENGTH:
        raise HTTPException(status_code=400, detail="Invalid symbol length")
    if not VALID_SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=400, detail="Symbol contains invalid characters")
    return symbol

def validate_chart_image(image_base64: str) -> str:
    """Validate chart image base64 data. Returns cleaned base64 string."""
    if not image_base64:
        raise HTTPException(status_code=400, detail="No image provided")
    img_data = image_base64
    if ',' in img_data:
        img_data = img_data.split(',')[1]
    try:
        decoded_size = len(base64.b64decode(img_data, validate=True))
        if decoded_size > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"Image too large ({decoded_size // 1024 // 1024}MB). Maximum is 10MB.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")
    return img_data

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

class UserPreferenceUpdate(BaseModel):
    preferred_provider: str
    preferred_model: Optional[str] = None

class ApiKeysUpdate(BaseModel):
    openai_key: Optional[str] = None
    gemini_key: Optional[str] = None
    claude_key: Optional[str] = None

class DisclaimerAcceptRequest(BaseModel):
    version: str = "1.0"

# --- LLM Configuration (user keys take priority over env keys) ---
def _mask_key(key: str) -> str:
    """Return last 4 chars masked as ****xxxx, or empty string."""
    if not key:
        return ""
    return f"****{key[-4:]}" if len(key) > 4 else "****"

def _safe_decrypt(ciphertext: str) -> str:
    """Decrypt a value using the server Fernet key; return empty string on failure."""
    if not ciphertext:
        return ""
    try:
        from cryptography.fernet import Fernet, InvalidToken
        key = os.environ.get("FERNET_KEY", "")
        if not key:
            return ""
        f = Fernet(key.encode() if isinstance(key, str) else key)
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ""

def get_llm_config(preferred_provider: str = None, preferred_model: str = None, user_profile: Dict = None) -> Dict[str, str]:
    """
    Get LLM configuration. User-stored API keys take priority over server env keys.
    Falls back to any available env key if the preferred provider has no key configured.
    """
    provider = (preferred_provider or os.environ.get("DEFAULT_LLM_PROVIDER", "gemini")).lower().strip()

    # Resolve user-stored (encrypted) API keys
    user_api_keys: Dict[str, str] = {}
    if user_profile and user_profile.get("api_keys"):
        stored = user_profile["api_keys"]
        for p in ("openai", "gemini", "claude"):
            enc = stored.get(f"{p}_enc", "")
            if enc:
                decrypted = _safe_decrypt(enc)
                if decrypted:
                    user_api_keys[p] = decrypted

    # Build key resolution order: user key → env key
    env_key_map = {
        "openai": os.environ.get("OPENAI_API_KEY", ""),
        "gemini": os.environ.get("GEMINI_API_KEY", ""),
        "claude": os.environ.get("CLAUDE_API_KEY", ""),
    }

    def resolve_key(p: str) -> str:
        return user_api_keys.get(p) or env_key_map.get(p, "")

    api_key = resolve_key(provider)
    if not api_key:
        # Try other providers in priority order
        for p in ("gemini", "openai", "claude"):
            if p != provider:
                fallback = resolve_key(p)
                if fallback:
                    provider = p
                    api_key = fallback
                    break

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="No AI API key configured. Add your API key in Settings → API Keys."
        )

    # Resolve model: user preference → env default → first supported model
    env_model_map = {
        "openai": os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
        "gemini": os.environ.get("GEMINI_MODEL", "gemini-3.0"),
        "claude": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
    }
    model = preferred_model or env_model_map.get(provider, SUPPORTED_MODELS[provider][0])
    # Guard: ensure model belongs to resolved provider
    if model not in SUPPORTED_MODELS.get(provider, []):
        model = SUPPORTED_MODELS[provider][0]

    return {"provider": provider, "model": model, "api_key": api_key}

# --- AI Quota System ---
async def check_and_increment_quota(user_id: str, feature: str = "ai_analysis") -> dict:
    """Check if user has remaining AI quota for today. Increment if available."""
    daily_limit = int(os.environ.get("AI_FREE_TIER_DAILY_LIMIT", "5"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    doc = await db.usage_tracking.find_one({"user_id": user_id, "date": today})

    count_field = f"{feature}_count"
    current_count = doc.get(count_field, 0) if doc else 0

    if current_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI analysis limit reached ({daily_limit}/{daily_limit}). Resets at midnight UTC."
        )

    await db.usage_tracking.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {count_field: 1}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    return {"used": current_count + 1, "limit": daily_limit, "remaining": daily_limit - current_count - 1}

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
# User Profile
# ---------------------------------------------------------------------------
@api_router.get("/user/profile")
async def get_user_profile(user: AuthenticatedUser = Depends(get_current_user)):
    existing = await db.users.find_one({"firebase_uid": user.uid}, {"_id": 0})
    if not existing:
        profile = {
            "firebase_uid": user.uid,
            "email": user.email,
            "display_name": user.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "preferred_provider": os.environ.get("DEFAULT_LLM_PROVIDER", "gemini"),
            "disclaimer_accepted_at": None,
            "disclaimer_version": None,
        }
        await db.users.insert_one(profile)
        profile.pop("_id", None)
        return profile
    return existing

# ---------------------------------------------------------------------------
# Settings — Provider/Model Preference + API Key Management
# ---------------------------------------------------------------------------
@api_router.get("/settings")
async def get_settings(user: AuthenticatedUser = Depends(get_current_user)):
    user_profile = await db.users.find_one({"firebase_uid": user.uid})
    preferred_provider = user_profile.get("preferred_provider", "gemini") if user_profile else "gemini"
    preferred_model = user_profile.get("preferred_model") if user_profile else None
    # Check which providers have keys available (user or env)
    stored = (user_profile or {}).get("api_keys", {})
    def _has_key(p: str) -> bool:
        enc = stored.get(f"{p}_enc", "")
        user_key = _safe_decrypt(enc) if enc else ""
        return bool(user_key or os.environ.get(f"{p.upper()}_API_KEY", ""))
    return {
        "preferred_provider": preferred_provider,
        "preferred_model": preferred_model,
        "supported_models": SUPPORTED_MODELS,
        "ai_available": any(_has_key(p) for p in ("openai", "gemini", "claude")),
        "provider_key_status": {p: _has_key(p) for p in ("openai", "gemini", "claude")},
    }

@api_router.post("/settings")
async def save_settings(payload: UserPreferenceUpdate, user: AuthenticatedUser = Depends(get_current_user)):
    provider = payload.preferred_provider.lower().strip()
    if provider not in SUPPORTED_MODELS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'")
    update_fields: Dict[str, Any] = {
        "preferred_provider": provider,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.preferred_model is not None:
        model = payload.preferred_model.strip()
        if model not in SUPPORTED_MODELS.get(provider, []):
            raise HTTPException(status_code=400, detail=f"Model '{model}' is not supported for provider '{provider}'")
        update_fields["preferred_model"] = model
    await db.users.update_one(
        {"firebase_uid": user.uid},
        {
            "$set": update_fields,
            "$setOnInsert": {
                "firebase_uid": user.uid,
                "email": user.email,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )
    return {"message": "Preferences saved", "preferred_provider": provider, "preferred_model": payload.preferred_model}

@api_router.get("/settings/api-keys")
async def get_api_keys(user: AuthenticatedUser = Depends(get_current_user)):
    """Return masked API keys so the UI can show which providers are configured."""
    user_profile = await db.users.find_one({"firebase_uid": user.uid})
    stored = (user_profile or {}).get("api_keys", {})
    result: Dict[str, str] = {}
    for provider in ("openai", "gemini", "claude"):
        enc = stored.get(f"{provider}_enc", "")
        plain = _safe_decrypt(enc) if enc else ""
        result[f"{provider}_key_masked"] = _mask_key(plain)
    return result

@api_router.post("/settings/api-keys")
async def save_api_keys(payload: ApiKeysUpdate, user: AuthenticatedUser = Depends(get_current_user)):
    """Encrypt and store per-provider API keys for this user."""
    fernet_key = os.environ.get("FERNET_KEY", "")
    if not fernet_key:
        raise HTTPException(status_code=503, detail="Server encryption not configured. Set FERNET_KEY in backend .env.")
    from cryptography.fernet import Fernet as _Fernet
    f = _Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)

    def _enc(val: Optional[str]) -> str:
        if not val or not val.strip():
            return ""
        return f.encrypt(val.strip().encode()).decode()

    api_keys_update: Dict[str, str] = {}
    if payload.openai_key is not None:
        api_keys_update["api_keys.openai_enc"] = _enc(payload.openai_key)
    if payload.gemini_key is not None:
        api_keys_update["api_keys.gemini_enc"] = _enc(payload.gemini_key)
    if payload.claude_key is not None:
        api_keys_update["api_keys.claude_enc"] = _enc(payload.claude_key)

    if not api_keys_update:
        raise HTTPException(status_code=400, detail="No keys provided")

    api_keys_update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"firebase_uid": user.uid},
        {
            "$set": api_keys_update,
            "$setOnInsert": {
                "firebase_uid": user.uid,
                "email": user.email,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )
    return {"message": "API keys saved successfully"}

# ---------------------------------------------------------------------------
# SEBI Disclaimer
# ---------------------------------------------------------------------------
@api_router.get("/disclaimer")
async def get_disclaimer():
    return {
        "version": CURRENT_DISCLAIMER_VERSION,
        "text": SEBI_DISCLAIMER_TEXT,
        "short_text": SEBI_DISCLAIMER_SHORT,
    }

@api_router.post("/user/accept-disclaimer")
async def accept_disclaimer(payload: DisclaimerAcceptRequest, user: AuthenticatedUser = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"firebase_uid": user.uid},
        {"$set": {"disclaimer_accepted_at": now, "disclaimer_version": payload.version, "updated_at": now}},
    )
    return {"accepted": True, "version": payload.version, "timestamp": now}

# ---------------------------------------------------------------------------
# AI Quota
# ---------------------------------------------------------------------------
@api_router.get("/user/quota")
async def get_user_quota(user: AuthenticatedUser = Depends(get_current_user)):
    daily_limit = int(os.environ.get("AI_FREE_TIER_DAILY_LIMIT", "5"))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = await db.usage_tracking.find_one({"user_id": user.uid, "date": today})
    used = doc.get("ai_analysis_count", 0) if doc else 0
    return {"used": used, "limit": daily_limit, "remaining": max(0, daily_limit - used)}

# ---------------------------------------------------------------------------
# Market Indices
# ---------------------------------------------------------------------------
@api_router.get("/market/indices")
@limiter.limit("60/minute")
async def get_market_indices(request: Request):
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
@limiter.limit("60/minute")
async def get_top_movers(request: Request):
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
@limiter.limit("60/minute")
async def get_stock_quote(request: Request, symbol: str):
    try:
        symbol = sanitize_symbol(symbol)
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
        fib_levels = compute_fibonacci_levels(hist)
        poc = compute_volume_profile_poc(hist)
        
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
@limiter.limit("60/minute")
async def get_stock_history(request: Request, symbol: str, period: str = "1mo", interval: str = "1d"):
    try:
        symbol = sanitize_symbol(symbol)
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
@limiter.limit("60/minute")
async def get_technicals(request: Request, symbol: str):
    try:
        symbol = sanitize_symbol(symbol)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y", interval="1d")
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        technicals = compute_technicals(hist)
        sr_levels = compute_support_resistance(hist)
        fib_levels = compute_fibonacci_levels(hist)
        poc = compute_volume_profile_poc(hist)
        return {"symbol": symbol, "technicals": technicals, "support_resistance": sr_levels}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# AI Analysis
@api_router.post("/stocks/{symbol}/ai-analysis")
@limiter.limit("10/minute")
async def get_ai_analysis(request: Request, symbol: str, body: AIAnalysisRequest, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        symbol = sanitize_symbol(symbol)
        await check_and_increment_quota(user.uid, "ai_analysis")
        user_profile = await db.users.find_one({"firebase_uid": user.uid})
        preferred_provider = user_profile.get("preferred_provider") if user_profile else None
        preferred_model = user_profile.get("preferred_model") if user_profile else None
        settings = get_llm_config(preferred_provider, preferred_model, user_profile)

        ticker = yf.Ticker(symbol)
        # Fetch multiple timeframes for confluence
        hist = ticker.history(period="1y", interval="1d")
        hist_1wk = ticker.history(period="2y", interval="1wk")
        hist_15m = ticker.history(period="5d", interval="15m")
        info = ticker.info
        
        if hist.empty:
            raise HTTPException(status_code=404, detail="No data found")
        
        technicals = compute_technicals(hist)
        technicals_1wk = compute_technicals(hist_1wk)
        technicals_15m = compute_technicals(hist_15m)
        
        sr_levels = compute_support_resistance(hist)
        fib_levels = compute_fibonacci_levels(hist)
        poc = compute_volume_profile_poc(hist)
        
        current_price = safe_float(hist['Close'].iloc[-1])
        prices_5d = [safe_float(p) for p in hist['Close'].tail(5).tolist()]
        prices_30d = [safe_float(p) for p in hist['Close'].tail(30).tolist()]
        
        stock_name = info.get("longName", symbol)
        sector = info.get("sector", "N/A")
        pe_ratio = safe_float(info.get("trailingPE"))
        market_cap = info.get("marketCap", "N/A")
        timeframe_desc = "short-term (1 week to 1 month)" if body.timeframe == "short" else "long-term (3 months to 1 year)"
        
        prompt = f"""You are a senior Indian stock market analyst AI. Analyze this stock and provide a clear BUY, SELL, or HOLD recommendation using Multi-Timeframe Confluence and Advanced Technicals.

STOCK: {stock_name} ({symbol})
Sector: {sector} | P/E: {pe_ratio} | Market Cap: {market_cap}
Current Price: ₹{current_price}

MULTI-TIMEFRAME CONFLUENCE:
- Daily (1D) Trend: MACD {technicals.get('macd',{}).get('signal')}, RSI {technicals.get('rsi')}
- Weekly (1W) Trend: MACD {technicals_1wk.get('macd',{}).get('signal')}, RSI {technicals_1wk.get('rsi')} 
- Intraday (15M) Trend: MACD {technicals_15m.get('macd',{}).get('signal')}, RSI {technicals_15m.get('rsi')}

DAILY TECHNICAL INDICATORS:
- RSI(14): {technicals.get('rsi')} ({technicals.get('rsi_signal')})
- ADX: {technicals.get('adx')}
- MACD: Line={technicals.get('macd',{}).get('macd_line')}, Signal={technicals.get('macd',{}).get('signal_line')}, Hist={technicals.get('macd',{}).get('histogram')}
- SMA20={technicals.get('moving_averages',{}).get('sma20')}, SMA50={technicals.get('moving_averages',{}).get('sma50')}, SMA200={technicals.get('moving_averages',{}).get('sma200')}
- Bollinger: {technicals.get('bollinger_bands',{}).get('signal')}

ADVANCED TECHNICALS (SUPPORT/RESISTANCE):
- Volume Profile Point of Control (POC): ₹{poc} (highest volume traded price)
- Fibonacci Levels: 0%={fib_levels.get('levels',{}).get('level_0')}, 23.6%={fib_levels.get('levels',{}).get('level_23_6')}, 38.2%={fib_levels.get('levels',{}).get('level_38_2')}, 50%={fib_levels.get('levels',{}).get('level_50_0')}, 61.8%={fib_levels.get('levels',{}).get('level_61_8')}
- Classic Pivot: {sr_levels.get('pivot')}, R1={sr_levels.get('resistance',{}).get('r1')}, S1={sr_levels.get('support',{}).get('s1')}

RECENT ACTIVITY:
- 5d Prices: {prices_5d}
- 30-day Range: ₹{min(p for p in prices_30d if p)} - ₹{max(p for p in prices_30d if p)}
- Analysis Timeframe: {timeframe_desc}

Return ONLY valid JSON:
{{"recommendation":"BUY/SELL/HOLD","confidence":1-100,"target_price":number,"stop_loss":number,"summary":"2-3 sentences","key_reasons":["r1","r2","r3"],"risks":["risk1","risk2"],"technical_outlook":"1-2 sentences","sentiment":"Bullish/Bearish/Neutral","multi_timeframe_sentiment":"Bullish/Bearish/Mixed"}}"""

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
            "id": str(uuid.uuid4()), "symbol": symbol, "timeframe": body.timeframe,
            "analysis": analysis, "current_price": current_price,
            "provider": settings["provider"], "model": settings["model"],
            "user_id": user.uid,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.ai_analyses.insert_one(analysis_doc)
        
        return {"symbol": symbol, "timeframe": body.timeframe, "current_price": current_price, "analysis": analysis, "support_resistance": sr_levels, "fib_levels": fib_levels, "poc": poc, "disclaimer": build_disclaimer_response_field(), "timestamp": analysis_doc["timestamp"]}
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
                fib_levels = compute_fibonacci_levels(hist)
                poc = compute_volume_profile_poc(hist)
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
            "disclaimer": build_disclaimer_response_field(),
        }
    except Exception as e:
        logger.error(f"Error in auto recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI-powered batch analysis — deep scan via LLM
@api_router.post("/ai/deep-scan")
@limiter.limit("5/minute")
async def deep_scan_stocks(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        await check_and_increment_quota(user.uid, "deep_scan")
        user_profile = await db.users.find_one({"firebase_uid": user.uid})
        preferred_provider = user_profile.get("preferred_provider") if user_profile else None
        preferred_model = user_profile.get("preferred_model") if user_profile else None
        settings = get_llm_config(preferred_provider, preferred_model, user_profile)
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
        result["disclaimer"] = build_disclaimer_response_field()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in deep scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chart Image Analysis - camera feature
@api_router.post("/ai/analyze-chart-image")
@limiter.limit("5/minute")
async def analyze_chart_image(request: Request, body: ChartImageRequest, user: AuthenticatedUser = Depends(get_current_user)):
    try:
        await check_and_increment_quota(user.uid, "chart_scan")
        user_profile = await db.users.find_one({"firebase_uid": user.uid})
        preferred_provider = user_profile.get("preferred_provider") if user_profile else None
        preferred_model = user_profile.get("preferred_model") if user_profile else None
        settings = get_llm_config(preferred_provider, preferred_model, user_profile)

        img_data = validate_chart_image(body.image_base64)
        
        prompt = f"""You are an expert technical analyst specializing in candlestick chart pattern recognition for Indian stock markets (NSE/BSE).

Analyze this candlestick chart image and provide:
1. Identify all visible candlestick patterns (Doji, Hammer, Engulfing, etc.)
2. Determine the overall trend (Uptrend, Downtrend, Sideways)
3. Identify support and resistance levels visible in the chart
4. Predict whether the stock will go UP or DOWN based on the chart patterns
5. Give a confidence level for your prediction

{f'Additional context: {body.context}' if body.context else ''}

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
        
        doc = {"id": str(uuid.uuid4()), "result": result, "user_id": user.uid, "timestamp": datetime.now(timezone.utc).isoformat()}
        await db.chart_analyses.insert_one(doc)
        
        return {"analysis": result, "disclaimer": build_disclaimer_response_field(), "timestamp": doc["timestamp"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing chart image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Watchlist CRUD
@api_router.get("/watchlist")
async def get_watchlist(user: AuthenticatedUser = Depends(get_current_user)):
    items = await db.watchlist.find({"user_id": user.uid}, {"_id": 0}).to_list(100)
    return {"watchlist": items}

@api_router.post("/watchlist")
async def add_to_watchlist(item: WatchlistCreate, user: AuthenticatedUser = Depends(get_current_user)):
    existing = await db.watchlist.find_one({"user_id": user.uid, "symbol": item.symbol.upper()}, {"_id": 0})
    if existing:
        return {"message": "Already in watchlist", "item": existing}
    watchlist_item = WatchlistItem(**item.dict())
    doc = watchlist_item.dict()
    doc["user_id"] = user.uid
    await db.watchlist.insert_one(doc)
    return {"message": "Added to watchlist", "item": watchlist_item.dict()}

@api_router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, user: AuthenticatedUser = Depends(get_current_user)):
    result = await db.watchlist.delete_one({"symbol": symbol.upper(), "user_id": user.uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Removed from watchlist"}

# Portfolio CRUD
@api_router.get("/portfolio")
async def get_portfolio(user: AuthenticatedUser = Depends(get_current_user)):
    items = await db.portfolio.find({"user_id": user.uid}, {"_id": 0}).to_list(100)
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
async def add_to_portfolio(item: PortfolioCreate, user: AuthenticatedUser = Depends(get_current_user)):
    portfolio_item = PortfolioItem(**item.dict())
    doc = portfolio_item.dict()
    doc["user_id"] = user.uid
    await db.portfolio.insert_one(doc)
    return {"message": "Added to portfolio", "item": portfolio_item.dict()}

@api_router.delete("/portfolio/{item_id}")
async def remove_from_portfolio(item_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    result = await db.portfolio.delete_one({"id": item_id, "user_id": user.uid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Removed from portfolio"}

# ---------------------------------------------------------------------------
# Phase 2.1 — Fundamentals Data
# ---------------------------------------------------------------------------

def extract_fundamentals(info: dict) -> dict:
    """Extract and group fundamental data from yfinance ticker.info."""
    def pct(v):
        """Convert decimal fraction to percentage, return None if missing."""
        f = safe_float(v)
        return round(f * 100, 2) if f is not None else None

    return {
        "valuation": {
            "pe_ratio":       safe_float(info.get("trailingPE")),
            "forward_pe":     safe_float(info.get("forwardPE")),
            "pb_ratio":       safe_float(info.get("priceToBook")),
            "peg_ratio":      safe_float(info.get("pegRatio")),
            "ev_ebitda":      safe_float(info.get("enterpriseToEbitda")),
            "ev":             safe_float(info.get("enterpriseValue")),
            "market_cap":     safe_float(info.get("marketCap")),
        },
        "profitability": {
            "roe":            pct(info.get("returnOnEquity")),
            "roa":            pct(info.get("returnOnAssets")),
            "gross_margin":   pct(info.get("grossMargins")),
            "operating_margin": pct(info.get("operatingMargins")),
            "profit_margin":  pct(info.get("profitMargins")),
            "ebitda_margin":  pct(info.get("ebitdaMargins")),
        },
        "growth": {
            "revenue_growth":  pct(info.get("revenueGrowth")),
            "earnings_growth": pct(info.get("earningsGrowth")),
            "eps":             safe_float(info.get("trailingEps")),
            "forward_eps":     safe_float(info.get("forwardEps")),
        },
        "financial_health": {
            "debt_to_equity":  safe_float(info.get("debtToEquity")),
            "current_ratio":   safe_float(info.get("currentRatio")),
            "quick_ratio":     safe_float(info.get("quickRatio")),
            "total_debt":      safe_float(info.get("totalDebt")),
            "free_cash_flow":  safe_float(info.get("freeCashflow")),
        },
        "dividends": {
            "dividend_yield":  pct(info.get("dividendYield")),
            "dividend_rate":   safe_float(info.get("dividendRate")),
            "payout_ratio":    pct(info.get("payoutRatio")),
            "ex_dividend_date": info.get("exDividendDate"),
        },
        "ownership": {
            "institutional_holding": pct(info.get("heldPercentInstitutions")),
            "insider_holding":       pct(info.get("heldPercentInsiders")),
            "float_shares":          safe_float(info.get("floatShares")),
        },
    }

@api_router.get("/stocks/{symbol}/fundamentals")
@limiter.limit("60/minute")
async def get_fundamentals(request: Request, symbol: str):
    """Return fundamental financial data for a stock."""
    sym = sanitize_symbol(symbol)
    try:
        ticker = yf.Ticker(sym)
        info = ticker.info
        if not info or "symbol" not in info:
            raise HTTPException(status_code=404, detail=f"Symbol {sym} not found")
        return {
            "symbol": sym,
            "name": info.get("longName") or info.get("shortName", sym),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "fundamentals": extract_fundamentals(info),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fundamentals error {sym}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch fundamentals")

# ---------------------------------------------------------------------------
# Phase 2.2 — News Integration
# ---------------------------------------------------------------------------
import feedparser
import hashlib
from functools import lru_cache

_news_cache: dict = {}
_NEWS_CACHE_TTL = 300  # 5 minutes

def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def _get_cached(key: str):
    entry = _news_cache.get(key)
    if entry and (datetime.now(timezone.utc).timestamp() - entry["ts"] < _NEWS_CACHE_TTL):
        return entry["data"]
    return None

def _set_cached(key: str, data):
    _news_cache[key] = {"data": data, "ts": datetime.now(timezone.utc).timestamp()}

def _days_ago(entry) -> str:
    """Return human-readable time string like '3 hours ago'."""
    import time
    try:
        published = entry.get("published_parsed")
        if published:
            dt = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
            diff = datetime.now(timezone.utc) - dt
            secs = int(diff.total_seconds())
            if secs < 3600:
                return f"{secs // 60}m ago"
            if secs < 86400:
                return f"{secs // 3600}h ago"
            return f"{secs // 86400}d ago"
    except Exception:
        pass
    return ""

def fetch_rss_feed(url: str, max_items: int = 20) -> list:
    """Fetch and parse RSS feed with 5-min cache."""
    key = _cache_key(url)
    cached = _get_cached(key)
    if cached is not None:
        return cached
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:max_items]:
            articles.append({
                "title":     entry.get("title", ""),
                "link":      entry.get("link", ""),
                "source":    feed.feed.get("title", ""),
                "published": _days_ago(entry),
                "summary":   re.sub(r"<[^>]+>", "", entry.get("summary", ""))[:200],
            })
        _set_cached(key, articles)
        return articles
    except Exception as e:
        logger.warning(f"RSS fetch failed {url}: {e}")
        return []

def get_market_news_feeds(max_items: int = 20) -> list:
    """Aggregate market news from Economic Times + Moneycontrol RSS."""
    feeds = [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://www.moneycontrol.com/rss/latestnews.xml",
    ]
    seen = set()
    articles = []
    for url in feeds:
        for a in fetch_rss_feed(url, max_items):
            if a["link"] not in seen:
                seen.add(a["link"])
                articles.append(a)
    return articles[:max_items]

def get_stock_news(symbol: str, max_items: int = 10) -> list:
    """Fetch stock-specific news via Google News RSS."""
    # Use company name if possible; strip exchange suffix
    base = re.sub(r"\.(NS|BO)$", "", symbol, flags=re.IGNORECASE)
    query = base.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}+NSE+stock&hl=en-IN&gl=IN&ceid=IN:en"
    return fetch_rss_feed(url, max_items)

@api_router.get("/market/news")
@limiter.limit("30/minute")
async def get_market_news(request: Request, limit: int = Query(20, ge=1, le=50)):
    """Return latest Indian market news from ET + Moneycontrol."""
    articles = get_market_news_feeds(limit)
    return {"articles": articles, "count": len(articles)}

@api_router.get("/stocks/{symbol}/news")
@limiter.limit("30/minute")
async def get_stock_news_endpoint(request: Request, symbol: str, limit: int = Query(10, ge=1, le=30)):
    """Return stock-specific news for a ticker."""
    sym = sanitize_symbol(symbol)
    articles = get_stock_news(sym, limit)
    return {"symbol": sym, "articles": articles, "count": len(articles)}

@api_router.get("/stocks/{symbol}/earnings")
@limiter.limit("30/minute")
async def get_stock_earnings(request: Request, symbol: str):
    """Return upcoming and historical earnings dates for a stock."""
    sym = sanitize_symbol(symbol)
    try:
        ticker = yf.Ticker(sym)
        calendar = ticker.calendar
        earnings_dates = ticker.earnings_dates
        
        upcoming = []
        historical = []
        
        # Parse yfinance earnings_dates if available
        if earnings_dates is not None and not earnings_dates.empty:
            for dt, row in earnings_dates.iterrows():
                try:
                    date_str = dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, 'strftime') else str(dt)
                    item = {
                        "date": date_str,
                        "eps_estimate": safe_float(row.get('EPS Estimate')),
                        "eps_actual": safe_float(row.get('Reported EPS')),
                        "surprise_pct": safe_float(row.get('Surprise(%)'))
                    }
                    if item["eps_actual"] is None:
                        upcoming.append(item)
                    else:
                        historical.append(item)
                except Exception:
                    continue
                    
        return {
            "symbol": sym,
            "upcoming": upcoming,
            "historical": historical[:10] if historical else []
        }
    except Exception as e:
        logger.error(f"Error fetching earnings for {sym}: {e}")
        return {"symbol": sym, "upcoming": [], "historical": []} # Return empty gracefully


# ---------------------------------------------------------------------------
# Phase 2.3 — Breakout Scanner
# ---------------------------------------------------------------------------

def detect_breakout(df: "pd.DataFrame", sr: dict, technicals: dict) -> Optional[dict]:
    """
    Score a stock for breakout strength (0-10).
    Returns breakout dict if score >= 4, else None.
    """
    if df is None or len(df) < 20:
        return None
    try:
        current_price = safe_float(df["Close"].iloc[-1])
        prev_price    = safe_float(df["Close"].iloc[-2]) if len(df) > 1 else current_price
        avg_vol       = safe_float(df["Volume"].iloc[-20:].mean())
        today_vol     = safe_float(df["Volume"].iloc[-1])

        r1 = safe_float((sr.get("resistance") or {}).get("r1"))
        s1 = safe_float((sr.get("support") or {}).get("s1"))

        rsi       = safe_float(technicals.get("rsi"))
        macd_sig  = technicals.get("macd", {}).get("signal", "")
        adx       = safe_float(technicals.get("adx"))

        if None in (current_price, avg_vol, today_vol):
            return None

        score = 0
        signals = []
        breakout_type = "neutral"

        # Volume ratio
        vol_ratio = round(today_vol / avg_vol, 2) if avg_vol else 1.0

        # Price above R1 (bullish breakout)
        if r1 and current_price > r1:
            if prev_price and prev_price < r1:
                score += 3; signals.append(f"Crossed above R1 ({r1:.2f}) today")
            else:
                score += 1; signals.append(f"Trading above R1 ({r1:.2f})")
            breakout_type = "bullish"

        # Volume spike
        if vol_ratio >= 2.0:
            score += 3; signals.append(f"Volume spike {vol_ratio}x average")
        elif vol_ratio >= 1.5:
            score += 2; signals.append(f"Above-avg volume {vol_ratio}x")

        # RSI momentum zone
        if rsi and 50 <= rsi <= 70:
            score += 2; signals.append(f"RSI in momentum zone ({rsi})")

        # MACD bullish
        if macd_sig == "Bullish":
            score += 1; signals.append("MACD bullish crossover")

        # ADX strong trend
        if adx and adx > 25:
            score += 1; signals.append(f"Strong trend ADX={adx}")

        # Price below S1 (bearish breakdown)
        if s1 and current_price < s1:
            if prev_price and prev_price > s1:
                score += 3; signals.append(f"Broke below S1 ({s1:.2f})")
            breakout_type = "bearish"

        if score < 4:
            return None

        return {
            "breakout_type":  breakout_type,
            "breakout_score": score,
            "current_price":  current_price,
            "volume_ratio":   vol_ratio,
            "signals":        signals,
            "rsi":            rsi,
            "macd_signal":    macd_sig,
            "adx":            adx,
        }
    except Exception as e:
        logger.warning(f"detect_breakout error: {e}")
        return None


@api_router.get("/market/breakouts")
@limiter.limit("10/minute")
async def get_breakouts(request: Request):
    """Scan NIFTY stocks for technical breakout signals."""
    symbols_data = get_nifty50_symbols()
    breakouts = []
    scanned = 0

    for sym_info in symbols_data:
        sym = sym_info["symbol"]
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period="6mo", interval="1d")
            if df.empty or len(df) < 20:
                continue
            df.index = pd.to_datetime(df.index)

            techs = compute_technicals(df)
            sr    = compute_support_resistance(df)
            result = detect_breakout(df, sr, techs)
            scanned += 1

            if result:
                breakouts.append({
                    "symbol":         sym,
                    "name":           sym_info.get("name", sym),
                    "sector":         sym_info.get("sector", ""),
                    **result,
                })
        except Exception as e:
            logger.warning(f"Breakout scan error {sym}: {e}")
            continue

    breakouts.sort(key=lambda x: x["breakout_score"], reverse=True)
    return {
        "breakouts":       breakouts,
        "stocks_scanned":  scanned,
        "breakouts_found": len(breakouts),
        "disclaimer":      SEBI_DISCLAIMER_SHORT,
    }

# ---------------------------------------------------------------------------
# Phase 2.4 — Sector Heatmap
# ---------------------------------------------------------------------------

@api_router.get("/market/sector-heatmap")
@limiter.limit("30/minute")
async def get_sector_heatmap(request: Request):
    """Return sector performance using 5-day price change for NIFTY stocks."""
    symbols_data = get_nifty50_symbols()
    sector_map: dict = {}

    for sym_info in symbols_data:
        sym    = sym_info["symbol"]
        sector = sym_info.get("sector", "Unknown")
        try:
            hist = yf.Ticker(sym).history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue
            open_price  = safe_float(hist["Close"].iloc[0])
            close_price = safe_float(hist["Close"].iloc[-1])
            if not open_price or not close_price:
                continue
            change_pct = round((close_price - open_price) / open_price * 100, 2)

            if sector not in sector_map:
                sector_map[sector] = []
            sector_map[sector].append({
                "symbol":     sym,
                "name":       sym_info.get("name", sym),
                "change_pct": change_pct,
                "price":      close_price,
            })
        except Exception as e:
            logger.warning(f"Heatmap error {sym}: {e}")
            continue

    sectors = []
    pos_count = 0
    neg_count = 0
    for sector, stocks in sector_map.items():
        avg = round(sum(s["change_pct"] for s in stocks) / len(stocks), 2)
        sorted_stocks  = sorted(stocks, key=lambda x: x["change_pct"], reverse=True)
        top_performer  = sorted_stocks[0] if sorted_stocks else None
        bottom_performer = sorted_stocks[-1] if sorted_stocks else None
        if avg >= 0:
            pos_count += 1
        else:
            neg_count += 1
        sectors.append({
            "sector":            sector,
            "avg_change_percent": avg,
            "stocks_count":      len(stocks),
            "top_performer":     top_performer,
            "bottom_performer":  bottom_performer,
            "stocks":            sorted_stocks,
        })

    sectors.sort(key=lambda x: x["avg_change_percent"], reverse=True)
    return {
        "sectors":       sectors,
        "total_sectors": len(sectors),
        "market_breadth": {
            "positive_sectors": pos_count,
            "negative_sectors": neg_count,
        },
    }



# ---------------------------------------------------------------------------
# Phase 2.5 — AI Daily Morning Brief
# ---------------------------------------------------------------------------
_morning_brief_cache = {}

@api_router.get("/market/morning-brief")
@limiter.limit("10/minute")
async def get_morning_brief(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    """Generates a daily morning brief based on overnight global markets and SGX Nifty/News."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check cache first
    if today in _morning_brief_cache:
        return _morning_brief_cache[today]
        
    try:
        # Fetch US Markets (S&P 500, Nasdaq)
        us_indices = {}
        for sym, name in [("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq")]:
            try:
                hist = yf.Ticker(sym).history(period="2d")
                if not hist.empty and len(hist) > 1:
                    c = safe_float(hist['Close'].iloc[-1])
                    p = safe_float(hist['Close'].iloc[-2])
                    pct = round((c - p) / p * 100, 2)
                    us_indices[name] = f"{pct}%"
            except: pass
            
        # Fetch latest top market news 
        news = get_market_news_feeds(max_items=3)
        news_titles = [n['title'] for n in news]
        
        user_profile = await db.users.find_one({"firebase_uid": user.uid})
        preferred_provider = user_profile.get("preferred_provider") if user_profile else None
        preferred_model = user_profile.get("preferred_model") if user_profile else None
        settings = get_llm_config(preferred_provider, preferred_model, user_profile)
        
        prompt = f"""You are the Chief Market Strategist for TradeMind AI, an Indian stock market app.
Write a concise, punchy "Daily Morning Brief" for traders opening the app at 9:00 AM.

DATA PROVIDED:
- Overnight US Markets: S&P 500 {us_indices.get('S&P 500', 'N/A')}, Nasdaq {us_indices.get('Nasdaq', 'N/A')}
- Top News Headlines: {news_titles}

REQUIREMENTS:
Return valid JSON representing a 3-point brief:
1. `global_cues`: 1 sentence summarizing the overnight global mood affecting India today.
2. `market_setup`: 1 sentence summarizing the likely opening setup for Nifty/BankNifty.
3. `theme_of_the_day`: 1 short sentence on which sector/theme to watch based on news.
4. `sentiment`: "Bullish", "Bearish", or "Neutral"

JSON FORMAT EXACTLY:
{{"global_cues": "...", "market_setup": "...", "theme_of_the_day": "...", "sentiment": "Neutral"}}
"""
        response = await call_llm(
            provider=settings["provider"],
            model=settings["model"],
            api_key=settings["api_key"],
            prompt=prompt
        )
        
        brief = parse_llm_json(response, {
            "global_cues": "Global markets were mixed overnight...",
            "market_setup": "Indian markets are expected to open relatively flat.",
            "theme_of_the_day": "Watch specific stock action rather than indices.",
            "sentiment": "Neutral"
        })
        
        result = {
            "date": today,
            "brief": brief,
            "us_markets": us_indices,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Cache it for the day
        _morning_brief_cache[today] = result
        return result
        
    except Exception as e:
        logger.error(f"Error generating morning brief: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate morning brief")


# ---------------------------------------------------------------------------
# Phase 2.6 — Price & Technical Alerts (In-App)
# ---------------------------------------------------------------------------

class AlertCreate(BaseModel):
    symbol: str
    target_price: Optional[float] = None
    condition: str = "above" # 'above' or 'below'
    notes: Optional[str] = None

@api_router.get("/alerts")
async def get_alerts(user: AuthenticatedUser = Depends(get_current_user)):
    """Get all active alerts for the user."""
    cursor = db.alerts.find({"user_id": user.uid, "is_active": True}).sort("created_at", -1)
    alerts = await cursor.to_list(length=100)
    for a in alerts:
        a["_id"] = str(a["_id"])
    return {"alerts": alerts}

@api_router.post("/alerts")
async def create_alert(payload: AlertCreate, user: AuthenticatedUser = Depends(get_current_user)):
    """Create a new price alert."""
    alert_doc = {
        "user_id": user.uid,
        "symbol": sanitize_symbol(payload.symbol),
        "target_price": payload.target_price,
        "condition": payload.condition,
        "notes": payload.notes,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "triggered_at": None
    }
    result = await db.alerts.insert_one(alert_doc)
    alert_doc["_id"] = str(result.inserted_id)
    return {"message": "Alert created", "alert": alert_doc}

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    """Delete or deactivate an alert."""
    from bson import ObjectId
    try:
        oid = ObjectId(alert_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
        
    result = await db.alerts.update_one(
        {"_id": oid, "user_id": user.uid},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found or already inactive")
    return {"message": "Alert removed"}

@api_router.get("/alerts/evaluate")
async def evaluate_alerts(user: AuthenticatedUser = Depends(get_current_user)):
    """Evaluate all active alerts for the user against current market prices. Returns triggered alerts."""
    cursor = db.alerts.find({"user_id": user.uid, "is_active": True})
    alerts = await cursor.to_list(length=50)
    
    triggered = []
    
    # Needs optimization in production, but okay for MVP to loop yfinance
    for alert in alerts:
        try:
            sym = alert["symbol"]
            info = yf.Ticker(sym).fast_info
            current_price = safe_float(info.last_price)
            
            if not current_price or not alert.get("target_price"):
                continue
                
            is_triggered = False
            if alert["condition"] == "above" and current_price >= alert["target_price"]:
                is_triggered = True
            elif alert["condition"] == "below" and current_price <= alert["target_price"]:
                is_triggered = True
                
            if is_triggered:
                # Mark as triggered/inactive
                await db.alerts.update_one(
                    {"_id": alert["_id"]},
                    {"$set": {
                        "is_active": False, 
                        "triggered_at": datetime.now(timezone.utc).isoformat(),
                        "trigger_price": current_price
                    }}
                )
                
                alert["_id"] = str(alert["_id"])
                alert["trigger_price"] = current_price
                triggered.append(alert)
                
        except Exception as e:
            logger.warning(f"Failed to evaluate alert {alert['_id']} for {alert.get('symbol')}: {e}")
            
    return {"triggered": triggered}

# ---------------------------------------------------------------------------
# Phase 3.1 — Angel One SmartAPI Broker Endpoints
# ---------------------------------------------------------------------------
from broker import get_broker, OrderRequest as BrokerOrderRequest
from cryptography.fernet import Fernet
from fastapi import WebSocket, WebSocketDisconnect

import asyncio

_FERNET_KEY = os.environ.get("FERNET_KEY", "").strip() or Fernet.generate_key().decode()
_fernet = Fernet(_FERNET_KEY.encode() if isinstance(_FERNET_KEY, str) else _FERNET_KEY)

def _encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()

def _decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()

class BrokerConnectRequest(BaseModel):
    provider: str = "angelone"
    api_key: str
    client_id: str
    pin: str
    totp_secret: str

class BrokerOrderRequestModel(BaseModel):
    symbol: str
    exchange: str = "NSE"
    transaction_type: str   # "BUY" | "SELL"
    quantity: int
    order_type: str = "MARKET"  # "MARKET" | "LIMIT"
    price: float = 0.0
    product: str = "CNC"

class BrokerCancelRequest(BaseModel):
    order_id: str


@api_router.post("/broker/connect")
@limiter.limit("5/minute")
async def broker_connect(request: Request, payload: BrokerConnectRequest,
                          user: AuthenticatedUser = Depends(get_current_user)):
    """Connect an Angel One broker account. PIN is never stored."""
    broker = get_broker(payload.provider)
    creds = {
        "api_key":     payload.api_key,
        "client_id":   payload.client_id,
        "pin":         payload.pin,
        "totp_secret": payload.totp_secret,
    }
    try:
        session = await broker.connect(creds)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Encrypt sensitive fields before storing
    await db.broker_connections.update_one(
        {"user_id": user.uid},
        {"$set": {
            "user_id":          user.uid,
            "provider":         payload.provider,
            "client_id":        payload.client_id,
            "api_key_enc":      _encrypt(payload.api_key),
            "totp_secret_enc":  _encrypt(payload.totp_secret),
            "jwt_token_enc":    _encrypt(session["jwtToken"]),
            "refresh_token_enc": _encrypt(session.get("refreshToken", "")),
            "feed_token_enc":   _encrypt(session.get("feedToken", "")),
            "connected_at":     datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {"connected": True, "client_id": payload.client_id, "provider": payload.provider}


async def _get_broker_session(user_id: str) -> tuple:
    """Return (broker, session_dict) for an authenticated user, or raise 400."""
    doc = await db.broker_connections.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=400, detail="No broker connected. Please connect in Settings.")
    session = {
        "api_key":      _decrypt(doc["api_key_enc"]),
        "client_id":    doc["client_id"],
        "jwtToken":     _decrypt(doc["jwt_token_enc"]),
        "refreshToken": _decrypt(doc.get("refresh_token_enc", _encrypt(""))),
        "feedToken":    _decrypt(doc.get("feed_token_enc", _encrypt(""))),
    }
    broker = get_broker(doc.get("provider", "angelone"))
    return broker, session


@api_router.post("/broker/disconnect")
async def broker_disconnect(user: AuthenticatedUser = Depends(get_current_user)):
    await db.broker_connections.delete_one({"user_id": user.uid})
    return {"connected": False}


@api_router.get("/broker/status")
async def broker_status(user: AuthenticatedUser = Depends(get_current_user)):
    doc = await db.broker_connections.find_one({"user_id": user.uid})
    if not doc:
        return {"connected": False}
    return {"connected": True, "client_id": doc["client_id"], "provider": doc.get("provider", "angelone")}


@api_router.post("/broker/order")
@limiter.limit("10/minute")
async def broker_place_order(request: Request, payload: BrokerOrderRequestModel,
                              user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    order = BrokerOrderRequest(
        symbol=payload.symbol, exchange=payload.exchange,
        transaction_type=payload.transaction_type, quantity=payload.quantity,
        order_type=payload.order_type, price=payload.price, product=payload.product,
    )
    try:
        result = await broker.place_order(session, order)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    await db.broker_orders.insert_one({
        "user_id": user.uid, "order_id": result.order_id,
        "symbol": payload.symbol, "type": payload.transaction_type,
        "qty": payload.quantity, "price": payload.price,
        "status": result.status, "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"order_id": result.order_id, "status": result.status, "message": result.message}


@api_router.post("/broker/order/cancel")
async def broker_cancel_order(payload: BrokerCancelRequest,
                               user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    try:
        result = await broker.cancel_order(session, payload.order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@api_router.get("/broker/orders")
async def broker_get_orders(user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    return {"orders": await broker.get_order_book(session)}


@api_router.get("/broker/positions")
async def broker_get_positions(user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    positions = await broker.get_positions(session)
    return {"positions": [p.__dict__ for p in positions]}


@api_router.get("/broker/holdings")
async def broker_get_holdings(user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    holdings = await broker.get_holdings(session)
    return {"holdings": [h.__dict__ for h in holdings]}


@api_router.get("/broker/funds")
async def broker_get_funds(user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    funds = await broker.get_funds(session)
    return funds.__dict__


@api_router.get("/broker/search-symbol")
async def broker_search_symbol(exchange: str = "NSE", q: str = Query(..., min_length=1),
                                user: AuthenticatedUser = Depends(get_current_user)):
    broker, session = await _get_broker_session(user.uid)
    results = await broker.search_symbol(session, exchange, q)
    return {"results": results}


# ---------------------------------------------------------------------------
# Phase 3.2 — WebSocket Real-Time Price Feed
# ---------------------------------------------------------------------------

from collections import defaultdict

class ConnectionManager:
    """Manages active WebSocket connections and per-symbol subscriptions."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}        # conn_id -> ws
        self.subscriptions: dict[str, set] = defaultdict(set)  # conn_id -> {symbols}
        self.symbol_conns: dict[str, set] = defaultdict(set)   # symbol -> {conn_ids}

    async def connect(self, conn_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[conn_id] = ws

    def disconnect(self, conn_id: str):
        self.connections.pop(conn_id, None)
        syms = self.subscriptions.pop(conn_id, set())
        for sym in syms:
            self.symbol_conns[sym].discard(conn_id)

    def subscribe(self, conn_id: str, symbols: list[str]):
        for sym in symbols:
            self.subscriptions[conn_id].add(sym)
            self.symbol_conns[sym].add(conn_id)

    def unsubscribe(self, conn_id: str, symbols: list[str]):
        for sym in symbols:
            self.subscriptions[conn_id].discard(sym)
            self.symbol_conns[sym].discard(conn_id)

    def subscribed_symbols(self) -> set:
        return set(self.symbol_conns.keys())

    async def send(self, conn_id: str, message: dict):
        ws = self.connections.get(conn_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(conn_id)

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        for conn_id in list(self.symbol_conns.get(symbol, [])):
            await self.send(conn_id, message)


ws_manager = ConnectionManager()


def _ist_market_status() -> str:
    """Calculate NSE market status in IST (UTC+5:30)."""
    from zoneinfo import ZoneInfo
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now_ist.weekday() >= 5:  # Saturday=5, Sunday=6
        return "weekend"
    h, m = now_ist.hour, now_ist.minute
    t = h * 60 + m
    if t < 9 * 60:
        return "pre-market"
    if t < 15 * 60 + 31:
        return "open"
    return "closed"


async def _price_polling_task():
    """Background task: poll yfinance every 5s for subscribed symbols."""
    while True:
        await asyncio.sleep(5)
        symbols = ws_manager.subscribed_symbols()
        if not symbols:
            continue
        try:
            tickers = yf.Tickers(" ".join(symbols))
            for sym in symbols:
                try:
                    info = tickers.tickers[sym].fast_info
                    price  = safe_float(info.last_price)
                    change = safe_float(info.three_month_return)
                    volume = safe_float(getattr(info, "last_volume", None))
                    await ws_manager.broadcast_to_symbol(sym, {
                        "type":   "price_update",
                        "symbol": sym,
                        "data":   {"price": price, "change": change, "volume": volume},
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Price polling error: {e}")


@app.on_event("startup")
async def start_price_polling():
    asyncio.create_task(_price_polling_task())


@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket, token: str = ""):
    """WebSocket endpoint for live price updates. Auth via Firebase token query param."""
    conn_id = str(uuid.uuid4())
    try:
        if token:
            decoded = firebase_auth.verify_id_token(token)
            user_id = decoded["uid"]
        else:
            user_id = "anonymous"
    except Exception:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(conn_id, websocket)
    market_status = _ist_market_status()
    await ws_manager.send(conn_id, {"type": "market_status", "data": {"status": market_status}})
    try:
        while True:
            msg = await websocket.receive_json()
            action  = msg.get("action")
            symbols = msg.get("symbols", [])
            if action == "subscribe":
                ws_manager.subscribe(conn_id, symbols)
                await ws_manager.send(conn_id, {"type": "subscribed", "symbols": symbols})
            elif action == "unsubscribe":
                ws_manager.unsubscribe(conn_id, symbols)
                await ws_manager.send(conn_id, {"type": "unsubscribed", "symbols": symbols})
            elif action == "ping":
                await ws_manager.send(conn_id, {"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(conn_id)
    except Exception as e:
        logger.warning(f"WS error {conn_id}: {e}")
        ws_manager.disconnect(conn_id)


# ---------------------------------------------------------------------------
# Phase 3.3 — F&O Options Chain + Greeks
# ---------------------------------------------------------------------------
from options import fetch_option_chain_nse, black_scholes_greeks, calculate_max_pain, analyse_oi, INDIA_RISK_FREE_RATE

_options_cache: dict = {}
_OPTIONS_CACHE_TTL = 300  # 5 min


@api_router.get("/options/{symbol}/chain")
@limiter.limit("30/minute")
async def get_option_chain(request: Request, symbol: str, expiry: Optional[str] = None):
    """Return option chain with OI analysis, max pain, and PCR for a stock."""
    sym = sanitize_symbol(symbol)

    # 5-minute cache
    cache_key = f"{sym}:{expiry or 'all'}"
    entry = _options_cache.get(cache_key)
    if entry and datetime.now(timezone.utc).timestamp() - entry["ts"] < _OPTIONS_CACHE_TTL:
        return entry["data"]

    try:
        underlying_price, expiry_dates, chain_rows = await asyncio.get_event_loop().run_in_executor(
            None, fetch_option_chain_nse, sym
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Option chain fetch failed: {e}")

    # Filter by selected expiry
    selected_expiry = expiry or (expiry_dates[0] if expiry_dates else None)
    filtered = [r for r in chain_rows if r["expiry_date"] == selected_expiry] if selected_expiry else chain_rows

    max_pain    = calculate_max_pain(filtered)
    oi_analysis = analyse_oi(filtered)

    result = {
        "symbol":           sym,
        "underlying_price": underlying_price,
        "expiry_dates":     expiry_dates,
        "selected_expiry":  selected_expiry,
        "chain":            sorted(filtered, key=lambda x: x["strike_price"]),
        "max_pain":         max_pain,
        "oi_analysis":      oi_analysis,
    }
    _options_cache[cache_key] = {"data": result, "ts": datetime.now(timezone.utc).timestamp()}
    return result


@api_router.get("/options/{symbol}/greeks")
@limiter.limit("30/minute")
async def get_option_greeks(request: Request, symbol: str,
                             strike: float = Query(...),
                             option_type: str = Query(..., regex="^(CE|PE)$"),
                             expiry: str = Query(...)):
    """Return Black-Scholes Greeks for a specific option contract."""
    sym = sanitize_symbol(symbol)

    # Fetch underlying price
    try:
        info  = yf.Ticker(sym).fast_info
        S     = safe_float(info.last_price) or 0
    except Exception:
        S = 0

    if not S:
        raise HTTPException(status_code=400, detail="Could not fetch underlying price")

    # Time to expiry in years
    try:
        from dateutil.parser import parse as parse_date  # type: ignore
        exp_dt = parse_date(expiry)
        T = max(0, (exp_dt.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days / 365.0)
    except Exception:
        T = 30 / 365.0  # default 30 days

    # Try to get IV from cached chain
    sigma = 0.25  # default 25%
    cache_key = f"{sym}:all"
    entry = _options_cache.get(cache_key)
    if entry:
        for row in entry["data"].get("chain", []):
            if (abs(row["strike_price"] - strike) < 0.01
                    and row["option_type"] == option_type
                    and row["expiry_date"] == expiry):
                iv = row.get("implied_volatility", 0)
                if iv:
                    sigma = iv / 100
                break

    greeks = black_scholes_greeks(S, strike, T, INDIA_RISK_FREE_RATE, sigma, option_type)
    return {
        "symbol":               sym,
        "strike":               strike,
        "option_type":          option_type,
        "expiry":               expiry,
        "underlying_price":     S,
        "time_to_expiry_days":  round(T * 365),
        "implied_volatility":   round(sigma * 100, 2),
        "greeks":               greeks,
    }

app.include_router(api_router)

_allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:8081,http://localhost:19006").split(",")]
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=_allowed_origins, allow_methods=["GET", "POST", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
