"""
FIRE（财务独立、提前退休）核心计算服务
使用 4% 安全提取率法则：FIRE数字 = 年均支出 × 倍数（默认25）
各资产类别采用不同收益率，加权平均后代入复利公式。
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


def _weighted_return(profile: FireProfile) -> float:
    """按资产规模加权计算综合年化收益率"""
    assets = [
        (profile.cash_assets,         profile.cash_return),
        (profile.stock_assets,        profile.stock_return),
        (profile.real_estate_assets,  profile.real_estate_return),
        (profile.other_assets,        profile.other_return),
    ]
    total = sum(a for a, _ in assets)
    if total <= 0:
        # 无资产时用简单平均
        return sum(r for _, r in assets) / len(assets)
    return sum(a * r for a, r in assets) / total


def _avg_monthly_expense(db: Session, user_id: int, months: int = 3) -> float:
    """计算近 N 个月月均支出（基于实际交易记录）"""
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

    total = sum(t.amount for t in txns)
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

    # 月均支出：优先使用手动配置值（>0），否则从近3月账单自动计算
    txn_avg = _avg_monthly_expense(db, user_id, months=3)
    avg_expense = profile.monthly_expense if profile.monthly_expense > 0 else txn_avg
    expense_source = "manual" if profile.monthly_expense > 0 else "auto"

    weighted_return = _weighted_return(profile)

    # 固定收入（工资/副业等）
    monthly_fixed_income = profile.monthly_fixed_income
    # 理财收入 = 当前总资产 × 加权年化收益率 / 12（已通过复利体现，仅用于展示）
    monthly_investment_income = round(total_assets * weighted_return / 12, 2)
    # 月总收入（展示用）
    monthly_total_income = monthly_fixed_income + monthly_investment_income

    # FIRE 公式中月储蓄 = 固定收入 - 支出（理财收入通过复利已计入资产增长，不重复计）
    monthly_savings = monthly_fixed_income - avg_expense
    savings_rate = (monthly_savings / monthly_fixed_income * 100) if monthly_fixed_income > 0 else 0.0

    fire_number = avg_expense * 12 * profile.fire_multiplier
    years = _years_to_fire(total_assets, fire_number, monthly_savings, weighted_return)
    progress_pct = min(total_assets / fire_number * 100, 100.0) if fire_number > 0 else 0.0

    category_breakdown = _expense_by_category(db, user_id, months=3)

    return {
        "fire_number": round(fire_number, 2),
        "total_assets": round(total_assets, 2),
        "progress_pct": round(progress_pct, 1),
        # 收入明细
        "monthly_fixed_income": monthly_fixed_income,
        "monthly_investment_income": monthly_investment_income,
        "monthly_total_income": round(monthly_total_income, 2),
        "avg_monthly_expense": round(avg_expense, 2),
        "expense_source": expense_source,   # "manual" | "auto"
        "monthly_savings": round(monthly_savings, 2),
        "savings_rate": round(savings_rate, 1),
        "years_to_fire": round(years, 1) if years is not None else None,
        "weighted_return": round(weighted_return * 100, 2),   # 百分比，方便前端展示
        "fire_multiplier": profile.fire_multiplier,
        "asset_breakdown": {
            "cash":         {"amount": profile.cash_assets,        "return": profile.cash_return},
            "stock":        {"amount": profile.stock_assets,       "return": profile.stock_return},
            "real_estate":  {"amount": profile.real_estate_assets, "return": profile.real_estate_return},
            "other":        {"amount": profile.other_assets,       "return": profile.other_return},
        },
        "category_breakdown": category_breakdown,
        "has_data": avg_expense > 0,
    }


def calculate_projection(db: Session, user_id: int, years: int = 30) -> list[dict]:
    """生成资产增长预测曲线（年度数据点）；月储蓄≤0时返回空列表"""
    profile = get_or_create_profile(db, user_id)
    txn_avg = _avg_monthly_expense(db, user_id, months=3)
    avg_expense = profile.monthly_expense if profile.monthly_expense > 0 else txn_avg

    total_assets = (
        profile.cash_assets + profile.stock_assets
        + profile.real_estate_assets + profile.other_assets
    )
    monthly_savings = profile.monthly_fixed_income - avg_expense
    fire_number = avg_expense * 12 * profile.fire_multiplier
    r = _weighted_return(profile) / 12

    # 月储蓄为负时无法预测，直接返回空
    if monthly_savings <= 0 or fire_number <= 0:
        return []

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
