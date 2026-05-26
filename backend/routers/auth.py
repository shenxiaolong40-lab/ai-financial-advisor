from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import settings
from backend.services.auth_service import (
    get_user_by_email, create_user, verify_password, create_token
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if settings.is_single_user:
        raise HTTPException(400, "单用户模式下无需注册，请将 USER_MODE 设为 multi 启用多用户")
    if len(body.password) < 6:
        raise HTTPException(400, "密码至少 6 位")
    if get_user_by_email(db, body.email):
        raise HTTPException(400, "该邮箱已注册")
    user = create_user(db, body.email, body.password)
    token = create_token(user.id)
    return {"token": token, "user_id": user.id, "email": user.email}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    if settings.is_single_user:
        raise HTTPException(400, "单用户模式下无需登录")
    user = get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash or ""):
        raise HTTPException(401, "邮箱或密码错误")
    token = create_token(user.id)
    return {"token": token, "user_id": user.id, "email": user.email}


@router.get("/me")
def me(db: Session = Depends(get_db)):
    if settings.is_single_user:
        return {"user_id": 1, "mode": "single"}
    return {"mode": "multi"}
