from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import create_access_token, verify_credentials, require_user, set_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if not verify_credentials(db, form.username, form.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenOut(access_token=create_access_token(form.username))


@router.post("/login-json", response_model=TokenOut)
def login_json(body: LoginIn, db: Session = Depends(get_db)):
    if not verify_credentials(db, body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenOut(access_token=create_access_token(body.username))


@router.get("/me")
def me(user: str = Depends(require_user)):
    return {"username": user}


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: str = Depends(require_user), db: Session = Depends(get_db)):
    if not verify_credentials(db, user, body.current_password):
        raise HTTPException(400, "Current password is incorrect")
    if len(body.new_password) < 4:
        raise HTTPException(400, "New password must be at least 4 characters")
    set_password(db, body.new_password)
    db.commit()
    return {"ok": True}
