from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from ..auth import create_access_token, verify_credentials, require_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends()):
    if not verify_credentials(form.username, form.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenOut(access_token=create_access_token(form.username))


@router.post("/login-json", response_model=TokenOut)
def login_json(body: LoginIn):
    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenOut(access_token=create_access_token(body.username))


@router.get("/me")
def me(user: str = Depends(require_user)):
    return {"username": user}
