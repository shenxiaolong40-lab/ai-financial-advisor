from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.models import Transaction, Budget, Goal, IncomeProfile, Category

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DEFAULT_USER_ID = 1


@router.get("/summary")
def get_summary(
    month: Optional[str] = Query(None, description="YYYY-MM, defaults to current month"),
    db: Session = Depends(get_db),
):
    if not month:
        now = datetime.now()
        month = f"{now.year:04d}-{now.month:02d}"

    year, m = int(month[:4]), int(month[5:7])
    start = date(year, m, 1)
    end = date(year + 1, 1, 1) if m == 12 else date(year, m + 1, 1)

    txns = db.query(Transaction).filter(
        Transaction.user_id == DEFAULT_USER_ID,
        Transaction.date >= start,
        Transaction.date < end,
    ).all()

    total_income = sum(t.amount for t in txns if t.type == "income")
    total_expense = sum(t.amount for t in txns if t.type == "expense")
    balance = total_income - total_expense

    # category breakdown for expenses
    cat_map: dict[str, float] = {}
    cat_icon_map: dict[str, str] = {}
    for t in txns:
        if t.type == "expense":
            label = t.category.name if t.category else "其他"
            icon = t.category.icon if t.category else "📦"
            cat_map[label] = cat_map.get(label, 0) + t.amount
            cat_icon_map[label] = icon

    category_breakdown = [
        {"name": k, "icon": cat_icon_map[k], "amount": round(v, 2)}
        for k, v in sorted(cat_map.items(), key=lambda x: -x[1])
    ]

    # budget progress
    budgets = db.query(Budget).filter(Budget.user_id == DEFAULT_USER_ID).all()
    budget_progress = []
    for b in budgets:
        if b.category_id:
            spent = sum(t.amount for t in txns if t.type == "expense" and t.category_id == b.category_id)
            cat = db.get(Category, b.category_id)
            label = cat.name if cat else "未知"
            icon = cat.icon if cat else "📦"
        else:
            spent = total_expense
            label = "总预算"
            icon = "💰"
        budget_progress.append({
            "id": b.id,
            "name": label,
            "icon": icon,
            "limit": b.limit_amount,
            "spent": round(spent, 2),
            "percent": round(spent / b.limit_amount * 100, 1) if b.limit_amount > 0 else 0,
        })

    # goals snapshot
    goals = db.query(Goal).filter(Goal.user_id == DEFAULT_USER_ID).all()
    goals_snapshot = [
        {
            "id": g.id,
            "name": g.name,
            "target": g.target_amount,
            "current": g.current_amount,
            "percent": round(g.current_amount / g.target_amount * 100, 1) if g.target_amount > 0 else 0,
            "deadline": g.deadline.isoformat() if g.deadline else None,
        }
        for g in goals
    ]

    # recent 5 transactions
    recent = sorted(txns, key=lambda t: t.date, reverse=True)[:5]
    recent_txns = [
        {
            "id": t.id,
            "date": t.date.isoformat(),
            "amount": t.amount,
            "type": t.type,
            "description": t.description,
            "merchant": t.merchant,
            "category_name": t.category.name if t.category else None,
            "category_icon": t.category.icon if t.category else "📦",
        }
        for t in recent
    ]

    income_profile = db.query(IncomeProfile).filter(IncomeProfile.user_id == DEFAULT_USER_ID).first()
    monthly_income_set = income_profile.monthly_income if income_profile else 0

    return {
        "month": month,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance": round(balance, 2),
        "monthly_income_set": monthly_income_set,
        "category_breakdown": category_breakdown,
        "budget_progress": budget_progress,
        "goals_snapshot": goals_snapshot,
        "recent_transactions": recent_txns,
    }


def _prev_month(year: int, m: int, n: int):
    """Return (year, month) n months before (year, m)."""
    total = year * 12 + (m - 1) - n
    return total // 12, total % 12 + 1


@router.get("/trend")
def get_trend(
    months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    now = datetime.now()
    result = []
    for i in range(months - 1, -1, -1):
        y, m = _prev_month(now.year, now.month, i)
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        txns = db.query(Transaction).filter(
            Transaction.user_id == DEFAULT_USER_ID,
            Transaction.date >= start,
            Transaction.date < end,
        ).all()
        income = sum(t.amount for t in txns if t.type == "income")
        expense = sum(t.amount for t in txns if t.type == "expense")
        result.append({
            "month": f"{y:04d}-{m:02d}",
            "income": round(income, 2),
            "expense": round(expense, 2),
            "balance": round(income - expense, 2),
        })
    return result
