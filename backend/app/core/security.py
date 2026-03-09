"""
Nexus Mail — Security Utilities
AES-256-GCM encryption for Google tokens, JWT creation/verification.
"""

import base64
import os
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import get_settings

import structlog

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────
# AES-256-GCM Token Encryption
# ──────────────────────────────────────────────

def _get_aes_key() -> bytes:
    """Get the AES-256 encryption key from settings."""
    settings = get_settings()
    key = settings.encryption_key
    if not key:
        raise ValueError("ENCRYPTION_KEY not set in environment")
    return base64.b64decode(key)


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token string using AES-256-GCM.
    Returns: base64-encoded string containing nonce + ciphertext.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Prepend nonce to ciphertext for storage
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt an AES-256-GCM encrypted token.
    Input: base64-encoded string containing nonce + ciphertext.
    """
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


# ──────────────────────────────────────────────
# JWT Token Management
# ──────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict | None:
    """
    Verify and decode a JWT access token.
    Returns the payload dict or None if invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        return None
