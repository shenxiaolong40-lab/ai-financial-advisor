from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from backend.database import get_db
from backend.services.sync_service import parse_alipay, parse_wechat, import_rows

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/{source}")
async def import_bill(
    source: str,
    file: UploadFile = File(...),
    account_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    if source not in ("alipay", "wechat"):
        raise HTTPException(400, "source 只支持 alipay 或 wechat")

    data = await file.read()
    if not data:
        raise HTTPException(400, "文件为空")

    try:
        if source == "alipay":
            rows = parse_alipay(data)
        else:
            rows = parse_wechat(data)
    except ValueError as e:
        raise HTTPException(422, str(e))

    if not rows:
        return {"inserted": 0, "skipped": 0, "total": 0, "message": "文件中未找到有效交易记录"}

    result = import_rows(rows, account_id, db)
    result["message"] = f"导入完成：新增 {result['inserted']} 条，跳过重复 {result['skipped']} 条"
    return result


@router.get("/sample/{source}")
def download_sample(source: str):
    """返回示例 CSV 内容，帮助用户了解格式"""
    if source == "alipay":
        content = (
            "支付宝交易记录明细查询\n"
            "账号:example@email.com\n"
            "起始日期:[2026-01-01]    终止日期:[2026-05-31]\n"
            "共2笔记录\n"
            "-------------------\n"
            "交易时间,交易分类,交易对方,对方账号,商品名称,收/支,金额(元),支付方式,当前状态,交易单号,商家单号,备注\n"
            "2026-05-20 12:30:00,餐饮食品,麦当劳,,午饭,支出,45.50,余额宝,交易成功,2026052022001234567890,00000001,\n"
            "2026-05-01 09:00:00,其他,公司,,五月工资,收入,18000.00,余额宝,交易成功,2026050122001234567891,00000002,\n"
            "-------------------\n"
        )
        filename = "alipay_sample.csv"
    elif source == "wechat":
        content = (
            "微信支付账单明细,,,,,,,,,,\n"
            "微信昵称：示例用户,,,,,,,,,,\n"
            "起始时间：[2026-01-01 00:00:00],,,,,,,,,,\n"
            "终止时间：[2026-05-31 23:59:59],,,,,,,,,,\n"
            "导出类型：全部,,,,,,,,,,\n"
            "共2笔记录,,,,,,,,,,\n"
            "--------------------,,,,,,,,,,\n"
            "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n"
            "2026-05-22 19:00:00,商户消费,肯德基,晚餐,支出,¥68.00,零钱,支付成功,4200001234567890,00000001,/\n"
            "2026-05-10 14:00:00,转账,朋友A,还款,收入,¥200.00,零钱,已到账,4200001234567891,/,/\n"
            "--------------------,,,,,,,,,,\n"
        )
        filename = "wechat_sample.csv"
    else:
        raise HTTPException(400, "source 只支持 alipay 或 wechat")

    from fastapi.responses import Response
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
