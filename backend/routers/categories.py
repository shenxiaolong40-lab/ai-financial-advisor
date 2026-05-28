from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user_id
from backend.models import Category

router = APIRouter(prefix="/api/categories", tags=["categories"])

SYSTEM_CATEGORIES = [
    {"name": "餐饮", "icon": "🍜"},
    {"name": "交通", "icon": "🚗"},
    {"name": "购物", "icon": "🛒"},
    {"name": "娱乐", "icon": "🎮"},
    {"name": "医疗", "icon": "🏥"},
    {"name": "教育", "icon": "📚"},
    {"name": "居家", "icon": "🏠"},
    {"name": "工资", "icon": "💼"},
    {"name": "副业", "icon": "💡"},
    {"name": "其他", "icon": "📦"},
]


@router.get("")
def list_categories(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    cats = db.query(Category).filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()
    return cats


def seed_categories(db: Session):
    existing = db.query(Category).filter(Category.user_id == None).count()
    if existing == 0:
        for c in SYSTEM_CATEGORIES:
            db.add(Category(**c))
        db.commit()
