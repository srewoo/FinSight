"""
News Sentiment Analysis for Indian Stock Market.
Scrapes financial news and provides sentiment scoring using LLM analysis.
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import feedparser
    import requests
    from bs4 import BeautifulSoup
    SENTIMENT_AVAILABLE = True
except ImportError as e:
    SENTIMENT_AVAILABLE = False
    logger.warning(f"Sentiment analysis dependencies not installed: {e}")


@dataclass
class NewsArticle:
    title: str
    source: str
    published: str
    link: str
    summary: str
    sentiment_score: float  # -1 (very negative) to 1 (very positive)
    sentiment_label: str    # "positive", "negative", "neutral"
    relevance_symbols: List[str]  # Related stock symbols
    llm_analysis: Optional[Dict[str, Any]] = None  # LLM-powered analysis


# Curated RSS feeds for Indian market news
INDIA_NEED_RSS_FEEDS = [
    {
        "name": "Moneycontrol - Market News",
        "url": "https://www.moneycontrol.com/rss/marketnews.xml",
        "symbols": ["NIFTY", "SENSEX"]
    },
    {
        "name": "Economic Times - Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeed/1998036.cms",
        "symbols": ["NIFTY", "SENSEX"]
    },
    {
        "name": "Business Standard - Markets",
        "url": "https://www.business-standard.com/rss/markets-113.xml",
        "symbols": ["NIFTY", "SENSEX"]
    },
    {
        "name": "Livemint - Market News",
        "url": "https://www.livemint.com/Rss/Market",
        "symbols": ["NIFTY", "SENSEX"]
    }
]

# Symbol-specific RSS feeds
SYMBOL_FEEDS = {
    "RELIANCE": [
        "https://www.moneycontrol.com/rss/business/reliance.xml",
    ],
    "TCS": [
        "https://www.moneycontrol.com/rss/business/tcs.xml",
    ],
    "HDFCBANK": [
        "https://www.moneycontrol.com/rss/business/hdfcbank.xml",
    ],
    "INFY": [
        "https://www.moneycontrol.com/rss/business/infosys.xml",
    ],
    "TATAMOTORS": [
        "https://www.moneycontrol.com/rss/business/tatamotors.xml",
    ]
}

# Sentiment keywords for Indian market context
POSITIVE_KEYWORDS = [
    "surge", "soar", "jump", "gain", "rally", "hit high", "record high", "outperform",
    "beat estimates", "upgrade", "bullish", "buy rating", "target raised", "profit up",
    "revenue growth", "strong quarter", "positive outlook", "accumulation", "breakout",
    "outperform", "market leader", "dividend", "bonus", "buyback", "order win",
    "expansion", "growth", "recovery", "momentum", "positive", "optimistic"
]

NEGATIVE_KEYWORDS = [
    "crash", "plunge", "tank", "slump", "decline", "fall", "drop", "hit low",
    "52-week low", "downgrade", "sell rating", "target cut", "loss", "miss estimates",
    "bearish", "profit down", "revenue decline", "weak quarter", "negative outlook",
    "distribution", "breakdown", "underperform", "laggard", "concern", "risk",
    "regulatory", "investigation", "scam", "fraud", "default", "bankruptcy"
]

NEUTRAL_KEYWORDS = [
    "stable", "unchanged", "flat", "range-bound", "sideways", "consolidate",
    "hold", "neutral", "wait and watch", "in-line"
]


def clean_text(text: str) -> str:
    """Clean HTML and extra whitespace from text."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def analyze_sentiment_with_llm(
    text: str,
    provider: str = "gemini",
    model: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use LLM (GPT/Gemini/Claude) for sophisticated sentiment analysis.
    Much more accurate than keyword matching.

    Returns:
        Dict with sentiment_score, sentiment_label, and detailed analysis
    """
    if not text:
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "confidence": 0,
            "analysis": "No text to analyze"
        }

    # Try to use LLM if available
    try:
        from llm_client import call_llm, SUPPORTED_MODELS

        # Use default model if not specified
        if not model:
            model = SUPPORTED_MODELS.get(provider, ["gemini-3.0"])[0]

        # Get API key from environment if not provided
        if not api_key:
            import os
            api_key = os.environ.get(f"{provider.upper()}_API_KEY", "")

        if not api_key:
            logger.warning(f"No API key for {provider}. Falling back to keyword analysis.")
            return None

        prompt = f"""Analyze this financial news text for sentiment. Consider:
