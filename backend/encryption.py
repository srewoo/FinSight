"""
Encryption utility using Fernet symmetric encryption.
Used for encrypting sensitive values (API keys, secrets) stored in MongoDB.
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet = None


def get_fernet() -> Fernet:
    """Get or initialize the Fernet cipher from FERNET_ENCRYPTION_KEY env var."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get("FERNET_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "FERNET_ENCRYPTION_KEY not set. Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns base64-encoded ciphertext."""
    if not plaintext:
        return ""
    f = get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext. Returns plaintext string."""
    if not ciphertext:
        return ""
    f = get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value — invalid token or corrupted data")
        raise ValueError("Decryption failed. The encryption key may have changed.")


def reset_fernet():
    """Reset the cached Fernet instance. Used in tests."""
    global _fernet
    _fernet = None
