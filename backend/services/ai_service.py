import httpx
from datetime import datetime, date
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import Transaction, Budget, Goal, IncomeProfile, AISession, Category

DEFAULT_USER_ID = 1
CHAT_MODEL = "claude-haiku-4-5-20251001"
ANALYSIS_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
CONTEXT_ROUNDS = 5


def _current_month() -> tuple:
    now = datetime.now()
    start = date(now.year, now.month, 1)
    end = date(now.year + 1, 1, 1) if now.month == 12 else date(now.year, now.month + 1, 1)
    return start, end


def _build_financial_context(db: Session) -> str:
    start, end = _current_month()
    now = datetime.now()
    month_label = f"{now.year}年{now.month}月"

    txns = db.query(Transaction).filter(
        Transaction.user_id == DEFAULT_USER_ID,
        Transaction.date >= start,
        Transaction.date < end,
    ).all()

    total_income = sum(t.amount for t in txns if t.type == "income")
    total_expense = sum(t.amount for t in txns if t.type == "expense")
    balance = total_income - total_expense

    cat_map: dict = {}
    for t in txns:
        if t.type == "expense":
            label = t.category.name if t.category else "其他"
            cat_map[label] = cat_map.get(label, 0) + t.amount
    category_lines = "\n".join(
        f"  - {k}: ¥{v:.0f}"
        for k, v in sorted(cat_map.items(), key=lambda x: -x[1])
    ) or "  暂无支出数据"

    budgets = db.query(Budget).filter(Budget.user_id == DEFAULT_USER_ID).all()
    budget_lines = []
    for b in budgets:
        if b.category_id:
            spent = sum(t.amount for t in txns if t.type == "expense" and t.category_id == b.category_id)
            cat = db.get(Category, b.category_id)
            name = cat.name if cat else "未知"
        else:
            spent = total_expense
            name = "总预算"
        pct = spent / b.limit_amount * 100 if b.limit_amount > 0 else 0
        status = "⚠️ 超支" if pct >= 100 else ("🔶 接近上限" if pct >= 80 else "✅ 正常")
        budget_lines.append(f"  - {name}: 已用¥{spent:.0f}/上限¥{b.limit_amount:.0f}（{pct:.0f}%）{status}")
    budget_section = "\n".join(budget_lines) or "  暂无预算设置"

    goals = db.query(Goal).filter(Goal.user_id == DEFAULT_USER_ID).all()
    goal_lines = []
    for g in goals:
        pct = g.current_amount / g.target_amount * 100 if g.target_amount > 0 else 0
        deadline_str = f"，截止 {g.deadline}" if g.deadline else ""
        remaining = g.target_amount - g.current_amount
        goal_lines.append(
            f"  - {g.name}: 已存¥{g.current_amount:.0f}/目标¥{g.target_amount:.0f}（{pct:.0f}%）"
            f"，还差¥{remaining:.0f}{deadline_str}"
        )
    goals_section = "\n".join(goal_lines) or "  暂无储蓄目标"

    income_profile = db.query(IncomeProfile).filter(IncomeProfile.user_id == DEFAULT_USER_ID).first()
    monthly_income_set = income_profile.monthly_income if income_profile else 0
    monthly_extra = income_profile.monthly_extra if income_profile else 0
    saving_rate = (balance / total_income * 100) if total_income > 0 else 0

    return f"""【{month_label}财务数据】
月固定收入设置：¥{monthly_income_set:.0f}（额外收入均值：¥{monthly_extra:.0f}）
本月实际收入：¥{total_income:.0f}
本月总支出：¥{total_expense:.0f}
本月结余：¥{balance:.0f}（储蓄率 {saving_rate:.1f}%）

本月支出分类：
{category_lines}

预算执行情况：
{budget_section}

储蓄目标进度：
{goals_section}"""


