from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.deps import get_current_user_id
from backend.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(body: ChatRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    if not body.message.strip():
        raise HTTPException(400, "消息不能为空")
    result = await ai_service.chat(body.message, db, user_id=user_id)
    return result


@router.post("/analysis")
async def analysis(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    result = await ai_service.generate_analysis(db, user_id=user_id)
    return result


@router.get("/history")
def get_history(limit: int = 20, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    from backend.models import AISession
    sessions = (
        db.query(AISession)
        .filter(AISession.user_id == user_id)
        .order_by(AISession.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"role": s.role, "content": s.content, "created_at": s.created_at.isoformat()}
        for s in reversed(sessions)
    ]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    from backend.models import AISession
    db.query(AISession).filter(AISession.user_id == user_id).delete()
    db.commit()
    return {"status": "cleared"}
