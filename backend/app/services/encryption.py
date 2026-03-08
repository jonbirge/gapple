from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    key = settings.gapple_encryption_key
    if not key:
        raise ValueError(
            "GAPPLE_ENCRYPTION_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        _fernet = Fernet(key.encode())
    except (ValueError, Exception) as e:
        raise ValueError(f"GAPPLE_ENCRYPTION_KEY is invalid: {e}") from e
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64-encoded Fernet token."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Decryption failed: invalid token or wrong key") from e


def reset() -> None:
    """Reset the cached Fernet instance (useful for testing)."""
    global _fernet
    _fernet = None
