import pytest
from cryptography.fernet import Fernet

from app.services import encryption


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Set a valid Fernet key for all tests in this module."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.gapple_encryption_key", key)
    encryption.reset()
    yield
    encryption.reset()


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-token-12345"
    ciphertext = encryption.encrypt(plaintext)
    assert ciphertext != plaintext
    assert encryption.decrypt(ciphertext) == plaintext


def test_different_plaintexts_produce_different_ciphertexts():
    ct1 = encryption.encrypt("secret_a")
    ct2 = encryption.encrypt("secret_b")
    assert ct1 != ct2


def test_empty_string_roundtrip():
    ciphertext = encryption.encrypt("")
    assert encryption.decrypt(ciphertext) == ""


def test_decrypt_with_wrong_key(monkeypatch):
    ciphertext = encryption.encrypt("hello")

    # Switch to a different key
    other_key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.config.settings.gapple_encryption_key", other_key)
    encryption.reset()

    with pytest.raises(ValueError, match="Decryption failed"):
        encryption.decrypt(ciphertext)


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr("app.config.settings.gapple_encryption_key", "")
    encryption.reset()

    with pytest.raises(ValueError, match="GAPPLE_ENCRYPTION_KEY is not set"):
        encryption.encrypt("test")
