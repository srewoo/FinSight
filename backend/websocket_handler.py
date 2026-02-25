"""
WebSocket handler for real-time stock price updates.
Provides live price streaming to connected clients.
"""
import asyncio
import logging
from typing import Dict, Optional, Set, Any
from datetime import datetime, timezone
import yfinance as yf

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time price updates."""
    
    def __init__(self):
        # Map of symbol -> set of websocket connections
        self.subscriptions: Dict[str, Set[Any]] = {}
        # Map of connection -> set of subscribed symbols
        self.connection_subscriptions: Dict[Any, Set[str]] = {}
        self._running = False
        self._update_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: Any, symbols: list[str]):
        """Accept connection and subscribe to symbols."""
        await websocket.accept()
        
        # Store connection subscriptions
        self.connection_subscriptions[websocket] = set(symbols)
        
        # Add to symbol subscriptions
        for symbol in symbols:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(websocket)
        
        logger.info(f"WebSocket connected. Subscribed to: {symbols}")
        
        # Send initial prices
        initial_data = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    current = float(hist['Close'].iloc[-1])
                    initial_data[symbol] = {
                        "price": round(current, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            except Exception as e:
                logger.warning(f"Failed to get initial price for {symbol}: {e}")
        
        if initial_data:
            await websocket.send_json({
                "type": "initial_prices",
                "data": initial_data
            })
    
    async def disconnect(self, websocket: Any):
        """Remove connection and clean up subscriptions."""
        symbols = self.connection_subscriptions.pop(websocket, set())
        
        for symbol in symbols:
            if symbol in self.subscriptions:
                self.subscriptions[symbol].discard(websocket)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
        
        logger.info(f"WebSocket disconnected. Removed subscriptions: {symbols}")
    
    async def subscribe(self, websocket: Any, symbols: list[str]):
        """Subscribe to additional symbols."""
        existing = self.connection_subscriptions.get(websocket, set())
        existing.update(symbols)
        self.connection_subscriptions[websocket] = existing
        
        for symbol in symbols:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            self.subscriptions[symbol].add(websocket)
        
        logger.info(f"WebSocket subscribed to: {symbols}")
    
    async def unsubscribe(self, websocket: Any, symbols: list[str]):
        """Unsubscribe from symbols."""
        existing = self.connection_subscriptions.get(websocket, set())
        existing.difference_update(symbols)
        self.connection_subscriptions[websocket] = existing
        
        for symbol in symbols:
            if symbol in self.subscriptions:
                self.subscriptions[symbol].discard(websocket)
                if not self.subscriptions[symbol]:
                    del self.subscriptions[symbol]
    
    async def broadcast_price(self, symbol: str, price_data: dict):
        """Broadcast price update to all subscribers of a symbol."""
        if symbol not in self.subscriptions:
            return
        
        message = {
            "type": "price_update",
            "symbol": symbol,
            "data": price_data
        }
        
        disconnected = set()
        for websocket in self.subscriptions[symbol]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def start_price_updates(self, interval: float = 2.0):
        """Start background task to fetch and broadcast prices."""
        self._running = True
        
        async def update_loop():
            """Fetch and broadcast prices at regular intervals."""
            while self._running:
                if not self.subscriptions:
                    await asyncio.sleep(interval)
                    continue
                
                # Fetch prices for all subscribed symbols
                tasks = []
                for symbol in list(self.subscriptions.keys()):
                    tasks.append(self._fetch_price(symbol))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for symbol, price_data in results:
                        if isinstance(price_data, dict):
                            await self.broadcast_price(symbol, price_data)
                
                await asyncio.sleep(interval)
        
        self._update_task = asyncio.create_task(update_loop())
        logger.info("Price update loop started")
    
    async def stop_price_updates(self):
        """Stop the background price update task."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        logger.info("Price update loop stopped")
    
    async def _fetch_price(self, symbol: str) -> tuple[str, dict]:
        """Fetch current price for a symbol."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                return symbol, {}
            
            current = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
            change = round(current - prev, 2)
            change_pct = round((change / prev) * 100, 2) if prev else 0
            
            price_data = {
                "price": round(current, 2),
                "change": change,
                "change_percent": change_pct,
                "volume": int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return symbol, price_data
        except Exception as e:
            logger.warning(f"Failed to fetch price for {symbol}: {e}")
            return symbol, {}
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connection_subscriptions)
    
    def get_subscribed_symbols(self) -> list[str]:
        """Get list of symbols with active subscribers."""
        return list(self.subscriptions.keys())


# Global WebSocket manager
ws_manager = WebSocketManager()
