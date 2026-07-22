"""
财务自由（FIRE）核心计算服务

定义：被动收入（资产 × 年化收益率）≥ 年度总支出
模型：工资结余每年投入资产池，资产复利增长，直到被动收入覆盖通胀后的支出。

计算公式：
  E(n)      = E × (1+i)^n              支出随通胀增长，i=2.5%
  S(n)      = S × (1+g_s)^n            工资逐年增长
  A(n)      = A(n-1)×(1+r) + S(n)-E(n) 逐年资产递推
  FIRE条件   = A(n) × r ≥ E(n)          被动收入覆盖当年支出
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from datetime import date

from backend.models import FireProfile, Transaction

INFLATION = 0.025  # 年通胀率，内置常量
MAX_YEARS = 100


def get_or_create_profile(db: Session, user_id: int) -> FireProfile:
    profile = db.query(FireProfile).filter(FireProfile.user_id == user_id).first()
    if not profile:
        profile = FireProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _expense_by_category(db: Session, user_id: int, months: int = 3) -> list[dict]:
    """近 N 个月各分类支出占比（用于前端饼图展示）"""
    today = date.today()
    yr, mo = today.year, today.month - months
    while mo <= 0:
        mo += 12
        yr -= 1
    start = date(yr, mo, 1)

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
        cat_map.setdefault(name, {"name": name, "icon": icon, "amount": 0.0})
        cat_map[name]["amount"] += t.amount
        total += t.amount

    result = sorted(cat_map.values(), key=lambda x: -x["amount"])
    for item in result:
        item["pct"] = round(item["amount"] / total * 100, 1) if total > 0 else 0.0
    return result


def _recent_monthly_avg(db: Session, user_id: int, tx_type: str, months: int = 3) -> float:
    """
    近 N 个月某类交易的月均值。
    tx_type: 'income' 或 'expense'。
    按"实际有交易的日历月"数平均（避免空月份稀释）。
    返回 0 表示无数据。
    """
    today = date.today()
    yr, mo = today.year, today.month - months
    while mo <= 0:
        mo += 12
        yr -= 1
    start = date(yr, mo, 1)

    txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.type == tx_type,
        Transaction.date >= start,
        Transaction.date <= today,
    ).all()

    if not txns:
        return 0.0

    total = sum(t.amount for t in txns)
    active_months = len({(t.date.year, t.date.month) for t in txns})
    return total / active_months


def _simulate(A0: float, S: float, g_s: float, E: float, r: float,
              max_years: int = MAX_YEARS) -> tuple[int | None, list[dict]]:
    """
    逐年递推，返回 (达标年数, 逐年数据列表)。
    达标年数为 None 表示 max_years 内无法达标。
    每条数据：year, assets, passive_income, expense, salary, surplus, fire_target
    """
    points = []
    assets = A0
    fire_year = None

    for n in range(1, max_years + 1):
        # n=1 对应设计文档第0年（当前年薪/支出，无增长），n-1 作为指数
        expense_n = E * ((1 + INFLATION) ** (n - 1))
        salary_n = S * ((1 + g_s) ** (n - 1))
        surplus_n = salary_n - expense_n
        assets = assets * (1 + r) + surplus_n
        passive_n = assets * r
        fire_target_n = expense_n / r if r > 0 else float("inf")

        points.append({
            "year": n,
            "assets": round(max(assets, 0), 0),
            "passive_income": round(passive_n, 0),
            "expense": round(expense_n, 0),
            "salary": round(salary_n, 0),
            "surplus": round(surplus_n, 0),
            "fire_target": round(fire_target_n, 0),
        })

        if fire_year is None and passive_n >= expense_n:
            fire_year = n

        # 资产归零后不可能再达标，提前终止（收益率为正时）
        if assets <= 0 and surplus_n < 0:
            break

    return fire_year, points


def calculate_fire_status(db: Session, user_id: int) -> dict:
    p = get_or_create_profile(db, user_id)

    A0 = p.total_assets
    g_s = p.salary_growth_rate
    r = p.annual_return

    # 优先用交易表聚合值（近3月平均×12年化），无数据则降级到手动配置
    tx_monthly_expense = _recent_monthly_avg(db, user_id, "expense", months=3)
    tx_monthly_income = _recent_monthly_avg(db, user_id, "income", months=3)

    E_tx = tx_monthly_expense * 12
    S_tx = tx_monthly_income * 12

    E_fixed = p.annual_fixed_expense
    E_flex = p.annual_flex_expense
    E_manual = E_fixed + E_flex
    S_manual = p.annual_salary

    use_tx_expense = E_tx > 0
    use_tx_income = S_tx > 0

    E = E_tx if use_tx_expense else E_manual
    S = S_tx if use_tx_income else S_manual

    data_source = {
        "expense": "transactions" if use_tx_expense else ("manual" if E_manual > 0 else "none"),
        "income":  "transactions" if use_tx_income  else ("manual" if S_manual > 0 else "none"),
        "tx_monthly_expense": round(tx_monthly_expense, 2),
        "tx_monthly_income":  round(tx_monthly_income, 2),
        "manual_annual_expense": round(E_manual, 2),
        "manual_annual_salary":  round(S_manual, 2),
    }

    current_passive = A0 * r
    already_free = (E > 0) and (current_passive >= E)

    annual_surplus = S - E
    savings_rate = (annual_surplus / S * 100) if S > 0 else 0.0
    passive_coverage_pct = (current_passive / E * 100) if E > 0 else 0.0

    has_data = E > 0

    if already_free:
        years_to_fire = 0
        fire_detail = None
    elif not has_data or r <= 0:
        years_to_fire = None
        fire_detail = None
    else:
        fire_year, _ = _simulate(A0, S, g_s, E, r)
        years_to_fire = fire_year  # None = 无法达标

        fire_detail = None
        if fire_year is not None:
            # 重新跑一次拿达标年详情
            _, points = _simulate(A0, S, g_s, E, r, max_years=fire_year)
            pt = points[-1]
            fire_detail = {
                "target_assets": pt["fire_target"],
                "passive_income_at_fire": pt["passive_income"],
                "expense_at_fire": pt["expense"],
            }

    # 敏感性分析：r-1% / r / r+1%
    sensitivity = []
    for delta in (-0.01, 0.0, 0.01):
        r2 = max(r + delta, 0.001)
        fy, _ = _simulate(A0, S, g_s, E, r2)
        sensitivity.append({
            "return_rate": round((r2) * 100, 1),
            "years_to_fire": fy,
        })

    return {
        "total_assets": round(A0, 2),
        "annual_salary": round(S, 2),
        "annual_expense": round(E, 2),
        "annual_fixed_expense": round(E_fixed, 2),
        "annual_flex_expense": round(E_flex, 2),
        "annual_return": round(r * 100, 2),          # 百分比
        "annual_surplus": round(annual_surplus, 2),
        "savings_rate": round(savings_rate, 1),
        "current_passive_income": round(current_passive, 2),
        "passive_coverage_pct": round(passive_coverage_pct, 1),
        "years_to_fire": years_to_fire,
        "already_free": already_free,
        "has_data": has_data,
        "fire_detail": fire_detail,
        "sensitivity": sensitivity,
        "category_breakdown": _expense_by_category(db, user_id),
        "data_source": data_source,
    }


def calculate_projection(db: Session, user_id: int, years: int = 35) -> list[dict]:
    """逐年预测曲线，最多到达标年+5年或 years，无法预测返回空列表"""
    p = get_or_create_profile(db, user_id)
    E = p.annual_fixed_expense + p.annual_flex_expense
    if E <= 0 or p.annual_return <= 0:
        return []

    fire_year, points = _simulate(
        p.total_assets, p.annual_salary, p.salary_growth_rate,
        E, p.annual_return, max_years=years,
    )

    # 截到达标年+5年（最多 years）
    cap = min((fire_year + 5) if fire_year else years, years, len(points))
    return points[:cap]
