from datetime import datetime, timedelta, timezone
import uuid
from jose import jwt, JWTError
from passlib.context import CryptContext
from typing import Optional
from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=[settings.PASSWORD_HASH_SCHEME], deprecated="auto")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta, secret: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)

def create_access_token(sub: str, role: str):
    return create_token({"sub": sub, "role": role, "type": "access"}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), settings.JWT_SECRET_KEY)

def create_refresh_token(sub: str, role: str, jti: str | None = None):
    jti = jti or uuid.uuid4().hex
    return create_token({"sub": sub, "role": role, "type": "refresh", "jti": jti}, timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES), settings.JWT_REFRESH_SECRET_KEY), jti

def decode_token(token: str, refresh: bool = False) -> Optional[dict]:
    secret = settings.JWT_REFRESH_SECRET_KEY if refresh else settings.JWT_SECRET_KEY
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError:
        return None
