import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import get_settings

settings = get_settings()

def _normalize_key(raw: str) -> bytes:
    b = raw.encode()
    if len(b) >= 32:
        return b[:32]
    return (b + b"0" * 32)[:32]

KEY = _normalize_key(settings.AES_ENCRYPTION_KEY)

def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    aesgcm = AESGCM(KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        raw = base64.b64decode(token)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(KEY)
        pt = aesgcm.decrypt(nonce, ct, None)
        return pt.decode()
    except Exception:
        return None