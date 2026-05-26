from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user_id
from backend.models import Account

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    name: str
    type: str
    balance: float = 0.0


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    balance: Optional[float] = None


@router.get("")
def list_accounts(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return db.query(Account).filter(Account.user_id == user_id).all()


@router.post("", status_code=201)
def create_account(body: AccountCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    a = Account(user_id=user_id, **body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.put("/{account_id}")
def update_account(account_id: int, body: AccountUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    a = db.get(Account, account_id)
    if not a or a.user_id != user_id:
        raise HTTPException(404, "Account not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    a = db.get(Account, account_id)
    if not a or a.user_id != user_id:
        raise HTTPException(404, "Account not found")
    db.delete(a)
    db.commit()
