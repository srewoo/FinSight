# FinSight - PRD

## Overview
AI-powered stock assistant for Indian markets (NSE & BSE) that provides real-time stock data, technical analysis, AI-driven buy/sell predictions, and candlestick chart scanning.

## Tech Stack
- **Frontend**: Expo (React Native) with expo-router, react-native-gifted-charts
- **Backend**: FastAPI with yfinance for real-time stock data
- **AI**: OpenAI / Google Gemini / Anthropic Claude (user-configured via Settings)
- **Database**: MongoDB
- **Theme**: Dark trading app aesthetic

## Features

### 1. Home Dashboard
- NIFTY 50 & SENSEX live indices
- Top gainers & losers (real-time from NSE)
- Pull-to-refresh

### 2. Stock Search
- Search across NSE & BSE exchanges
- Both symbol and company name search
- Dynamic yfinance lookup for unknown symbols

### 3. Stock Detail Page
- Live price with change %
- Interactive price chart (1D/5D/1M/3M/6M/1Y)
- **Support & Resistance Levels** (R1/R2/R3, S1/S2/S3, Pivot)
- **Period Highs/Lows** (1M, 6M, 52W)
- Technical Indicators: RSI, MACD, ADX, Bollinger Bands, SMA/EMA
- AI Analysis with short-term & long-term predictions
- Buy/Sell/Hold recommendation with confidence %, target price, stop loss

### 4. AI Stock Picks
- Auto-scans 40+ NSE stocks with 6-month candle data
- Technical scoring algorithm (RSI, MACD, ADX, Bollinger, SMA)
- Buy & Sell recommendations with confidence bars
- Support/resistance levels per stock
- Market sentiment indicator

### 5. Chart Scanner (Camera)
- Capture candlestick chart via camera
- Upload chart from gallery
- AI Vision model analyzes chart patterns
- Identifies: patterns, support/resistance, trend, prediction

### 6. Watchlist
- Add/remove stocks via heart icon
- Stored in MongoDB

### 7. Portfolio Tracker
- Add holdings (symbol, quantity, buy price)
- Real-time P&L calculation
- Total portfolio value & returns

## API Endpoints
- `GET /api/market/indices` - NIFTY 50 & SENSEX
- `GET /api/market/top-movers` - Top gainers/losers
- `GET /api/stocks/search?q=` - Search stocks
- `GET /api/stocks/{symbol}/quote` - Live quote with S/R
- `GET /api/stocks/{symbol}/history` - Price history
- `GET /api/stocks/{symbol}/technicals` - Indicators + S/R
- `POST /api/stocks/{symbol}/ai-analysis` - AI-powered stock analysis
- `GET /api/ai/auto-recommendations` - Bulk stock scan
- `POST /api/ai/analyze-chart-image` - Chart vision analysis
- Watchlist & Portfolio CRUD endpoints

## Data Sources
- **yfinance**: Free real-time NSE/BSE data
- **OpenAI / Gemini / Claude**: AI predictions (user-provided API key, configured in Settings)
