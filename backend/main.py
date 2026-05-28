from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.config import settings
from backend.database import init_db
from backend.routers import transactions, categories, ai, imports, auth, fire
from backend.routers.categories import seed_categories
from backend.database import SessionLocal

app = FastAPI(title="财务自由顾问", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(fire.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(ai.router)
app.include_router(imports.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": settings.user_mode}


def _migrate_db():
    """SQLite 字段迁移：新增分类收益率字段"""
    from sqlalchemy import text
    from backend.database import engine
    new_cols = [
        ("monthly_expense",      10000.0),
        ("monthly_fixed_income", 0.0),
        ("cash_return",          0.02),
        ("stock_return",         0.08),
        ("real_estate_return",   0.04),
        ("other_return",         0.04),
    ]
    with engine.connect() as conn:
        for col, default in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE fire_profiles ADD COLUMN {col} FLOAT DEFAULT {default}"))
                conn.execute(text(f"UPDATE fire_profiles SET {col} = {default} WHERE {col} IS NULL"))
                conn.commit()
            except Exception:
                pass  # 字段已存在，忽略
        # 将旧 monthly_income 迁移到 monthly_fixed_income（老用户数据保留）
        try:
            conn.execute(text(
                "UPDATE fire_profiles SET monthly_fixed_income = monthly_income "
                "WHERE monthly_fixed_income = 0 AND monthly_income > 0"
            ))
            conn.commit()
        except Exception:
            pass


@app.on_event("startup")
def on_startup():
    init_db()
    _migrate_db()
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


# 前端静态文件 — 必须在所有 API 路由注册后再挂载
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
