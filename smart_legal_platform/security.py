from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from functools import lru_cache
from typing import Callable

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from smart_legal_platform.config import get_settings
from smart_legal_platform.models import Role, User, UserInDB


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.admin: {
        "search:read",
        "contracts:analyze",
        "cases:read",
        "cases:write",
        "communications:write",
        "analytics:read",
        "backup:run",
    },
    Role.lawyer: {
        "search:read",
        "contracts:analyze",
        "cases:read",
        "cases:write",
        "communications:write",
        "analytics:read",
    },
    Role.paralegal: {"search:read", "contracts:analyze", "cases:read", "cases:write"},
    Role.client: {"cases:read", "communications:write"},
}


def hash_password(password: str) -> str:
    settings = get_settings()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        settings.jwt_secret.encode("utf-8"),
        120_000,
    )
    return digest.hex()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    expected = hash_password(plain_password)
    return hmac.compare_digest(expected, hashed_password)


USERS_DB: dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        full_name="Platform Admin",
        role=Role.admin,
        hashed_password=hash_password("Admin@12345"),
    ),
    "nora": UserInDB(
        username="nora",
        full_name="Nora Al-Hassan",
        role=Role.lawyer,
        hashed_password=hash_password("Lawyer@123"),
    ),
    "omar": UserInDB(
        username="omar",
        full_name="Omar Al-Qahtani",
        role=Role.lawyer,
        hashed_password=hash_password("Lawyer@123"),
    ),
    "layla": UserInDB(
        username="layla",
        full_name="Layla Al-Salem",
        role=Role.paralegal,
        hashed_password=hash_password("Para@123"),
    ),
    "client1": UserInDB(
        username="client1",
        full_name="Client One",
        role=Role.client,
        hashed_password=hash_password("Client@123"),
    ),
}


def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_user(username: str) -> UserInDB | None:
    return USERS_DB.get(username)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        if not username:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc
    user = get_user(username)
    if not user:
        raise credentials_error
    if user.disabled:
        raise HTTPException(status_code=403, detail="User disabled")
    return User(**user.model_dump(exclude={"hashed_password"}))


def has_permission(user: User, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def require_permission(permission: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return dependency


def random_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.encryption_key.encode("utf-8"))


def encrypt_text(value: str) -> str:
    token = _fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str) -> str:
    try:
        payload = _fernet().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise HTTPException(status_code=400, detail="Invalid encrypted payload") from exc
    return payload.decode("utf-8")

