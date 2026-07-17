"""Field-level encryption for sensitive DB columns using Fernet symmetric encryption.

Key: FIELD_ENCRYPTION_KEY env var (32-byte base64-urlsafe key).
Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_KEY_RAW = os.getenv("FIELD_ENCRYPTION_KEY", "")

def _get_fernet() -> Fernet | None:
    if not _KEY_RAW:
        return None
    try:
        return Fernet(_KEY_RAW.encode())
    except Exception:
        logger.error("FIELD_ENCRYPTION_KEY is set but invalid — field encryption disabled")
        return None

_fernet: Fernet | None = _get_fernet()

def encrypt_field(value: str | None) -> str | None:
    """Encrypt a string value. Returns None if value is None or encryption not configured."""
    if value is None:
        return None
    if _fernet is None:
        return value  # graceful degradation — encryption not configured
    return _fernet.encrypt(value.encode()).decode()

def decrypt_field(value: str | None) -> str | None:
    """Decrypt a string value. Returns None if value is None or decryption fails."""
    if value is None:
        return None
    if _fernet is None:
        return value  # graceful degradation
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        logger.warning("decrypt_field: InvalidToken — returning None")
        return None