1. Market sentiment (bullish/bearish)
2. Company-specific news impact
3. Sector/industry implications
4. Economic context

Text to analyze:
{text[:2000]}  # Truncate to avoid token limits

Return ONLY valid JSON:
{{
  "sentiment_score": -1.0 to 1.0,
  "sentiment_label": "positive" | "negative" | "neutral",
  "confidence": 0-100,
  "key_themes": ["theme1", "theme2"],
  "market_impact": "high" | "medium" | "low",
  "analysis": "2-3 sentence summary"
}}"""

        response = await call_llm(
            provider=provider,
            model=model,
            api_key=api_key,
            prompt=prompt,
            system_message="You are an expert Indian stock market analyst. Analyze news sentiment objectively. Return ONLY valid JSON."
        )

        # Parse JSON response
        import json
        result = json.loads(response.strip())

        return {
            "sentiment_score": float(result.get("sentiment_score", 0)),
            "sentiment_label": result.get("sentiment_label", "neutral"),
            "confidence": int(result.get("confidence", 50)),
            "key_themes": result.get("key_themes", []),
            "market_impact": result.get("market_impact", "medium"),
            "analysis": result.get("analysis", ""),
            "method": "llm"
        }

    except Exception as e:
        logger.warning(f"LLM sentiment analysis failed: {e}. Falling back to keyword method.")
        return None


def calculate_sentiment(text: str) -> tuple[float, str]:
    """
    Calculate sentiment score from text using keyword matching.
    Fallback method when LLM is not available.
    Returns (score, label) where score is -1 to 1.
    """
    if not text:
        return 0.0, "neutral"

    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))

    positive_matches = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    negative_matches = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    neutral_matches = sum(1 for kw in NEUTRAL_KEYWORDS if kw in text_lower)

    total = positive_matches + negative_matches + neutral_matches
    if total == 0:
        return 0.0, "neutral"

    # Calculate score: -1 (very negative) to 1 (very positive)
    score = (positive_matches - negative_matches) / max(total, 1)
    score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]

    # Determine label
    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"

    return round(score, 3), label


def extract_symbols(text: str, known_symbols: List[str]) -> List[str]:
    """Extract stock symbols mentioned in text."""
    text_upper = text.upper()
    found = []
    for sym in known_symbols:
        if sym in text_upper:
            found.append(sym)
    return found[:5]  # Limit to 5 symbols


async def fetch_rss_feed(
    url: str,
    source_name: str,
    timeout: int = 10,
    use_llm: bool = False,
    llm_provider: str = "gemini"
) -> List[Dict[str, Any]]:
    """Fetch and parse RSS feed with optional LLM sentiment analysis."""
    if not SENTIMENT_AVAILABLE:
        return []

    try:
        feed = feedparser.parse(url, timeout=timeout)
        articles = []

        # Batch analyze with LLM if requested (more efficient)
        if use_llm:
            # Analyze first 5 articles with LLM (rate limit consideration)
            for i, entry in enumerate(feed.entries[:5]):
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                combined_text = f"{title} {summary}"

                llm_result = await analyze_sentiment_with_llm(
                    combined_text,
                    provider=llm_provider
                )

                if llm_result:
                    sentiment_score = llm_result["sentiment_score"]
                    sentiment_label = llm_result["sentiment_label"]
                else:
                    # Fallback to keyword
                    sentiment_score, sentiment_label = calculate_sentiment(combined_text)

                articles.append({
                    "title": title,
                    "source": source_name,
                    "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                    "link": entry.get("link", ""),
                    "summary": summary[:300],
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "llm_analysis": llm_result,
                })

            # Rest use keyword method
            for entry in feed.entries[5:10]:
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                combined_text = f"{title} {summary}"
                score, label = calculate_sentiment(combined_text)

                articles.append({
                    "title": title,
                    "source": source_name,
                    "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                    "link": entry.get("link", ""),
                    "summary": summary[:300],
                    "sentiment_score": score,
                    "sentiment_label": label,
                    "llm_analysis": None,
                })
        else:
            # All keyword-based
            for entry in feed.entries[:10]:
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                combined_text = f"{title} {summary}"
                score, label = calculate_sentiment(combined_text)

                articles.append({
                    "title": title,
                    "source": source_name,
                    "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                    "link": entry.get("link", ""),
                    "summary": summary[:300],
                    "sentiment_score": score,
                    "sentiment_label": label,
                })

        return articles
    except Exception as e:
        logger.warning(f"Failed to fetch RSS feed {source_name}: {e}")
        return []


async def get_market_news(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch general market news with sentiment analysis.
    Returns list of articles sorted by recency.
    """
    if not SENTIMENT_AVAILABLE:
        return []
    
    all_articles = []
    
    # Fetch from multiple sources
    for feed_info in INDIA_NEED_RSS_FEEDS:
        articles = fetch_rss_feed(feed_info["url"], feed_info["name"])
        all_articles.extend(articles)
    
    # Sort by published date (newest first)
    all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)
    
    # Add symbol relevance
    known_symbols = ["NIFTY", "SENSEX", "RELIANCE", "TCS", "HDFCBANK", "INFY", 
                     "ICICIBANK", "SBIN", "TATAMOTORS", "BAJFINANCE"]
    
    for article in all_articles:
        text = f"{article['title']} {article['summary']}"
        article["relevance_symbols"] = extract_symbols(text, known_symbols)
    
    return all_articles[:limit]


