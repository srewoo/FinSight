"""
Price Alerts System for FinSight.
Allows users to set price alerts that trigger when stock crosses a target price.
Includes push notification integration via FCM.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import yfinance as yf
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class AlertCreate(BaseModel):
    symbol: str
    target_price: float
    condition: str  # "above" or "below"
    note: str = ""


class Alert(BaseModel):
    id: str
    user_id: str
    symbol: str
    target_price: float
    condition: str
    current_price: Optional[float] = None
    triggered: bool = False
    triggered_at: Optional[str] = None
    note: str = ""
    notified: bool = False  # Track if push notification was sent
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DeviceToken(BaseModel):
    user_id: str
    token: str
    platform: str  # "ios" or "android"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AlertsManager:
    """Manages price alerts for users."""

    def __init__(self, db: AsyncIOMotorClient):
        self.db = db
        self._fcm_available = False

    def set_fcm_available(self, available: bool):
        """Set FCM availability status."""
        self._fcm_available = available

    async def register_device_token(self, user_id: str, token: str, platform: str) -> bool:
        """Register or update user's device token for push notifications."""
        try:
            await self.db.device_tokens.update_one(
                {"user_id": user_id, "token": token},
                {
                    "$set": {
                        "platform": platform,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                },
                upsert=True
            )
            logger.info(f"Registered device token for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register device token: {e}")
            return False

    async def remove_device_token(self, user_id: str, token: str) -> bool:
        """Remove a device token."""
        try:
            await self.db.device_tokens.delete_one(
                {"user_id": user_id, "token": token}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to remove device token: {e}")
            return False

    async def get_user_device_tokens(self, user_id: str) -> List[str]:
        """Get all device tokens for a user."""
        try:
            tokens = await self.db.device_tokens.find(
                {"user_id": user_id},
                {"token": 1, "_id": 0}
            ).to_list(10)
            return [t["token"] for t in tokens if t.get("token")]
        except Exception as e:
            logger.error(f"Failed to get device tokens: {e}")
            return []

    async def get_user_alerts(self, user_id: str, active_only: bool = True) -> List[Alert]:
        """Get all alerts for a user."""
        query = {"user_id": user_id}
        if active_only:
            query["triggered"] = False

        alerts = await self.db.alerts.find(query, {"_id": 0}).to_list(100)
        return [Alert(**a) for a in alerts]

    async def create_alert(self, user_id: str, alert_data: AlertCreate) -> Alert:
        """Create a new price alert."""
        # Get current price
        try:
            ticker = yf.Ticker(alert_data.symbol)
            hist = ticker.history(period="1d")
            current_price = float(hist['Close'].iloc[-1]) if not hist.empty else None
        except Exception:
            current_price = None

        alert = Alert(
            id=str(__import__('uuid').uuid4()),
            user_id=user_id,
            symbol=alert_data.symbol,
            target_price=alert_data.target_price,
            condition=alert_data.condition,
            current_price=current_price,
            note=alert_data.note,
            notified=False,
        )

        doc = alert.dict()
        await self.db.alerts.insert_one(doc)
        return alert

    async def delete_alert(self, user_id: str, alert_id: str) -> bool:
        """Delete an alert."""
        result = await self.db.alerts.delete_one({"id": alert_id, "user_id": user_id})
        return result.deleted_count > 0

    async def check_and_trigger_alerts(self, symbol: str, current_price: float) -> List[Alert]:
        """
        Check all alerts for a symbol and trigger if condition met.
        Sends push notifications for triggered alerts.
        Returns list of triggered alerts.
        """
        alerts = await self.db.alerts.find({
            "symbol": symbol,
            "triggered": False
        }).to_list(100)

        triggered = []
        now = datetime.now(timezone.utc).isoformat()

        # Import FCM here to avoid circular imports
        from fcm import fcm

        for alert_data in alerts:
            condition = alert_data.get("condition")
            target = alert_data.get("target_price")
            user_id = alert_data.get("user_id")

            should_trigger = False
            if condition == "above" and current_price >= target:
                should_trigger = True
            elif condition == "below" and current_price <= target:
                should_trigger = True

            if should_trigger:
                # Update alert status
                await self.db.alerts.update_one(
                    {"_id": alert_data["_id"]},
                    {
                        "$set": {
                            "triggered": True,
                            "triggered_at": now,
                            "current_price": current_price
                        }
                    }
                )
                alert_data["triggered"] = True
                alert_data["triggered_at"] = now
                alert_data["current_price"] = current_price
                triggered.append(Alert(**alert_data))

                # Send push notification if FCM is available
                if self._fcm_available and not alert_data.get("notified", False):
                    try:
                        device_tokens = await self.get_user_device_tokens(user_id)
                        if device_tokens:
                            result = await fcm.send_alert_notification(
                                device_tokens=device_tokens,
                                symbol=symbol,
                                target_price=target,
                                current_price=current_price,
                                condition=condition,
                                alert_id=alert_data.get("id")
                            )
                            logger.info(f"FCM notification sent: {result}")

                            # Mark as notified
                            await self.db.alerts.update_one(
                                {"_id": alert_data["_id"]},
                                {"$set": {"notified": True}}
                            )
                    except Exception as e:
                        logger.error(f"Failed to send FCM notification: {e}")

        return triggered

    async def get_triggered_alerts(self, user_id: str) -> List[Alert]:
        """Get all triggered (unread) alerts for a user."""
        alerts = await self.db.alerts.find({
            "user_id": user_id,
            "triggered": True
        }, {"_id": 0}).to_list(100)
        return [Alert(**a) for a in alerts]

    async def mark_alert_read(self, user_id: str, alert_id: str) -> bool:
        """Mark a triggered alert as read (delete it)."""
        result = await self.db.alerts.delete_one({"id": alert_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts grouped by symbol for batch checking."""
        alerts = await self.db.alerts.find({"triggered": False}).to_list(1000)

        # Group by symbol
        by_symbol: Dict[str, List] = {}
        for alert in alerts:
            sym = alert.get("symbol")
            if sym not in by_symbol:
                by_symbol[sym] = []
            by_symbol[sym].append(alert)

        return by_symbol

    async def evaluate_all_alerts(self) -> int:
        """
        Evaluate all active alerts against current prices.
        Call this periodically (e.g., every minute) from a background task.
        Returns count of triggered alerts.
        """
        by_symbol = await self.get_all_active_alerts()
        total_triggered = 0

        for symbol, alerts in by_symbol.items():
            try:
                # Fetch current price
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")
                if hist.empty:
                    continue

                current_price = float(hist['Close'].iloc[-1])
                triggered = await self.check_and_trigger_alerts(symbol, current_price)
                total_triggered += len(triggered)

            except Exception as e:
                logger.error(f"Failed to evaluate alerts for {symbol}: {e}")

        return total_triggered


# Global alerts manager (initialized in server.py)
alerts_manager: Optional[AlertsManager] = None


def init_alerts(db: AsyncIOMotorClient):
    """Initialize the alerts manager."""
    global alerts_manager
    alerts_manager = AlertsManager(db)
    logger.info("Alerts manager initialized")
