from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user_id
from backend.models import Budget

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


class BudgetCreate(BaseModel):
    category_id: Optional[int] = None
    limit_amount: float
    period: str = "monthly"


@router.get("")
def list_budgets(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return db.query(Budget).filter(Budget.user_id == user_id).all()


@router.post("", status_code=201)
def upsert_budget(body: BudgetCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    existing = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category_id == body.category_id,
        Budget.period == body.period,
    ).first()
    if existing:
        existing.limit_amount = body.limit_amount
        db.commit()
        db.refresh(existing)
        return existing
    b = Budget(user_id=user_id, **body.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    b = db.get(Budget, budget_id)
    if not b or b.user_id != user_id:
        raise HTTPException(404, "Budget not found")
    db.delete(b)
    db.commit()
