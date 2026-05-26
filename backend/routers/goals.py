from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Goal

router = APIRouter(prefix="/api/goals", tags=["goals"])

DEFAULT_USER_ID = 1


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    deadline: Optional[date] = None


@router.get("")
def list_goals(db: Session = Depends(get_db)):
    return db.query(Goal).filter(Goal.user_id == DEFAULT_USER_ID).all()


@router.post("", status_code=201)
def create_goal(body: GoalCreate, db: Session = Depends(get_db)):
    g = Goal(user_id=DEFAULT_USER_ID, **body.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.put("/{goal_id}")
def update_goal(goal_id: int, body: GoalUpdate, db: Session = Depends(get_db)):
    g = db.get(Goal, goal_id)
    if not g or g.user_id != DEFAULT_USER_ID:
        raise HTTPException(404, "Goal not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(g, k, v)
    db.commit()
    db.refresh(g)
    return g


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    g = db.get(Goal, goal_id)
    if not g or g.user_id != DEFAULT_USER_ID:
        raise HTTPException(404, "Goal not found")
    db.delete(g)
    db.commit()
