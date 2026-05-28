"""
QQ 邮箱 IMAP 同步服务 — 解析银行交易提醒邮件，自动导入账单
支持：招商银行、工商银行、建设银行、农业银行、交通银行、浦发、中信、平安等主流银行
"""
from __future__ import annotations

import base64
import hashlib
import imaplib
import re
import ssl
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header, make_header
from typing import Optional

from backend.config import settings
from backend.services.sync_service import ParsedRow

# ── Fernet-compatible 加密（用 settings.secret_key 派生 32 字节密钥）────────────

def _get_fernet():
    from cryptography.fernet import Fernet
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_auth_code(auth_code: str) -> str:
    return _get_fernet().encrypt(auth_code.encode()).decode()


def decrypt_auth_code(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


# ── QQ IMAP 配置 ──────────────────────────────────────────────────────────────

QQ_IMAP_HOST = "imap.qq.com"
QQ_IMAP_PORT = 993

# 已知银行发件域名（用于邮件搜索）
BANK_SENDER_KEYWORDS = [
    "cmbchina.com",    # 招商银行
    "icbc.com.cn",     # 工商银行
    "ccb.com",         # 建设银行
    "abchina.com",     # 农业银行
    "bankcomm.com",    # 交通银行
    "spdb.com.cn",     # 浦发银行
    "citicbank.com",   # 中信银行
    "pingan.com",      # 平安银行
    "boc.cn",          # 中国银行
    "cgbchina.com.cn", # 广发银行
    "ceb.com.cn",      # 光大银行
    "hxb.com.cn",      # 华夏银行
    "minsheng",        # 民生银行
]

# 主题关键词（辅助过滤）
SUBJECT_KEYWORDS = ["消费", "交易提醒", "刷卡提醒", "账单提醒", "记账提醒", "扣款提醒"]


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _decode_str(s: str) -> str:
    """解码邮件头中的编码字符串"""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def _get_text_body(msg) -> str:
    """从 email.message 中提取纯文本内容"""
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                charset = part.get_content_charset() or "utf-8"
                try:
                    body_parts.append(part.get_payload(decode=True).decode(charset, errors="replace"))
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body_parts.append(msg.get_payload(decode=True).decode(charset, errors="replace"))
        except Exception:
            pass
    return "\n".join(body_parts)


def _clean_html(html: str) -> str:
    """简单去除 HTML 标签"""
    return re.sub(r"<[^>]+>", " ", html)


# ── 交易解析规则 ──────────────────────────────────────────────────────────────
# 每条规则是 (银行名, 发件关键词, 正则匹配, 字段映射)
# 正则命名组: date / merchant / amount / direction

PARSE_RULES = [
    # 招商银行: "您的招商银行信用卡尾号XXXX已于2026年05月28日 12:30在麦当劳消费人民币45.50元"
    {
        "bank": "招商银行",
        "sender_kw": "cmbchina",
        "patterns": [
            r"已于(?P<date>\d{4}年\d{2}月\d{2}日[\s\d:]*?)在(?P<merchant>.+?)消费人民币(?P<amount>[\d,]+\.?\d*)元",
            r"于(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}).*?在(?P<merchant>.+?)消费.*?(?P<amount>[\d,]+\.?\d*)元",
        ],
        "direction": "expense",
    },
    # 工商银行: "您于2026-05-28在网上支付消费人民币100.00元"
    {
        "bank": "工商银行",
        "sender_kw": "icbc",
        "patterns": [
            r"您于(?P<date>\d{4}[-年]\d{2}[-月]\d{2}[\s\d:时分]*)在(?P<merchant>.+?)消费人民币(?P<amount>[\d,]+\.?\d*)元",
            r"消费商户[:：](?P<merchant>.+?)\s+交易金额[:：](?P<amount>[\d,]+\.?\d*)元.*?交易时间[:：](?P<date>\d{4}[-年]\d{2}[-月]\d{2})",
        ],
        "direction": "expense",
    },
    # 建设银行
    {
        "bank": "建设银行",
        "sender_kw": "ccb",
        "patterns": [
            r"于(?P<date>\d{4}年\d{2}月\d{2}日\d{2}时\d{2}分).*?在(?P<merchant>.+?)消费人民币(?P<amount>[\d,]+\.?\d*)元",
            r"商户名称[:：](?P<merchant>.+?)\s+消费金额[:：](?P<amount>[\d,]+\.?\d*)元",
        ],
        "direction": "expense",
    },
    # 农业银行
    {
        "bank": "农业银行",
        "sender_kw": "abchina",
        "patterns": [
            r"于(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}).*?在(?P<merchant>.+?)(?:消费|扣款)(?:人民币|¥)(?P<amount>[\d,]+\.?\d*)元",
        ],
        "direction": "expense",
    },
    # 交通银行
    {
        "bank": "交通银行",
        "sender_kw": "bankcomm",
        "patterns": [
            r"(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?消费商户[:：](?P<merchant>.+?)\s+消费金额[:：](?P<amount>[\d,]+\.?\d*)元",
        ],
        "direction": "expense",
    },
    # 平安银行
    {
        "bank": "平安银行",
        "sender_kw": "pingan",
        "patterns": [
            r"消费商户[:：](?P<merchant>.+?)\s+交易金额[:：](?P<amount>[\d,]+\.?\d*)元.*?交易时间[:：](?P<date>\d{4}-\d{2}-\d{2})",
            r"于(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}).*?(?P<merchant>.+?)(?:消费|扣款)(?:人民币)?(?P<amount>[\d,]+\.?\d*)元",
        ],
        "direction": "expense",
    },
    # 通用兜底规则: 提取消费金额 + 日期
    {
        "bank": "银行",
        "sender_kw": None,
        "patterns": [
            r"(?P<date>\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?[\s\d:时分秒]*).*?(?:消费|扣款|转出).*?(?:人民币|¥|￥)?(?P<amount>[\d,]+\.\d{2})元",
        ],
        "direction": "expense",
    },
]


def _parse_date(raw: str) -> Optional[str]:
    """尝试将各种日期格式统一为 YYYY-MM-DD"""
    raw = raw.strip()
    patterns = [
        (r"(\d{4})年(\d{2})月(\d{2})日", "%Y-%m-%d"),
        (r"(\d{4})-(\d{2})-(\d{2})", None),
        (r"(\d{4})(\d{2})(\d{2})", "%Y-%m-%d"),
    ]
    # 尝试直接格式
    for pat, _ in patterns:
        m = re.search(pat, raw)
        if m:
            try:
                if "-" in raw:
                    return re.search(r"\d{4}-\d{2}-\d{2}", raw).group()
                else:
                    groups = m.groups()
                    return f"{groups[0]}-{groups[1]}-{groups[2]}"
            except Exception:
                continue
    return None


def _try_parse_row(body: str, subject: str, msg_date: str, rule: dict) -> Optional[ParsedRow]:
    """用一条规则尝试从邮件正文提取交易信息"""
    text = _clean_html(body) + "\n" + subject
    for pat in rule["patterns"]:
        m = re.search(pat, text, re.DOTALL)
        if not m:
            continue
        gd = m.groupdict()
        raw_date = gd.get("date", "") or msg_date
        date_str = _parse_date(raw_date) or msg_date[:10]
        if not date_str:
            continue
        merchant = gd.get("merchant", rule["bank"]).strip()[:64]
        # 清理 merchant 中的多余空格
        merchant = re.sub(r"\s+", " ", merchant).strip()
        raw_amount = gd.get("amount", "0").replace(",", "")
        try:
            amount = float(raw_amount)
            if amount <= 0:
                continue
        except ValueError:
            continue

        import hashlib as _hl
        sync_id = _hl.md5(f"{date_str}{amount}{merchant}".encode()).hexdigest()[:16]

        return ParsedRow(
            date=date_str,
            amount=amount,
            tx_type=rule["direction"],
            merchant=merchant,
            description=f"{rule['bank']}交易提醒",
            sync_source="email",
            sync_id=sync_id,
            raw_category="",
        )
    return None


def _parse_email_to_row(raw_email: bytes, fallback_date: str) -> Optional[ParsedRow]:
    """解析单封邮件 → ParsedRow"""
    msg = message_from_bytes(raw_email)
    subject = _decode_str(msg.get("Subject", ""))
    sender = _decode_str(msg.get("From", "")).lower()
    body = _get_text_body(msg)

    # 按规则优先级尝试匹配（有 sender_kw 的规则先试）
    for rule in PARSE_RULES:
        kw = rule.get("sender_kw")
        if kw and kw not in sender:
            continue
        row = _try_parse_row(body, subject, fallback_date, rule)
        if row:
            return row

    # 兜底：没有 sender_kw 限制的通用规则
    for rule in PARSE_RULES:
        if rule.get("sender_kw") is not None:
            continue
        row = _try_parse_row(body, subject, fallback_date, rule)
        if row:
            return row

    return None


# ── 对外接口 ──────────────────────────────────────────────────────────────────

def test_connection(email_addr: str, auth_code: str) -> dict:
    """测试 QQ 邮箱 IMAP 连接，返回 {ok, message}"""
    try:
        ctx = ssl.create_default_context()
        imap = imaplib.IMAP4_SSL(QQ_IMAP_HOST, QQ_IMAP_PORT, ssl_context=ctx)
        imap.login(email_addr, auth_code)
        imap.logout()
        return {"ok": True, "message": "连接成功，授权码验证通过"}
    except imaplib.IMAP4.error as e:
        msg = str(e)
        if "AUTHENTICATIONFAILED" in msg or "Authentication failed" in msg:
            return {"ok": False, "message": "授权码错误，请在 QQ 邮箱设置中重新生成授权码"}
        return {"ok": False, "message": f"登录失败：{msg}"}
    except Exception as e:
        return {"ok": False, "message": f"连接失败：{str(e)}"}


def fetch_bank_transactions(email_addr: str, auth_code: str, days: int = 90) -> list[ParsedRow]:
    """从 QQ 邮箱拉取近 N 天的银行交易提醒邮件，返回解析后的 ParsedRow 列表"""
    ctx = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(QQ_IMAP_HOST, QQ_IMAP_PORT, ssl_context=ctx)
    imap.login(email_addr, auth_code)
    imap.select("INBOX")

    since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    results: list[ParsedRow] = []

    # 按关键词搜索主题（逐个关键词，合并结果）
    found_ids: set[bytes] = set()
    for kw in SUBJECT_KEYWORDS:
        try:
            typ, data = imap.search(None, f'(SINCE "{since_date}" SUBJECT "{kw}")')
            if typ == "OK" and data[0]:
                for uid in data[0].split():
                    found_ids.add(uid)
        except Exception:
            continue

    # 按银行域名搜索发件人
    for domain in BANK_SENDER_KEYWORDS:
        try:
            typ, data = imap.search(None, f'(SINCE "{since_date}" FROM "{domain}")')
            if typ == "OK" and data[0]:
                for uid in data[0].split():
                    found_ids.add(uid)
        except Exception:
            continue

    for uid in found_ids:
        try:
            typ, data = imap.fetch(uid, "(RFC822)")
            if typ != "OK" or not data or not data[0]:
                continue
            raw = data[0][1]
            row = _parse_email_to_row(raw, datetime.now().strftime("%Y-%m-%d"))
            if row:
                results.append(row)
        except Exception:
            continue

    imap.logout()

    # 去重（按 sync_id）
    seen: set[str] = set()
    unique = []
    for r in results:
        if r.sync_id not in seen:
            seen.add(r.sync_id)
            unique.append(r)

    return unique
