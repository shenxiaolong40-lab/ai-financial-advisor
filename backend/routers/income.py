from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import IncomeProfile

router = APIRouter(prefix="/api/income", tags=["income"])

DEFAULT_USER_ID = 1


class IncomeUpdate(BaseModel):
    monthly_income: float
    monthly_extra: float = 0.0
    currency: str = "CNY"


@router.get("")
def get_income(db: Session = Depends(get_db)):
    profile = db.query(IncomeProfile).filter(IncomeProfile.user_id == DEFAULT_USER_ID).first()
    if not profile:
        return {"monthly_income": 0.0, "monthly_extra": 0.0, "currency": "CNY"}
    return profile


@router.put("")
def update_income(body: IncomeUpdate, db: Session = Depends(get_db)):
    profile = db.query(IncomeProfile).filter(IncomeProfile.user_id == DEFAULT_USER_ID).first()
    if profile:
        profile.monthly_income = body.monthly_income
        profile.monthly_extra = body.monthly_extra
        profile.currency = body.currency
    else:
        profile = IncomeProfile(user_id=DEFAULT_USER_ID, **body.model_dump())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
