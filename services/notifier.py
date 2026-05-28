"""
services/notifier.py — Internal Telegram group notifications.
Always sends in Chinese (zh) regardless of user language.
"""
import logging
from telegram import Bot
from services.i18n import t
import config

logger = logging.getLogger(__name__)

INTERNAL_LANG = "zh"


async def notify_new_candidate(bot: Bot, data: dict, user_lang: str) -> None:
    """Send new candidate alert to internal group."""
    try:
        msg = t("notify.new_candidate", INTERNAL_LANG,
                record_id=data.get("record_id", ""),
                name=data.get("name", ""),
                nationality=data.get("nationality", ""),
                age=data.get("age", ""),
                city=data.get("city", ""),
                languages=data.get("languages", ""),
                position=data.get("position", ""),
                salary=data.get("salary", ""),
                resume_link=data.get("resume_link", "无"),
                tags=data.get("ai_tags", ""),
                summary=data.get("ai_summary", ""),
                user_lang=_lang_display(user_lang))
        await bot.send_message(
            chat_id=config.TELEGRAM_INTERNAL_GROUP_ID,
            text=msg,
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"Failed to notify new candidate: {e}")


async def notify_new_company(bot: Bot, data: dict, user_lang: str) -> None:
    """Send new company hiring alert to internal group."""
    try:
        msg = t("notify.new_company", INTERNAL_LANG,
                record_id=data.get("record_id", ""),
                company=data.get("company_name", ""),
                industry=data.get("industry", ""),
                contact=data.get("contact_name", ""),
                title=data.get("contact_title", ""),
                position=data.get("position", ""),
                headcount=data.get("headcount", ""),
                location=data.get("location", ""),
                salary=data.get("salary", ""),
                language_req=data.get("language_req", ""),
                start_date=data.get("start_date", ""),
                tags=data.get("ai_tags", ""),
                summary=data.get("ai_summary", ""),
                user_lang=_lang_display(user_lang))
        await bot.send_message(
            chat_id=config.TELEGRAM_INTERNAL_GROUP_ID,
            text=msg,
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"Failed to notify new company: {e}")


async def notify_new_boss_show(bot: Bot, data: dict, user_lang: str) -> None:
    """Send Boss Show collaboration alert to internal group."""
    try:
        msg = t("notify.new_boss_show", INTERNAL_LANG,
                record_id=data.get("record_id", ""),
                company=data.get("company", ""),
                industry=data.get("industry", ""),
                contact=data.get("contact", ""),
                contact_info=data.get("contact_info", ""),
                intent=data.get("intent", ""),
                topic=data.get("topic", ""),
                user_lang=_lang_display(user_lang))
        await bot.send_message(
            chat_id=config.TELEGRAM_INTERNAL_GROUP_ID,
            text=msg,
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"Failed to notify boss show: {e}")


def _lang_display(lang: str) -> str:
    return {"zh": "中文", "en": "English", "km": "ភាស"}.get(lang, lang)
