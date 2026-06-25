import os
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("ADMIN_SECRET_KEY environment variable is required")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

security = HTTPBearer()
ph = PasswordHasher()

_token_blocklist: set[str] = set()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False


def create_access_token() -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": "admin", "exp": expire, "iat": now, "jti": str(uuid.uuid4())},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def get_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        jti = payload.get("jti")
        if jti and jti in _token_blocklist:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def revoke_token(jti: str):
    _token_blocklist.add(jti)


def get_admin_password_hash() -> str:
    raw = os.environ["ADMIN_PASSWORD"]
    return hash_password(raw)


class AdminPassword:
    def __init__(self):
        self._hash = None

    @property
    def hash(self) -> str:
        if self._hash is None:
            self._hash = get_admin_password_hash()
        return self._hash


admin_password = AdminPassword()
