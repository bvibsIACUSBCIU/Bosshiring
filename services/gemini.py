"""
services/gemini.py — Resume parsing and summary generation via Gemini AI.
"""
import json
import logging
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
    "km": "Khmer (ភorg org org org org org org org org)",
}


def _read_prompt(name: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, name), encoding="utf-8") as f:
        return f.read()


async def parse_resume(file_bytes: bytes, mime_type: str, lang: str) -> dict:
    """Parse a resume file using Gemini. Returns parsed dict or {} on failure."""
    try:
        prompt = _read_prompt("candidate_parse.txt")
        response = _client.models.generate_content(
            model=_MODEL,
            contents=[
                prompt,
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
        )
        text = response.text.strip()
        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini parse_resume failed: {e}")
        return {}


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
        response = _client.models.generate_content(model=_MODEL, contents=prompt)
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
        response = _client.models.generate_content(model=_MODEL, contents=prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini company summary failed: {e}")
        return {"ai_summary": "AI解析失败", "ai_tags": ""}