def _get_conversation_history(db: Session) -> list:
    sessions = (
        db.query(AISession)
        .filter(AISession.user_id == DEFAULT_USER_ID)
        .order_by(AISession.created_at.desc())
        .limit(CONTEXT_ROUNDS * 2)
        .all()
    )
    sessions = list(reversed(sessions))
    return [{"role": s.role, "content": s.content} for s in sessions if s.role in ("user", "assistant")]


def _save_message(db: Session, role: str, content: str, tokens: int = 0):
    msg = AISession(user_id=DEFAULT_USER_ID, role=role, content=content, tokens_used=tokens)
    db.add(msg)
    db.commit()

    total = db.query(AISession).filter(AISession.user_id == DEFAULT_USER_ID).count()
    if total > 50:
        oldest = (
            db.query(AISession)
            .filter(AISession.user_id == DEFAULT_USER_ID)
            .order_by(AISession.created_at.asc())
            .limit(total - 50)
            .all()
        )
        for o in oldest:
            db.delete(o)
        db.commit()


def _key_valid() -> bool:
    k = settings.anthropic_api_key
    return bool(k) and k != "your_anthropic_api_key_here" and k.startswith("sk-")


async def chat(message: str, db: Session, deep: bool = False) -> dict:
    if not _key_valid():
        return {"reply": "❌ 未配置有效的 ANTHROPIC_API_KEY。\n\n请编辑 `backend/.env` 文件，将 `ANTHROPIC_API_KEY=` 后面填入你的 Anthropic API Key（以 `sk-ant-` 开头）。", "tokens": 0}

    financial_context = _build_financial_context(db)
    history = _get_conversation_history(db)

    system_prompt = f"""你是一位专业的个人财务顾问，你直接访问用户的真实财务数据并给出精准建议。

分析规则：
- 用具体数字说话，不说"可能"、"也许"等模糊词
- 发现异常波动要明确指出
- 给出的建议要可执行：具体金额、具体行动
- 语气友好鼓励，不制造焦虑
- 回复控制在 200 字以内，关键数字用**加粗**

{financial_context}"""

    messages = history + [{"role": "user", "content": message}]
    model = ANALYSIS_MODEL if deep else CHAT_MODEL

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": MAX_TOKENS,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
            if resp.status_code == 401:
                return {"reply": "❌ API Key 无效，请检查 .env 文件中的 ANTHROPIC_API_KEY 是否正确。", "tokens": 0}
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return {"reply": "⏱️ 请求超时，请稍后重试。", "tokens": 0}
    except httpx.RequestError as e:
        return {"reply": f"🌐 网络错误：{str(e)}", "tokens": 0}

    reply = data["content"][0]["text"]
    tokens = data.get("usage", {}).get("output_tokens", 0)

    _save_message(db, "user", message)
    _save_message(db, "assistant", reply, tokens)

    return {"reply": reply, "tokens": tokens, "model": model}


async def generate_analysis(db: Session) -> dict:
    if not _key_valid():
        return {"report": "❌ 未配置有效的 ANTHROPIC_API_KEY，请编辑 `backend/.env` 文件。"}

    financial_context = _build_financial_context(db)

    system_prompt = """你是一位个人财务分析师。根据用户本月的财务数据，生成一份简洁的分析报告。

报告格式（严格遵守）：
1. 📊 本月总结（2句话）
2. 🔍 重点发现（2-3个具体数字发现）
3. 💡 行动建议（2条具体可执行建议）

每条控制在 1-2 句话，关键数字**加粗**，总字数不超过 250 字。"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANALYSIS_MODEL,
                    "max_tokens": 600,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": financial_context}],
                },
            )
            if resp.status_code == 401:
                return {"report": "❌ API Key 无效，请检查 .env 文件。"}
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return {"report": "⏱️ 请求超时，请稍后重试。"}
    except httpx.RequestError as e:
        return {"report": f"🌐 网络错误：{str(e)}"}

    reply = data["content"][0]["text"]
    _save_message(db, "assistant", reply, data.get("usage", {}).get("output_tokens", 0))
    return {"report": reply}
