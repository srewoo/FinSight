"""Tests for the Fernet encryption utility."""
import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def setup_encryption_key(monkeypatch):
    """Set a test encryption key for every test."""
    test_key = Fernet.generate_key().decode()
    monkeypatch.setenv("FERNET_ENCRYPTION_KEY", test_key)
    # Reset cached fernet instance before each test
    from encryption import reset_fernet
    reset_fernet()
    yield
    reset_fernet()


def test_encrypt_decrypt_roundtrip():
    from encryption import encrypt_value, decrypt_value
    plaintext = "sk-ant-api03-secret-key-12345"
    ciphertext = encrypt_value(plaintext)
    assert ciphertext != plaintext
    assert decrypt_value(ciphertext) == plaintext


def test_encrypt_different_outputs():
    """Fernet produces different ciphertexts for the same input (due to timestamp + IV)."""
    from encryption import encrypt_value
    a = encrypt_value("same-input")
    b = encrypt_value("same-input")
    assert a != b  # Different ciphertexts


def test_encrypt_empty_string():
    from encryption import encrypt_value, decrypt_value
    assert encrypt_value("") == ""
    assert decrypt_value("") == ""


def test_decrypt_invalid_ciphertext():
    from encryption import decrypt_value
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_value("not-valid-ciphertext")


def test_decrypt_with_wrong_key(monkeypatch):
    from encryption import encrypt_value, decrypt_value, reset_fernet
    ciphertext = encrypt_value("secret-data")

    # Switch to a different key
    new_key = Fernet.generate_key().decode()
    monkeypatch.setenv("FERNET_ENCRYPTION_KEY", new_key)
    reset_fernet()

    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_value(ciphertext)


def test_missing_key_raises(monkeypatch):
    from encryption import reset_fernet
    monkeypatch.delenv("FERNET_ENCRYPTION_KEY", raising=False)
    reset_fernet()

    from encryption import encrypt_value
    with pytest.raises(RuntimeError, match="FERNET_ENCRYPTION_KEY not set"):
        encrypt_value("test")
