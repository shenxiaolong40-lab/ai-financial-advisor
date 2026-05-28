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


class FireProfileUpdate(BaseModel):
    monthly_income: Optional[float] = None
    cash_assets: Optional[float] = None
    stock_assets: Optional[float] = None
    real_estate_assets: Optional[float] = None
    other_assets: Optional[float] = None
    expected_return: Optional[float] = None
    fire_multiplier: Optional[float] = None


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
    profile = get_or_create_profile(db, user_id)
    return {
        "monthly_income": profile.monthly_income,
        "cash_assets": profile.cash_assets,
        "stock_assets": profile.stock_assets,
        "real_estate_assets": profile.real_estate_assets,
        "other_assets": profile.other_assets,
        "expected_return": profile.expected_return,
        "fire_multiplier": profile.fire_multiplier,
    }


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
    return {
        "monthly_income": profile.monthly_income,
        "cash_assets": profile.cash_assets,
        "stock_assets": profile.stock_assets,
        "real_estate_assets": profile.real_estate_assets,
        "other_assets": profile.other_assets,
        "expected_return": profile.expected_return,
        "fire_multiplier": profile.fire_multiplier,
    }


@router.get("/projection")
def fire_projection(
    years: int = 30,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    points = calculate_projection(db, user_id, years=min(years, 50))
    return {"points": points}
