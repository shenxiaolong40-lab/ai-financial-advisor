import httpx
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import AISession
from backend.services.fire_service import calculate_fire_status

CHAT_MODEL = "deepseek-chat"
DEEPSEEK_BASE = "https://api.deepseek.com"
MAX_TOKENS = 1024
CONTEXT_ROUNDS = 5

SYSTEM_PROMPT = """你是一位专注于 FIRE（财务独立、提前退休）的财务自由顾问。

核心职责：
- 帮助用户通过提高储蓄率、优化支出结构、合理配置资产来提前实现财务自由
- 所有建议必须包含：具体金额、对储蓄率的影响、预计提前自由的年数
- 用数字说话，不说"可能""也许"等模糊词
- 建议要具体可执行，不讨论与财务自由无关的话题
- 回复控制在 300 字以内，关键数字用**加粗**

FIRE 基础知识：
- FIRE 数字 = 年均支出 × 25（4% 安全提取率法则）
- 储蓄率是最关键的杠杆：储蓄率 50% 约 17 年自由，储蓄率 75% 约 7 年
- 资产配置建议：指数基金（全市场/沪深300）长期年化约 7-10%"""


def _key_valid() -> bool:
    k = settings.deepseek_api_key
    return bool(k) and k.startswith("sk-") and len(k) > 10


def _build_fire_context(db: Session, user_id: int) -> str:
    try:
        status = calculate_fire_status(db, user_id)
    except Exception:
        return "（暂无财务数据，请先录入收入和资产信息）"

    years_str = f"{status['years_to_fire']} 年" if status['years_to_fire'] is not None else "无法计算（支出超过收入）"

    cat_lines = "\n".join(
        f"  - {c['icon']}{c['name']}: ¥{c['amount']:.0f}/月（{c['pct']}%）"
        for c in status["category_breakdown"][:6]
    ) or "  暂无支出数据"

    assets = status["asset_breakdown"]
    total = status["total_assets"]

    return (
        f"【用户当前 FIRE 状态】\n"
        f"FIRE 数字：¥{status['fire_number']:,.0f}（目标净资产）\n"
        f"当前总资产：¥{total:,.0f}（完成度 {status['progress_pct']}%）\n"
        f"  现金/货基：¥{assets['cash']:,.0f}\n"
        f"  股票/基金：¥{assets['stock']:,.0f}\n"
        f"  房产：¥{assets['real_estate']:,.0f}\n"
        f"  其他：¥{assets['other']:,.0f}\n"
        f"月收入：¥{status['monthly_income']:,.0f}\n"
        f"月均支出（近3月）：¥{status['avg_monthly_expense']:,.0f}\n"
        f"月储蓄：¥{status['monthly_savings']:,.0f}（储蓄率 {status['savings_rate']}%）\n"
        f"预计财务自由：{years_str}（年化 {status['expected_return']*100:.0f}% 收益）\n\n"
        f"近3月支出分布：\n{cat_lines}"
    )


def _get_history(db: Session, user_id: int) -> list:
    sessions = (
        db.query(AISession)
        .filter(AISession.user_id == user_id)
        .order_by(AISession.created_at.desc())
        .limit(CONTEXT_ROUNDS * 2)
        .all()
    )
    return [{"role": s.role, "content": s.content} for s in reversed(sessions) if s.role in ("user", "assistant")]


def _save_message(db: Session, role: str, content: str, user_id: int, tokens: int = 0):
    db.add(AISession(user_id=user_id, role=role, content=content, tokens_used=tokens))
    db.commit()
    total = db.query(AISession).filter(AISession.user_id == user_id).count()
    if total > 50:
        oldest = (
            db.query(AISession)
            .filter(AISession.user_id == user_id)
            .order_by(AISession.created_at.asc())
            .limit(total - 50)
            .all()
        )
        for o in oldest:
            db.delete(o)
        db.commit()


async def _call_deepseek(system: str, messages: list) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": CHAT_MODEL,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "system", "content": system}] + messages,
            },
        )
        if resp.status_code == 401:
            raise ValueError("API Key 无效，请检查 .env 中的 DEEPSEEK_API_KEY")
        if resp.status_code == 402:
            raise ValueError("账户余额不足，请前往 DeepSeek 平台充值")
        resp.raise_for_status()
        return resp.json()


async def chat(message: str, db: Session, user_id: int = 1) -> dict:
    if not _key_valid():
        return {"reply": "未配置有效的 DEEPSEEK_API_KEY，请编辑 .env 文件。", "tokens": 0}

    fire_context = _build_fire_context(db, user_id)
    history = _get_history(db, user_id)
    system = SYSTEM_PROMPT + "\n\n" + fire_context
    messages = history + [{"role": "user", "content": message}]

    try:
        data = await _call_deepseek(system, messages)
    except ValueError as e:
        return {"reply": str(e), "tokens": 0}
    except httpx.TimeoutException:
        return {"reply": "请求超时，请稍后重试。", "tokens": 0}
    except httpx.RequestError as e:
        return {"reply": f"网络错误：{str(e)}", "tokens": 0}

    reply = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("completion_tokens", 0)
    _save_message(db, "user", message, user_id)
    _save_message(db, "assistant", reply, user_id, tokens)
    return {"reply": reply, "tokens": tokens}


async def generate_analysis(db: Session, user_id: int = 1) -> dict:
    if not _key_valid():
        return {"report": "未配置有效的 DEEPSEEK_API_KEY，请编辑 .env 文件。"}

    fire_context = _build_fire_context(db, user_id)

    analysis_prompt = (
        SYSTEM_PROMPT + "\n\n" + fire_context + "\n\n"
        "请生成一份 FIRE 优化报告，格式：\n"
        "**核心指标**（1句话总结储蓄率和距离自由年数）\n\n"
        "**提升收入**（1条具体建议 + 预期影响）\n\n"
        "**压缩支出**（从支出分布中找出最值得削减的1-2项，含具体金额和可提前的年数）\n\n"
        "**资产配置**（根据当前资产结构给出1条调整建议）\n\n"
        "总字数不超过 300 字。"
    )

    try:
        data = await _call_deepseek(
            analysis_prompt,
            [{"role": "user", "content": "请生成我的 FIRE 优化报告"}],
        )
    except ValueError as e:
        return {"report": str(e)}
    except httpx.TimeoutException:
        return {"report": "请求超时，请稍后重试。"}
    except httpx.RequestError as e:
        return {"report": f"网络错误：{str(e)}"}

    reply = data["choices"][0]["message"]["content"]
    _save_message(db, "assistant", reply, user_id, data.get("usage", {}).get("completion_tokens", 0))
    return {"report": reply}
