import base64
import hashlib
from datetime import timedelta
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import Settings
from app.database import utc_now


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(settings: Settings, subject: str) -> str:
    expire = utc_now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    subject = payload.get("sub")
    if not subject:
        raise ValueError("Invalid token subject")
    return str(subject)


def _fernet_key(settings: Settings) -> bytes:
    if settings.encryption_key:
        return settings.encryption_key.encode()
    digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(settings: Settings, value: str) -> str:
    return Fernet(_fernet_key(settings)).encrypt(value.encode()).decode()


def decrypt_secret(settings: Settings, value: str) -> str:
    return Fernet(_fernet_key(settings)).decrypt(value.encode()).decode()
