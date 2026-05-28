"""
FIRE（财务独立、提前退休）核心计算服务
使用 4% 安全提取率法则：FIRE数字 = 年均支出 × 倍数（默认25）
"""
from __future__ import annotations

from datetime import date, datetime
from math import log
from typing import Optional

from sqlalchemy.orm import Session

from backend.models import FireProfile, Transaction


def get_or_create_profile(db: Session, user_id: int) -> FireProfile:
    profile = db.query(FireProfile).filter(FireProfile.user_id == user_id).first()
    if not profile:
        profile = FireProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _avg_monthly_expense(db: Session, user_id: int, months: int = 3) -> float:
    """计算近 N 个月月均支出（基于实际交易记录）"""
    today = date.today()
    # 往前推 months 个月
    year = today.year
    month = today.month - months
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)

    txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= start,
        Transaction.date <= today,
    ).all()

    total = sum(t.amount for t in txns)
    # 如果没有记录，返回 0（不是 None，让调用方判断）
    return total / months if total > 0 else 0.0


def _expense_by_category(db: Session, user_id: int, months: int = 3) -> list[dict]:
    """近 N 个月各分类支出占比"""
    today = date.today()
    year = today.year
    month = today.month - months
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)

    txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == "expense",
        Transaction.date >= start,
        Transaction.date <= today,
    ).all()

    cat_map: dict[str, dict] = {}
    total = 0.0
    for t in txns:
        name = t.category.name if t.category else "其他"
        icon = t.category.icon if t.category else "📦"
        if name not in cat_map:
            cat_map[name] = {"name": name, "icon": icon, "amount": 0.0}
        cat_map[name]["amount"] += t.amount
        total += t.amount

    result = sorted(cat_map.values(), key=lambda x: -x["amount"])
    for item in result:
        item["pct"] = round(item["amount"] / total * 100, 1) if total > 0 else 0.0
    return result


def _years_to_fire(
    current_assets: float,
    fire_number: float,
    monthly_savings: float,
    annual_return: float,
) -> Optional[float]:
    """复利计算距离 FIRE 的年数"""
    if current_assets >= fire_number:
        return 0.0
    if monthly_savings <= 0:
        return None  # 无法到达

    r = annual_return / 12  # 月化收益率
    if r <= 0:
        # 无收益时线性计算
        months = (fire_number - current_assets) / monthly_savings
        return months / 12

    # FV = PV*(1+r)^n + PMT*((1+r)^n - 1)/r
    # => (FV + PMT/r) = (PV + PMT/r)*(1+r)^n
    # => n = log((FV + PMT/r) / (PV + PMT/r)) / log(1+r)
    pmt_r = monthly_savings / r
    base = current_assets + pmt_r
    target = fire_number + pmt_r

    if base <= 0 or target <= 0:
        return None
    ratio = target / base
    if ratio <= 1:
        # base >= target 意味着初始资产已超过目标（含储蓄加速）
        return 0.0

    n_months = log(ratio) / log(1 + r)
    return n_months / 12


def calculate_fire_status(db: Session, user_id: int) -> dict:
    profile = get_or_create_profile(db, user_id)

    total_assets = (
        profile.cash_assets
        + profile.stock_assets
        + profile.real_estate_assets
        + profile.other_assets
    )

    avg_expense = _avg_monthly_expense(db, user_id, months=3)
    monthly_income = profile.monthly_income
    monthly_savings = monthly_income - avg_expense
    savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0.0

    fire_number = avg_expense * 12 * profile.fire_multiplier
    years = _years_to_fire(total_assets, fire_number, monthly_savings, profile.expected_return)
    progress_pct = min(total_assets / fire_number * 100, 100.0) if fire_number > 0 else 0.0

    category_breakdown = _expense_by_category(db, user_id, months=3)

    return {
        "fire_number": round(fire_number, 2),
        "total_assets": round(total_assets, 2),
        "progress_pct": round(progress_pct, 1),
        "monthly_income": monthly_income,
        "avg_monthly_expense": round(avg_expense, 2),
        "monthly_savings": round(monthly_savings, 2),
        "savings_rate": round(savings_rate, 1),
        "years_to_fire": round(years, 1) if years is not None else None,
        "expected_return": profile.expected_return,
        "fire_multiplier": profile.fire_multiplier,
        "asset_breakdown": {
            "cash": profile.cash_assets,
            "stock": profile.stock_assets,
            "real_estate": profile.real_estate_assets,
            "other": profile.other_assets,
        },
        "category_breakdown": category_breakdown,
        "has_data": avg_expense > 0,  # 是否有足够的交易数据
    }


def calculate_projection(db: Session, user_id: int, years: int = 30) -> list[dict]:
    """生成资产增长预测曲线（年度数据点）"""
    profile = get_or_create_profile(db, user_id)
    avg_expense = _avg_monthly_expense(db, user_id, months=3)

    total_assets = (
        profile.cash_assets + profile.stock_assets
        + profile.real_estate_assets + profile.other_assets
    )
    monthly_savings = profile.monthly_income - avg_expense
    fire_number = avg_expense * 12 * profile.fire_multiplier
    r = profile.expected_return / 12

    points = []
    assets = total_assets
    fire_reached_year = None

    for month in range(1, years * 12 + 1):
        assets = assets * (1 + r) + monthly_savings
        if month % 12 == 0:
            yr = month // 12
            if assets >= fire_number and fire_reached_year is None:
                fire_reached_year = yr
            points.append({
                "year": yr,
                "assets": round(max(assets, 0), 0),
                "fire_target": round(fire_number, 0),
            })

    return points
