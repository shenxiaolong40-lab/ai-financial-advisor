from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database import get_db
from backend.deps import get_current_user_id
from backend.models import Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


class TransactionCreate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: float
    type: str
    date: date
    description: str = ""
    merchant: str = ""
    sync_source: Optional[str] = None
    sync_id: Optional[str] = None


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    date: Optional[date] = None
    description: Optional[str] = None
    merchant: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    account_id: Optional[int]
    category_id: Optional[int]
    amount: float
    type: str
    date: date
    description: str
    merchant: str
    sync_source: Optional[str]
    category_name: Optional[str] = None
    category_icon: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("")
def list_transactions(
    month: Optional[str] = Query(None),
    category_id: Optional[int] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    q = db.query(Transaction).filter(Transaction.user_id == user_id)

    if month:
        year, m = int(month[:4]), int(month[5:7])
        from datetime import date as dt
        start = dt(year, m, 1)
        end = dt(year + 1, 1, 1) if m == 12 else dt(year, m + 1, 1)
        q = q.filter(Transaction.date >= start, Transaction.date < end)
    if category_id:
        q = q.filter(Transaction.category_id == category_id)
    if type:
        q = q.filter(Transaction.type == type)
    if search:
        q = q.filter(
            Transaction.description.ilike(f"%{search}%") |
            Transaction.merchant.ilike(f"%{search}%")
        )

    total = q.count()
    items = q.order_by(desc(Transaction.date)).offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for t in items:
        out = TransactionOut.model_validate(t)
        if t.category:
            out.category_name = t.category.name
            out.category_icon = t.category.icon
        result.append(out)

    return {"total": total, "page": page, "page_size": page_size, "items": result}


@router.post("", status_code=201)
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    t = Transaction(user_id=user_id, **body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/{txn_id}")
def update_transaction(
    txn_id: int,
    body: TransactionUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    t = db.get(Transaction, txn_id)
    if not t or t.user_id != user_id:
        raise HTTPException(404, "Transaction not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    t = db.get(Transaction, txn_id)
    if not t or t.user_id != user_id:
        raise HTTPException(404, "Transaction not found")
    db.delete(t)
    db.commit()
