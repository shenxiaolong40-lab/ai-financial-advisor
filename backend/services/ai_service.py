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

FIRE 核心模型：
- 财务自由 = 被动收入（资产 × 年化收益率）≥ 年度总支出
- 工资是资产积累的引擎，不是被动收入
- 通胀率 2.5% 内置，支出和所需资产每年自然增长
- 储蓄率是最关键的杠杆：储蓄率 50% 约 17 年，储蓄率 75% 约 7 年
- 资产配置建议：指数基金（全市场/沪深300）长期年化约 7-10%"""


def _key_valid() -> bool:
    k = settings.deepseek_api_key
    return bool(k) and k.startswith("sk-") and len(k) > 10


def _build_fire_context(db: Session, user_id: int) -> str:
    try:
        status = calculate_fire_status(db, user_id)
    except Exception:
        return "（暂无财务数据，请先录入收入和资产信息）"

    if status["already_free"]:
        years_str = "已实现财务自由 🎉"
    elif status["years_to_fire"] is None:
        years_str = "按当前参数 100 年内无法达标"
    else:
        years_str = f"{status['years_to_fire']} 年"

    fd = status.get("fire_detail") or {}
    sensitivity = status.get("sensitivity", [])
    sens_lines = "\n".join(
        f"  收益率 {s['return_rate']}%：{s['years_to_fire']} 年" if s['years_to_fire'] else
        f"  收益率 {s['return_rate']}%：无法达标"
        for s in sensitivity
    )

    ds = status.get("data_source") or {}
    src_cn = {"transactions": "近3月交易记录年化", "manual": "手动配置", "none": "未填写"}
    income_src = src_cn.get(ds.get("income"), "未知")
    expense_src = src_cn.get(ds.get("expense"), "未知")

    return (
        f"【用户当前 FIRE 状态】\n"
        f"当前总资产：¥{status['total_assets']:,.0f}\n"
        f"年化理财收益率：{status['annual_return']}%\n"
        f"当前年被动收入（资产×收益率）：¥{status['current_passive_income']:,.0f}\n"
        f"被动收入覆盖支出：{status['passive_coverage_pct']}%\n"
        f"年工资：¥{status['annual_salary']:,.0f}（数据来源：{income_src}）\n"
        f"年总支出：¥{status['annual_expense']:,.0f}（数据来源：{expense_src}）\n"
        f"  其中手动配置刚性支出：¥{status['annual_fixed_expense']:,.0f}\n"
        f"  其中手动配置弹性支出：¥{status['annual_flex_expense']:,.0f}\n"
        f"年结余（工资-支出）：¥{status['annual_surplus']:,.0f}（储蓄率 {status['savings_rate']}%）\n"
        f"预计财务自由：{years_str}\n"
        + (f"达标时资产：¥{fd.get('target_assets',0):,.0f}，"
           f"被动收入：¥{fd.get('passive_income_at_fire',0):,.0f}，"
           f"当年支出：¥{fd.get('expense_at_fire',0):,.0f}\n" if fd else "")
        + f"\n收益率敏感性分析：\n{sens_lines}"
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
        "**核心指标**（1句话总结当前被动覆盖率、储蓄率和距离自由年数）\n\n"
        "**提升收入**（1条具体建议 + 预期影响）\n\n"
        "**压缩支出**（指出弹性支出中最值得削减的方向，含具体金额和可提前的年数）\n\n"
        "**资产增值**（根据当前收益率给出1条提升建议）\n\n"
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
