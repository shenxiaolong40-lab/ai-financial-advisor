"""
账单 CSV 解析器 — 支持支付宝、微信格式
两个平台的导出文件都包含若干头部行，实际数据从表头行后开始。
"""
from __future__ import annotations
import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from backend.models import Transaction, Category

# 支付宝表头关键列名
ALIPAY_HEADERS = {
    "time": "交易时间",
    "category": "交易分类",
    "counterpart": "交易对方",
    "goods": "商品名称",
    "direction": "收/支",
    "amount": "金额(元)",
    "status": "当前状态",
    "order_id": "交易单号",
}

# 微信表头关键列名
WECHAT_HEADERS = {
    "time": "交易时间",
    "tx_type": "交易类型",
    "counterpart": "交易对方",
    "goods": "商品",
    "direction": "收/支",
    "amount": "金额(元)",
    "status": "当前状态",
    "order_id": "交易单号",
}

# 分类名称关键词 → 系统分类 ID 映射（按种子数据顺序）
# 餐饮=1 交通=2 购物=3 娱乐=4 医疗=5 教育=6 居家=7 工资=8 副业=9 其他=10
CATEGORY_KEYWORDS: list[tuple[list[str], int]] = [
    (["餐饮", "美食", "外卖", "超市", "便利", "生鲜", "水果", "饮食", "食品", "奶茶", "咖啡", "快餐"], 1),
    (["交通", "滴滴", "出行", "打车", "地铁", "公交", "停车", "加油", "高速", "机票", "火车", "高铁"], 2),
    (["购物", "电商", "京东", "天猫", "淘宝", "拼多多", "服饰", "鞋", "数码", "家电", "百货"], 3),
    (["娱乐", "游戏", "电影", "视频", "音乐", "ktv", "健身", "运动", "旅游"], 4),
    (["医疗", "医院", "药店", "诊所", "挂号", "药品"], 5),
    (["教育", "学习", "培训", "书", "课程", "考试"], 6),
    (["居家", "房租", "水电", "物业", "家居", "装修", "宽带"], 7),
    (["工资", "薪资", "薪水", "奖金"], 8),
    (["副业", "兼职", "稿费", "佣金", "分红"], 9),
]


@dataclass
class ParsedRow:
    date: str           # YYYY-MM-DD
    amount: float
    tx_type: str        # income / expense
    merchant: str
    description: str
    sync_source: str    # alipay / wechat
    sync_id: str
    raw_category: str   # 原始分类文本，用于自动映射


def _clean_amount(raw: str) -> float:
    return float(raw.strip().lstrip("¥").lstrip("￥").replace(",", "") or "0")


def _guess_category_id(merchant: str, description: str, raw_category: str) -> Optional[int]:
    text = (merchant + description + raw_category).lower()
    for keywords, cat_id in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return cat_id
    return None


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _find_header_row(rows: list[list[str]], key: str) -> int:
    for i, row in enumerate(rows):
        if row and key in row[0]:
            return i
    return -1


# ─── 支付宝 ─────────────────────────────────────────────────────────────────

def parse_alipay(data: bytes) -> list[ParsedRow]:
    text = _decode_bytes(data)
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader]

    header_idx = _find_header_row(rows, "交易时间")
    if header_idx == -1:
        raise ValueError("未找到支付宝账单表头，请确认文件格式正确")

    header = [h.strip() for h in rows[header_idx]]
    result: list[ParsedRow] = []

    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip() or row[0].strip().startswith("-"):
            continue
        try:
            r = {header[i]: row[i].strip() for i in range(min(len(header), len(row)))}
        except IndexError:
            continue

        direction = r.get("收/支", "").strip()
        if direction not in ("收入", "支出"):
            continue  # 跳过"不计收支"

        status = r.get("当前状态", "")
        if "退款" in status or "关闭" in status or "失败" in status:
            continue

        try:
            amount = _clean_amount(r.get("金额(元)", "0"))
            if amount <= 0:
                continue
        except ValueError:
            continue

        raw_time = r.get("交易时间", "").strip()
        try:
            dt = datetime.strptime(raw_time[:19], "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        merchant = r.get("交易对方", "").strip()
        description = r.get("商品名称", "").strip()
        sync_id = r.get("交易单号", "").strip()
        raw_category = r.get("交易分类", "").strip()

        result.append(ParsedRow(
            date=date_str,
            amount=amount,
            tx_type="income" if direction == "收入" else "expense",
            merchant=merchant,
            description=description,
            sync_source="alipay",
            sync_id=sync_id,
            raw_category=raw_category,
        ))

    return result


# ─── 微信 ────────────────────────────────────────────────────────────────────

def parse_wechat(data: bytes) -> list[ParsedRow]:
    text = _decode_bytes(data)
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader]

    header_idx = _find_header_row(rows, "交易时间")
    if header_idx == -1:
        raise ValueError("未找到微信账单表头，请确认文件格式正确")

    header = [h.strip() for h in rows[header_idx]]
    result: list[ParsedRow] = []

    for row in rows[header_idx + 1:]:
        if not row or not row[0].strip() or row[0].strip().startswith("-"):
            continue
        try:
            r = {header[i]: row[i].strip() for i in range(min(len(header), len(row)))}
        except IndexError:
            continue

        direction = r.get("收/支", "").strip()
        if direction not in ("收入", "支出"):
            continue

        status = r.get("当前状态", "")
        if "退款" in status or "已退款" in status:
            continue

        try:
            amount = _clean_amount(r.get("金额(元)", "0"))
            if amount <= 0:
                continue
        except ValueError:
            continue

        raw_time = r.get("交易时间", "").strip()
        try:
            dt = datetime.strptime(raw_time[:19], "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        merchant = r.get("交易对方", "").strip()
        description = r.get("商品", "").strip()
        sync_id = r.get("交易单号", "").strip()
        raw_category = r.get("交易类型", "").strip()

        result.append(ParsedRow(
            date=date_str,
            amount=amount,
            tx_type="income" if direction == "收入" else "expense",
            merchant=merchant,
            description=description,
            sync_source="wechat",
            sync_id=sync_id,
            raw_category=raw_category,
        ))

    return result


# ─── 写入数据库 ───────────────────────────────────────────────────────────────

def import_rows(rows: list[ParsedRow], db: Session, user_id: int = 1) -> dict:
    inserted = 0
    skipped = 0

    for row in rows:
        if row.sync_id:
            exists = db.query(Transaction).filter(
                Transaction.sync_source == row.sync_source,
                Transaction.sync_id == row.sync_id,
            ).first()
            if exists:
                skipped += 1
                continue

        cat_id = _guess_category_id(row.merchant, row.description, row.raw_category)

        from datetime import date as PyDate
        try:
            txn_date = PyDate.fromisoformat(row.date)
        except ValueError:
            skipped += 1
            continue

        txn = Transaction(
            user_id=user_id,
            category_id=cat_id,
            amount=row.amount,
            type=row.tx_type,
            date=txn_date,
            description=row.description,
            merchant=row.merchant,
            sync_source=row.sync_source,
            sync_id=row.sync_id or None,
        )
        db.add(txn)
        inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "total": len(rows)}
