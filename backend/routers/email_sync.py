from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import get_current_user_id
from backend.models import EmailConfig
from backend.services.email_service import (
    decrypt_auth_code,
    encrypt_auth_code,
    fetch_bank_transactions,
    test_connection,
)
from backend.services.sync_service import import_rows

router = APIRouter(prefix="/api/email", tags=["email"])


class EmailConfigIn(BaseModel):
    email: str
    auth_code: str
    provider: str = "qq"


class EmailConfigOut(BaseModel):
    id: int
    email: str
    provider: str
    enabled: bool
    last_sync_at: Optional[datetime]
    created_at: datetime


# ── GET config ────────────────────────────────────────────────────────────────

@router.get("/config")
def get_email_config(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user_id).first()
    if not cfg:
        return {"configured": False}
    return {
        "configured": True,
        "id": cfg.id,
        "email": cfg.email,
        "provider": cfg.provider,
        "enabled": cfg.enabled,
        "last_sync_at": cfg.last_sync_at.isoformat() if cfg.last_sync_at else None,
        "created_at": cfg.created_at.isoformat(),
    }


# ── POST config（保存 + 自动测试连接）────────────────────────────────────────

@router.post("/config")
def save_email_config(
    body: EmailConfigIn,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # 先测试连接
    result = test_connection(body.email, body.auth_code)
    if not result["ok"]:
        raise HTTPException(400, result["message"])

    encrypted = encrypt_auth_code(body.auth_code)
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user_id).first()
    if cfg:
        cfg.email = body.email
        cfg.auth_code_encrypted = encrypted
        cfg.provider = body.provider
        cfg.enabled = True
    else:
        cfg = EmailConfig(
            user_id=user_id,
            email=body.email,
            auth_code_encrypted=encrypted,
            provider=body.provider,
        )
        db.add(cfg)

    db.commit()
    db.refresh(cfg)
    return {"ok": True, "message": "邮箱配置已保存", "email": cfg.email}


# ── DELETE config ─────────────────────────────────────────────────────────────

@router.delete("/config")
def delete_email_config(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user_id).first()
    if cfg:
        db.delete(cfg)
        db.commit()
    return {"ok": True}


# ── POST test（仅测试连接，不保存）────────────────────────────────────────────

@router.post("/test")
def test_email_connection(
    body: EmailConfigIn,
    user_id: int = Depends(get_current_user_id),
):
    result = test_connection(body.email, body.auth_code)
    if not result["ok"]:
        raise HTTPException(400, result["message"])
    return result


# ── POST sync/run（拉取 + 解析 + 入库）────────────────────────────────────────

@router.post("/sync/run")
def run_email_sync(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user_id).first()
    if not cfg or not cfg.enabled:
        raise HTTPException(400, "未配置邮箱，请先在账户页面配置 QQ 邮箱")

    try:
        auth_code = decrypt_auth_code(cfg.auth_code_encrypted)
        rows = fetch_bank_transactions(cfg.email, auth_code, days=90)
    except Exception as e:
        raise HTTPException(500, f"邮件拉取失败：{str(e)}")

    if not rows:
        cfg.last_sync_at = datetime.utcnow()
        db.commit()
        return {
            "inserted": 0,
            "skipped": 0,
            "total": 0,
            "message": "未找到银行交易提醒邮件（近 90 天）",
        }

    result = import_rows(rows, account_id=None, db=db, user_id=user_id)
    cfg.last_sync_at = datetime.utcnow()
    db.commit()

    result["message"] = f"同步完成：新增 {result['inserted']} 条，跳过重复 {result['skipped']} 条"
    return result
