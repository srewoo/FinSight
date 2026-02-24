"""auth.py — Firebase removed. All endpoints are unauthenticated.
   Stub get_current_user returns a fixed anonymous user so existing
   endpoint signatures don't need to change."""
import logging
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

class AuthenticatedUser:
    """Stub user — no auth required."""
    def __init__(self, uid="anonymous", email="user@local", name="User", photo_url=None):
        self.uid = uid
        self.email = email
        self.name = name
        self.photo_url = photo_url

_ANON_USER = AuthenticatedUser()

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> AuthenticatedUser:
    """Returns the anonymous stub user — no token verification performed."""
    return _ANON_USER

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[AuthenticatedUser]:
    """Always returns the stub user."""
    return _ANON_USER

def init_firebase():
    """No-op — Firebase removed."""
    pass
