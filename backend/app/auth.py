from datetime import datetime, timedelta
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from .config import settings
from . import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)
ALGORITHM = "HS256"

# Settings keys used to override the shop login once changed via the app.
# Falls back to config (.env) defaults until a password change is made.
KEY_USERNAME = "shop_username"
KEY_PASSWORD_HASH = "shop_password_hash"


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _get_setting(db: Session, key: str) -> str:
    row = db.query(models.Setting).filter_by(key=key).first()
    return row.value if row else ""


def current_username(db: Session) -> str:
    return _get_setting(db, KEY_USERNAME) or settings.SHOP_USERNAME


def verify_credentials(db: Session, username: str, password: str) -> bool:
    expected_user = current_username(db)
    if username != expected_user:
        return False
    stored_hash = _get_setting(db, KEY_PASSWORD_HASH)
    if stored_hash:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    # No password change made yet — fall back to the .env default.
    return password == settings.SHOP_PASSWORD


def set_password(db: Session, new_password: str):
    row = db.query(models.Setting).filter_by(key=KEY_PASSWORD_HASH).first()
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    if row:
        row.value = hashed
    else:
        db.add(models.Setting(key=KEY_PASSWORD_HASH, value=hashed))


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
