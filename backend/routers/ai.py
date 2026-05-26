from fastapi import APIRouter

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health")
def ai_health():
    return {"status": "AI router placeholder — Phase 3"}
