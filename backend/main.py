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
    """SQLite 字段迁移：新增 FIRE 新模型字段，并从旧字段迁移数据"""
    from sqlalchemy import text
    from backend.database import engine
    new_cols = [
        ("total_assets",         0.0),
        ("annual_salary",        0.0),
        ("salary_growth_rate",   0.05),
        ("annual_fixed_expense", 0.0),
        ("annual_flex_expense",  0.0),
        ("annual_return",        0.05),
    ]
    with engine.connect() as conn:
        for col, default in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE fire_profiles ADD COLUMN {col} FLOAT DEFAULT {default}"))
                conn.execute(text(f"UPDATE fire_profiles SET {col} = {default} WHERE {col} IS NULL"))
                conn.commit()
            except Exception:
                pass  # 字段已存在，忽略

        # 从旧字段迁移数据（仅当新字段仍为默认零值时执行）
        try:
            # total_assets = 四类资产之和
            conn.execute(text(
                "UPDATE fire_profiles SET total_assets = "
                "COALESCE(cash_assets,0)+COALESCE(stock_assets,0)+"
                "COALESCE(real_estate_assets,0)+COALESCE(other_assets,0) "
                "WHERE total_assets = 0 AND ("
                "COALESCE(cash_assets,0)+COALESCE(stock_assets,0)+"
                "COALESCE(real_estate_assets,0)+COALESCE(other_assets,0)) > 0"
            ))
            # annual_salary = monthly_fixed_income * 12
            conn.execute(text(
                "UPDATE fire_profiles SET annual_salary = monthly_fixed_income * 12 "
                "WHERE annual_salary = 0 AND COALESCE(monthly_fixed_income,0) > 0"
            ))
            # annual_fixed_expense = monthly_expense * 12（旧月均支出全部归入刚性支出）
            conn.execute(text(
                "UPDATE fire_profiles SET annual_fixed_expense = monthly_expense * 12 "
                "WHERE annual_fixed_expense = 0 AND COALESCE(monthly_expense,0) > 0"
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
