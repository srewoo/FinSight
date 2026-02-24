"""
backend/broker.py — Abstract broker abstraction + Angel One SmartAPI implementation.

Pattern mirrors llm_client.py: abstract base class + concrete implementation,
swappable via provider name.
"""
from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class OrderRequest:
    symbol: str          # NSE trading symbol, e.g. "RELIANCE"
    exchange: str        # "NSE" | "BSE"
    transaction_type: str  # "BUY" | "SELL"
    quantity: int
    order_type: str      # "MARKET" | "LIMIT"
    price: float = 0.0   # required for LIMIT orders
    product: str = "CNC" # CNC (delivery) | MIS (intraday) | NRML (F&O)
    variety: str = "NORMAL"


@dataclass
class OrderResponse:
    order_id: str
    status: str
    message: str


@dataclass
class Position:
    symbol: str
    exchange: str
    quantity: int
    average_price: float
    ltp: float
    pnl: float
    product: str


@dataclass
class Holding:
    symbol: str
    isin: str
    quantity: int
    average_price: float
    ltp: float
    current_value: float
    pnl: float
    pnl_percent: float


@dataclass
class FundsData:
    net: float
    available_cash: float
    used_margin: float
    total_balance: float


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseBroker(ABC):
    """Abstract broker interface. All implementations must conform to this."""

    @abstractmethod
    async def connect(self, credentials: dict) -> dict:
        """Authenticate and return session token dict."""
        ...

    @abstractmethod
    async def disconnect(self, client_id: str) -> bool:
        ...

    @abstractmethod
    async def place_order(self, session: dict, order: OrderRequest) -> OrderResponse:
        ...

    @abstractmethod
    async def cancel_order(self, session: dict, order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_order_book(self, session: dict) -> List[dict]:
        ...

    @abstractmethod
    async def get_positions(self, session: dict) -> List[Position]:
        ...

    @abstractmethod
    async def get_holdings(self, session: dict) -> List[Holding]:
        ...

    @abstractmethod
    async def get_funds(self, session: dict) -> FundsData:
        ...

    @abstractmethod
    async def search_symbol(self, session: dict, exchange: str, query: str) -> List[dict]:
        ...


# ---------------------------------------------------------------------------
# Angel One SmartAPI implementation
# ---------------------------------------------------------------------------

class AngelOneBroker(BaseBroker):
    """
    Angel One SmartAPI broker.
    Uses smartapi-python SDK (sync), executed in asyncio thread pool.
    Requires: pip install smartapi-python pyotp
    """

    def _make_smart_connect(self, api_key: str):
        """Create a SmartConnect instance (lazy import so server starts without SDK)."""
        try:
            from SmartApi import SmartConnect  # type: ignore
            return SmartConnect(api_key=api_key)
        except ImportError:
            raise RuntimeError(
                "smartapi-python not installed. Run: pip install smartapi-python"
            )

    def _generate_totp(self, totp_secret: str) -> str:
        import pyotp
        return pyotp.TOTP(totp_secret).now()

    async def connect(self, credentials: dict) -> dict:
        """
        credentials = {api_key, client_id, pin, totp_secret}
        PIN is only used here and never stored.
        Returns session dict with jwtToken, refreshToken, feedToken.
        """
        api_key     = credentials["api_key"]
        client_id   = credentials["client_id"]
        pin         = credentials["pin"]
        totp_secret = credentials["totp_secret"]

        def _sync_connect():
            smart = self._make_smart_connect(api_key)
            totp  = self._generate_totp(totp_secret)
            data  = smart.generateSession(client_id, pin, totp)
            if not data or data.get("status") is False:
                raise ValueError(data.get("message", "Angel One login failed"))
            return {
                "jwtToken":     data["data"]["jwtToken"],
                "refreshToken": data["data"]["refreshToken"],
                "feedToken":    data["data"]["feedToken"],
                "client_id":    client_id,
                "api_key":      api_key,
            }

        return await asyncio.get_event_loop().run_in_executor(None, _sync_connect)

    async def disconnect(self, client_id: str) -> bool:
        logger.info(f"AngelOne disconnect: {client_id}")
        return True  # JWT expires; no explicit server-side logout needed

    async def place_order(self, session: dict, order: OrderRequest) -> OrderResponse:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.setSessionExpiryHook(lambda: None)
            smart.userId     = session["client_id"]
            smart.jwtToken   = session["jwtToken"]
            smart.refreshToken = session.get("refreshToken", "")
            smart.feedToken  = session.get("feedToken", "")

            params = {
                "variety":          order.variety,
                "tradingsymbol":    order.symbol,
                "symboltoken":      "",          # resolved client-side ideally
                "transactiontype":  order.transaction_type,
                "exchange":         order.exchange,
                "ordertype":        order.order_type,
                "producttype":      order.product,
                "duration":         "DAY",
                "price":            str(order.price) if order.order_type == "LIMIT" else "0",
                "squareoff":        "0",
                "stoploss":         "0",
                "quantity":         str(order.quantity),
            }
            result = smart.placeOrder(params)
            if not result or result.get("status") is False:
                raise ValueError(result.get("message", "Order failed"))
            return OrderResponse(
                order_id=result["data"]["orderid"],
                status="placed",
                message=result.get("message", "Order placed successfully"),
            )

        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    async def cancel_order(self, session: dict, order_id: str) -> dict:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.cancelOrder(order_id, "NORMAL")
            return result or {}
        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    async def get_order_book(self, session: dict) -> List[dict]:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.orderBook()
            return (result or {}).get("data") or []
        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    async def get_positions(self, session: dict) -> List[Position]:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.position()
            raw = (result or {}).get("data") or []
            positions = []
            for p in raw:
                positions.append(Position(
                    symbol=p.get("tradingsymbol", ""),
                    exchange=p.get("exchange", ""),
                    quantity=int(p.get("netqty", 0)),
                    average_price=float(p.get("averageprice", 0)),
                    ltp=float(p.get("ltp", 0)),
                    pnl=float(p.get("unrealised", 0)),
                    product=p.get("producttype", ""),
                ))
            return positions
        result = await asyncio.get_event_loop().run_in_executor(None, _sync)
        return result

    async def get_holdings(self, session: dict) -> List[Holding]:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.holding()
            raw = (result or {}).get("data") or []
            holdings = []
            for h in raw:
                qty = int(h.get("quantity", 0))
                avg = float(h.get("averageprice", 0))
                ltp = float(h.get("ltp", 0))
                cur = qty * ltp
                pnl = cur - qty * avg
                holdings.append(Holding(
                    symbol=h.get("tradingsymbol", ""),
                    isin=h.get("isin", ""),
                    quantity=qty,
                    average_price=avg,
                    ltp=ltp,
                    current_value=round(cur, 2),
                    pnl=round(pnl, 2),
                    pnl_percent=round(pnl / (qty * avg) * 100, 2) if avg else 0,
                ))
            return holdings
        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    async def get_funds(self, session: dict) -> FundsData:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.rmsLimit()
            data = (result or {}).get("data") or {}
            return FundsData(
                net=float(data.get("net", 0)),
                available_cash=float(data.get("availablecash", 0)),
                used_margin=float(data.get("utiliseddebits", 0)),
                total_balance=float(data.get("grossutilisation", 0)),
            )
        return await asyncio.get_event_loop().run_in_executor(None, _sync)

    async def search_symbol(self, session: dict, exchange: str, query: str) -> List[dict]:
        def _sync():
            smart = self._make_smart_connect(session["api_key"])
            smart.jwtToken = session["jwtToken"]
            result = smart.searchScrip(exchange, query)
            return (result or {}).get("data") or []
        return await asyncio.get_event_loop().run_in_executor(None, _sync)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_broker(provider: str = "angelone") -> BaseBroker:
    providers = {"angelone": AngelOneBroker}
    cls = providers.get(provider.lower())
    if not cls:
        raise ValueError(f"Unknown broker provider: {provider}")
    return cls()
