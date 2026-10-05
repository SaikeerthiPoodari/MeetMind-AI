from datetime import datetime, timedelta, timezone
import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .db import get_db
from .models import User

pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")
bearer = HTTPBearer(auto_error=False)
def hash_password(value: str) -> str: return pwd.hash(value)
def verify_password(value: str, hashed: str) -> bool: return pwd.verify(value, hashed)
def create_token(user: User) -> str:
    payload = {"sub": user.id, "email": user.email, "role": user.role, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, SECRET, algorithm="HS256")
def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try: payload = jwt.decode(credentials.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc: raise HTTPException(status_code=401, detail="Authentication expired") from exc
    user = db.get(User, payload.get("sub"))
    if not user: raise HTTPException(status_code=401, detail="User no longer exists")
    return user
