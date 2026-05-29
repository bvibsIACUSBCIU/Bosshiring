"""
services/gemini.py — Resume parsing and summary generation via Gemini AI.
"""
import asyncio
import json
import logging
import mimetypes
import os

from google import genai
from google.genai import types

import config

logger = logging.getLogger(__name__)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)

_client = genai.Client(api_key=config.GEMINI_API_KEY)
_MODEL = "gemini-2.5-flash"

_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")

_LANG_MAP = {
    "zh": "Simplified Chinese",
    "en": "English",
    "km": "Khmer (ភ)",
}

_RESUME_DEFAULTS = {
    "name": "",
    "gender": "",
    "age": "",
    "nationality": "",
    "current_city": "",
    "phone_whatsapp": "",
    "languages": [],
    "education": "",
    "years_experience": "",
    "industry_experience": [],
    "work_experience": "",
    "desired_position": [],
    "desired_salary": "",
    "preferred_locations": [],
    "available_from": "",
    "cambodia_experience": False,
    "needs_accommodation": False,
    "needs_visa_support": False,
    "notes": "",
}


def _read_prompt(name: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, name), encoding="utf-8") as f:
        return f.read()


def normalize_mime_type(mime_type: str | None, filename: str = "") -> str:
    """Return a Gemini-friendly MIME type for resume uploads."""
    if mime_type and mime_type != "application/octet-stream":
        return mime_type
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/pdf"


def _empty_resume_result() -> dict:
    return dict(_RESUME_DEFAULTS)


def _extract_json_text(text: str) -> str:
    text = (text or "").strip()
    if "```json" in text:
        return text.split("```json", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1].strip()
    return text


def _coerce_list(value) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, (set, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1", "y", "是", "有", "需要"}
    return bool(value)


def _normalize_resume_result(data: dict | None) -> dict:
    result = _empty_resume_result()
    if not isinstance(data, dict):
        return result

    for key, default in _RESUME_DEFAULTS.items():
        value = data.get(key, default)
        if isinstance(default, list):
            result[key] = _coerce_list(value)
        elif isinstance(default, bool):
            result[key] = _coerce_bool(value)
        elif value is None:
            result[key] = ""
        else:
            result[key] = str(value).strip()
    return result


async def parse_resume(file_bytes: bytes, mime_type: str, lang: str, filename: str = "") -> dict:
    """Parse a resume file using Gemini. Always returns the resume schema."""
    try:
        prompt = _read_prompt("candidate_parse.txt")
        normalized_mime = normalize_mime_type(mime_type, filename)
        response = await asyncio.to_thread(
            _client.models.generate_content,
            model=_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=file_bytes, mime_type=normalized_mime),
            ],
        )
        data = json.loads(_extract_json_text(response.text))
        return _normalize_resume_result(data)
    except Exception as e:
        logger.error(f"Gemini parse_resume failed: {e}")
        return _empty_resume_result()


async def generate_candidate_summary(data: dict, lang: str) -> dict:
    """Generate AI summary and tags for a candidate.
    Returns {ai_summary, ai_tags, ai_recommended_roles, ai_risk_notes}.
    """
    try:
        prompt_template = _read_prompt("candidate_summary.txt")
        lang_instruction = _LANG_MAP.get(lang, "English")
        prompt = prompt_template.format(
            data=json.dumps(data, cls=SetEncoder, ensure_ascii=False, indent=2),
            lang_instruction=lang_instruction,
        )
        response = await asyncio.to_thread(
            _client.models.generate_content,
            model=_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini candidate summary failed: {e}")
        return {"ai_summary": "AI解析失败", "ai_tags": "", "ai_recommended_roles": "", "ai_risk_notes": ""}


async def generate_company_summary(data: dict, lang: str) -> dict:
    """Generate AI summary and tags for a company posting.
    Returns {ai_summary, ai_tags}.
    """
    try:
        prompt_template = _read_prompt("company_summary.txt")
        lang_instruction = _LANG_MAP.get(lang, "English")
        prompt = prompt_template.format(
            data=json.dumps(data, cls=SetEncoder, ensure_ascii=False, indent=2),
            lang_instruction=lang_instruction,
        )
        response = await asyncio.to_thread(
            _client.models.generate_content,
            model=_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini company summary failed: {e}")
        return {"ai_summary": "AI解析失败", "ai_tags": ""}
