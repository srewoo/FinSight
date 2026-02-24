import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

# Set up logging and config
logger = logging.getLogger(__name__)

# Config
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-this-in-production-long-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
SECURITY_DISABLED = os.environ.get("DISABLE_AUTH", "false").lower() == "true"

# Security utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

class AuthenticatedUser:
    """Represents the currently authenticated user session."""
    def __init__(self, uid: str, email: str, name: str = "User"):
        self.uid = uid
        self.email = email
        self.name = name

    def __repr__(self):
        return f"<AuthenticatedUser email={self.email}>"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the hashed version."""
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plaintext password."""
    return pwd_context.hash(password[:72])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a JWT encoded token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    """Decodes the JWT token and returns the current user. Raises 401 if invalid/missing."""
    if SECURITY_DISABLED:
        return AuthenticatedUser(uid="anonymous", email="admin@local.host", name="Local Admin")
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            raise credentials_exception
        # In a real app we might query the DB here to verify the user still exists/is active
        return AuthenticatedUser(uid=user_id, email=email, name=payload.get("name", "User"))
    except JWTError:
        raise credentials_exception

async def get_optional_user(token: str = Depends(oauth2_scheme)) -> Optional[AuthenticatedUser]:
    """Decodes the JWT token but returns None if invalid/missing, instead of raising an error."""
    if SECURITY_DISABLED:
        return AuthenticatedUser(uid="anonymous", email="admin@local.host", name="Local Admin")
        
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            return None
        return AuthenticatedUser(uid=user_id, email=email, name=payload.get("name", "User"))
    except JWTError:
        return None

def init_firebase():
    """Kept to satisfy existing router initialization calls."""
    pass
