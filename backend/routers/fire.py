from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.deps import get_current_user_id
from backend.services.fire_service import (
    calculate_fire_status,
    calculate_projection,
    get_or_create_profile,
)

router = APIRouter(prefix="/api/fire", tags=["fire"])


def _profile_dict(profile):
    return {
        "monthly_fixed_income": profile.monthly_fixed_income,
        "monthly_expense":      profile.monthly_expense,
        "cash_assets":          profile.cash_assets,
        "stock_assets":         profile.stock_assets,
        "real_estate_assets":   profile.real_estate_assets,
        "other_assets":         profile.other_assets,
        "cash_return":          profile.cash_return,
        "stock_return":         profile.stock_return,
        "real_estate_return":   profile.real_estate_return,
        "other_return":         profile.other_return,
        "fire_multiplier":      profile.fire_multiplier,
    }


class FireProfileUpdate(BaseModel):
    monthly_fixed_income: Optional[float] = None
    monthly_expense:      Optional[float] = None
    cash_assets:          Optional[float] = None
    stock_assets:         Optional[float] = None
    real_estate_assets:   Optional[float] = None
    other_assets:         Optional[float] = None
    cash_return:          Optional[float] = None
    stock_return:         Optional[float] = None
    real_estate_return:   Optional[float] = None
    other_return:         Optional[float] = None
    fire_multiplier:      Optional[float] = None


@router.get("/status")
def fire_status(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return calculate_fire_status(db, user_id)


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return _profile_dict(get_or_create_profile(db, user_id))


@router.put("/profile")
def update_profile(
    body: FireProfileUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    profile = get_or_create_profile(db, user_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return _profile_dict(profile)


@router.get("/projection")
def fire_projection(
    years: int = 30,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    points = calculate_projection(db, user_id, years=min(years, 50))
    return {"points": points}
