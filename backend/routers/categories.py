from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])

DEFAULT_USER_ID = 1

SYSTEM_CATEGORIES = [
    {"name": "餐饮", "icon": "🍜", "parent_id": None},
    {"name": "交通", "icon": "🚗", "parent_id": None},
    {"name": "购物", "icon": "🛒", "parent_id": None},
    {"name": "娱乐", "icon": "🎮", "parent_id": None},
    {"name": "医疗", "icon": "🏥", "parent_id": None},
    {"name": "教育", "icon": "📚", "parent_id": None},
    {"name": "居家", "icon": "🏠", "parent_id": None},
    {"name": "工资", "icon": "💼", "parent_id": None},
    {"name": "副业", "icon": "💡", "parent_id": None},
    {"name": "其他", "icon": "📦", "parent_id": None},
]


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).filter(
        (Category.user_id == None) | (Category.user_id == DEFAULT_USER_ID)
    ).all()
    return cats


def seed_categories(db: Session):
    existing = db.query(Category).filter(Category.user_id == None).count()
    if existing == 0:
        for c in SYSTEM_CATEGORIES:
            db.add(Category(**c))
        db.commit()
