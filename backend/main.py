from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.config import settings
from backend.database import init_db
from backend.routers import transactions, accounts, categories, budgets, goals, income, dashboard, ai, imports, auth
from backend.routers import email_sync
from backend.routers.categories import seed_categories
from backend.database import SessionLocal

app = FastAPI(title="AI Finance Advisor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(income.router)
app.include_router(ai.router)
app.include_router(imports.router)
app.include_router(email_sync.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.user_mode}


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        from backend.models import User
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            db.add(User(id=1, single_user_mode=True))
            db.commit()
        seed_categories(db)
    finally:
        db.close()


# 前端静态文件 — 必须在所有 API 路由注册后再挂载，API 路由优先匹配
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