async def get_stock_news(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch news for a specific stock symbol.
    """
    if not SENTIMENT_AVAILABLE:
        return []
    
    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()
    all_articles = []
    
    # Try symbol-specific feeds
    if base_sym in SYMBOL_FEEDS:
        for feed_url in SYMBOL_FEEDS[base_sym]:
            articles = fetch_rss_feed(feed_url, f"{base_sym} News")
            all_articles.extend(articles)
    
    # Also fetch general market news and filter
    market_news = await get_market_news(limit=50)
    for article in market_news:
        if base_sym in article.get("relevance_symbols", []):
            all_articles.append(article)
    
    # Remove duplicates by link
    seen = set()
    unique_articles = []
    for article in all_articles:
        link = article.get("link", "")
        if link not in seen:
            seen.add(link)
            unique_articles.append(article)
    
    # Sort by recency
    unique_articles.sort(key=lambda x: x.get("published", ""), reverse=True)
    
    return unique_articles[:limit]


async def get_sentiment_summary(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get overall market sentiment summary.
    """
    news = await get_market_news(limit=50)
    
    if not news:
        return {
            "overall_sentiment": "neutral",
            "overall_score": 0.0,
            "articles_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
        }
    
    scores = [article["sentiment_score"] for article in news]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    
    positive_count = sum(1 for s in scores if s > 0.2)
    negative_count = sum(1 for s in scores if s < -0.2)
    neutral_count = len(scores) - positive_count - negative_count
    
    if avg_score > 0.2:
        overall = "positive"
    elif avg_score < -0.2:
        overall = "negative"
    else:
        overall = "neutral"
    
    return {
        "overall_sentiment": overall,
        "overall_score": round(avg_score, 3),
        "articles_count": len(news),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "latest_news": news[:10],
    }


# Web scraping fallback (use sparingly to avoid IP bans)
async def scrape_moneycontrol_headlines() -> List[Dict[str, Any]]:
    """
    Fallback: Scrape headlines from Moneycontrol homepage.
    Use this only if RSS feeds fail.
    """
    if not SENTIMENT_AVAILABLE:
        return []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get("https://www.moneycontrol.com/news/market-news/", 
                          headers=headers, timeout=10)
        resp.raise_for_status()
        
        _parser = "lxml" if __import__("importlib.util", fromlist=["find_spec"]).find_spec("lxml") else "html.parser"
        soup = BeautifulSoup(resp.text, _parser)
        articles = []
        
        # Moneycontrol specific selectors (may need updates)
        for item in soup.select("ul.list li")[:15]:
            title_elem = item.find("a")
            if not title_elem:
                continue
            
            title = clean_text(title_elem.get("text", ""))
            link = title_elem.get("href", "")
            
            if title and link.startswith("http"):
                score, label = calculate_sentiment(title)
                articles.append({
                    "title": title,
                    "source": "Moneycontrol (scraped)",
                    "published": datetime.now(timezone.utc).isoformat(),
                    "link": link,
                    "summary": "",
                    "sentiment_score": score,
                    "sentiment_label": label,
                    "relevance_symbols": extract_symbols(title, ["NIFTY", "SENSEX"])
                })
        
        return articles
    except Exception as e:
        logger.warning(f"Moneycontrol scraping failed: {e}")
        return []
