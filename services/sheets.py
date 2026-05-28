"""
services/sheets.py — Google Sheets append, sequential ID generation, retry logic.
"""
import asyncio
import json
import logging
import os
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
        return spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=40)


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


async def append_row(tab_name: str, row: list[str], prefix: str) -> str:
    """Append a row to the specified sheet tab. Returns the record_id.
    Retries once after 3s on failure. On second failure, writes to failed_submissions.jsonl and propagates the exception.
    """
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
                await asyncio.sleep(3)
            else:
                _write_failed(tab_name, row, str(e))
                raise e


    return record_id


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
