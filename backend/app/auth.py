from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_credentials(username: str, password: str) -> bool:
    return (username == settings.SHOP_USERNAME and
            password == settings.SHOP_PASSWORD)


def require_user(token: str = Depends(oauth2_scheme)) -> str:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise cred_exc
        return sub
    except JWTError:
        raise cred_exc
