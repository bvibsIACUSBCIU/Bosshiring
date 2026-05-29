"""
services/sheets.py — Google Sheets append, sequential ID generation, retry logic.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client: gspread.Client | None = None

_HEADERS = {
    "candidates": [
        "记录ID", "提交时间", "用户语言", "状态", "姓名", "性别", "年龄", "国籍",
        "现居城市", "Telegram用户名", "Telegram用户ID", "电话/WhatsApp",
        "语言能力", "学历", "工作年限", "行业经验", "工作经历", "期望岗位", "期望薪资",
        "可接受工作地点", "可入职时间", "柬埔寨经验", "需要住宿", "需要签证/工作证",
        "简历链接", "附件链接", "备注", "AI摘要", "AI标签", "AI推荐岗位",
        "AI风险提示", "原始JSON", "内部备注", "负责HR", "最后更新",
    ],
    "companies": [
        "记录ID", "提交时间", "用户语言", "状态", "公司名称", "行业", "公司地址",
        "联系人姓名", "联系人职位", "Telegram用户名", "Telegram用户ID",
        "电话/WhatsApp", "招聘岗位", "招聘人数", "工作地点", "薪资范围",
        "工作时间", "语言要求", "经验要求", "提供住宿", "提供签证/工作证",
        "期望到岗时间", "岗位描述", "接受服务费条款", "企业资料链接", "备注",
        "AI摘要", "AI标签", "原始JSON", "内部备注", "负责HR", "最后更新",
    ],
    "boss_show": [
        "记录ID", "提交时间", "用户语言", "状态", "企业名称", "行业", "联系人",
        "联系方式", "Telegram用户名", "采访主题/合作意向", "企业简介", "合作类型",
        "内部备注", "最后更新",
    ],
}


def _get_client() -> gspread.Client:
    global _client
    if _client is None:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES
        )
        _client = gspread.authorize(creds)
    return _client


def _get_sheet(tab_name: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=40)
    _ensure_header(ws, tab_name)
    return ws


def _ensure_header(ws: gspread.Worksheet, tab_name: str) -> None:
    header = _HEADERS.get(tab_name)
    if not header:
        return
    first_row = ws.row_values(1)
    if any(cell.strip() for cell in first_row):
        return
    ws.update("A1", [header], value_input_option="USER_ENTERED")


def _next_seq(tab_name: str, prefix: str) -> str:
    """Generate next sequential record ID like C-20250528-0001."""
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%Y%m%d")
    try:
        ws = _get_sheet(tab_name)
        all_ids = ws.col_values(1)  # Column A = record_id
        today_prefix = f"{prefix}-{today}-"
        today_ids = [rid for rid in all_ids if rid.startswith(today_prefix)]
        seq = len(today_ids) + 1
        return f"{prefix}-{today}-{seq:04d}"
    except Exception as e:
        logger.error(f"Failed to generate sequential ID for {tab_name}: {e}")
        import random
        rand_suffix = random.randint(1000, 9999)
        now_time = datetime.now(timezone(timedelta(hours=7))).strftime("%H%M%S")
        return f"{prefix}-{today}-{now_time}-{rand_suffix}"


def _append_row_sync(tab_name: str, row: list[str], prefix: str) -> str:
    """Synchronous helper to append a row to Google Sheets with retry logic."""
    record_id = _next_seq(tab_name, prefix)
    row[0] = record_id  # Ensure record_id is set
    row[1] = datetime.now(timezone(timedelta(hours=7))).isoformat()  # submitted_at

    for attempt in range(2):
        try:
            ws = _get_sheet(tab_name)
            ws.append_row(row, value_input_option="USER_ENTERED")
            logger.info(f"Appended {record_id} to {tab_name}")
            return record_id
        except Exception as e:
            logger.error(f"Sheets append attempt {attempt+1} failed: {e}")
            if attempt == 0:
                time.sleep(3)
            else:
                _write_failed(tab_name, row, str(e))
                raise e
    return record_id


async def append_row(tab_name: str, row: list[str], prefix: str) -> str:
    """Append a row to the specified sheet tab. Returns the record_id.
    Retries once after 3s on failure. On second failure, writes to failed_submissions.jsonl and propagates the exception.
    """
    return await asyncio.to_thread(_append_row_sync, tab_name, row, prefix)


def _write_failed(tab_name: str, row: list[str], error: str) -> None:
    """Write failed submission to local JSONL fallback."""
    os.makedirs("data", exist_ok=True)
    entry = {
        "tab": tab_name,
        "row": row,
        "error": error,
        "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat(),
    }
    with open("data/failed_submissions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.warning(f"Wrote failed submission to data/failed_submissions.jsonl")
