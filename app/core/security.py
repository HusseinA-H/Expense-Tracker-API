import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError


class TokenPayload(BaseModel):
    sub: str  # User ID
    email: str | None = None
    role: str
    iat: int
    exp: int
    jti: str


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(user_id: uuid.UUID, role: str, email: str | None = None) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": f"access_{uuid.uuid4().hex}",
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


def verify_access_token(token: str) -> TokenPayload:
    """Decode and validate JWT. Raises AuthenticationError if invalid/expired."""
    try:
        payload_dict = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenPayload(**payload_dict)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            message="Access token has expired.", error_code="TOKEN_EXPIRED"
        )
    except (jwt.InvalidTokenError, ValueError):
        raise AuthenticationError(
            message="Token is malformed or tampered.", error_code="TOKEN_INVALID"
        )


def generate_opaque_token() -> str:
    """Generate a secure random hex string to be used as a refresh token."""
    return uuid.uuid4().hex + uuid.uuid4().hex
