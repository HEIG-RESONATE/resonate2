import hashlib
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.environ["ADMIN_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


def hash_password(password: str) -> str:
    salted = f"{SECRET_KEY}:{password}"
    return hashlib.sha256(salted.encode())


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain).digest() == hashed.digest()


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": "admin", "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


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
