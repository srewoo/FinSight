"""
Firebase Cloud Messaging (FCM) Push Notifications
Send push notifications for price alerts and other events.
"""
import logging
import os
from typing import List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    from firebase_admin.exceptions import FirebaseError
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    logger.warning("firebase-admin not installed. Push notifications disabled.")
    logger.warning("Install with: pip install firebase-admin")


class FCMNotification:
    """Firebase Cloud Messaging notification sender."""
    
    def __init__(self):
        self._initialized = False
        self._app: Optional[firebase_admin.App] = None
    
    def initialize(self, service_account_path: Optional[str] = None):
        """Initialize Firebase Admin SDK."""
        if not FCM_AVAILABLE:
            return False
        
        if service_account_path and os.path.exists(service_account_path):
            try:
                cred = credentials.Certificate(service_account_path)
                self._app = firebase_admin.initialize_app(cred)
                self._initialized = True
                logger.info("FCM initialized successfully")
                return True
            except Exception as e:
                logger.error(f"FCM initialization failed: {e}")
                return False
        else:
            logger.warning("FCM service account not configured. Push notifications disabled.")
            return False
    
    async def send_alert_notification(
        self,
        device_tokens: List[str],
        symbol: str,
        target_price: float,
        current_price: float,
        condition: str,
        alert_id: str
    ) -> dict:
        """
        Send push notification for triggered price alert.
        
        Args:
            device_tokens: List of FCM device tokens
            symbol: Stock symbol (e.g., "RELIANCE.NS")
            target_price: Target price that was triggered
            current_price: Current market price
            condition: "above" or "below"
            alert_id: Alert ID for deep linking
        
        Returns:
            dict with success/failure counts
        """
        if not self._initialized:
            logger.warning("FCM not initialized. Skipping notification.")
            return {"success": 0, "failure": len(device_tokens)}
        
        # Determine direction and emoji
        if condition == "above":
            direction = "above"
            emoji = "📈"
            color = "#10B981"  # Green
        else:
            direction = "below"
            emoji = "📉"
            color = "#EF4444"  # Red
        
        # Create notification
        notification = messaging.Notification(
            title=f"{emoji} {symbol} Alert Triggered!",
            body=f"Price {direction} ₹{target_price:.2f} (Now: ₹{current_price:.2f})",
        )
        
        # Create data payload for deep linking
        data = {
            "type": "alert_triggered",
            "alert_id": alert_id,
            "symbol": symbol,
            "target_price": str(target_price),
            "current_price": str(current_price),
            "condition": condition,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Send to all tokens
        success_count = 0
        failure_count = 0
        
        for token in device_tokens:
            try:
                message = messaging.Message(
                    notification=notification,
                    data=data,
                    token=token,
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            color=color,
                            sound="default",
                            click_action="finsight://alerts",
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound="default",
                                category="ALERT_TRIGGERED",
                            ),
                        ),
                    ),
                )
                
                response = messaging.send(message)
                if response:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except FirebaseError as e:
                logger.error(f"FCM send error: {e}")
                failure_count += 1
            except Exception as e:
                logger.error(f"Unexpected error sending FCM: {e}")
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}
    
    async def send_market_update(
        self,
        device_tokens: List[str],
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> dict:
        """Send general market update notification."""
        if not self._initialized:
            return {"success": 0, "failure": len(device_tokens)}
        
        notification = messaging.Notification(
            title=title,
            body=body,
        )
        
        success_count = 0
        failure_count = 0
        
        for token in device_tokens:
            try:
                message = messaging.Message(
                    notification=notification,
                    data=data or {},
                    token=token,
                )
                
                response = messaging.send(message)
                if response:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"FCM send error: {e}")
                failure_count += 1
        
        return {"success": success_count, "failure": failure_count}
    
    async def subscribe_to_topic(self, device_tokens: List[str], topic: str) -> dict:
        """Subscribe devices to a topic (e.g., market_updates, sector:IT)."""
        if not self._initialized:
            return {"success": 0, "failure": len(device_tokens)}
        
        try:
            response = messaging.subscribe_to_topic(device_tokens, topic)
            return {
                "success": response.success_count,
                "failure": response.failure_count
            }
        except Exception as e:
            logger.error(f"Topic subscription error: {e}")
            return {"success": 0, "failure": len(device_tokens)}
    
    async def unsubscribe_from_topic(self, device_tokens: List[str], topic: str) -> dict:
        """Unsubscribe devices from a topic."""
        if not self._initialized:
            return {"success": 0, "failure": len(device_tokens)}
        
        try:
            response = messaging.unsubscribe_from_topic(device_tokens, topic)
            return {
                "success": response.success_count,
                "failure": response.failure_count
            }
        except Exception as e:
            logger.error(f"Topic unsubscription error: {e}")
            return {"success": 0, "failure": len(device_tokens)}


# Global FCM instance
fcm = FCMNotification()


def init_fcm():
    """Initialize FCM from environment configuration."""
    service_account = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    return fcm.initialize(service_account)
