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
        "total_assets":           profile.total_assets,
        "annual_salary":          profile.annual_salary,
        "salary_growth_rate":     profile.salary_growth_rate,
        "annual_fixed_expense":   profile.annual_fixed_expense,
        "annual_flex_expense":    profile.annual_flex_expense,
        "annual_return":          profile.annual_return,
    }


class FireProfileUpdate(BaseModel):
    total_assets:           Optional[float] = None
    annual_salary:          Optional[float] = None
    salary_growth_rate:     Optional[float] = None
    annual_fixed_expense:   Optional[float] = None
    annual_flex_expense:    Optional[float] = None
    annual_return:          Optional[float] = None


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
    years: int = 35,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    points = calculate_projection(db, user_id, years=min(years, 100))
    return {"points": points}
