"""bot/handlers/contact.py — Static contact card."""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from bot.states import MAIN_MENU
from bot import keyboards as kb
from services.i18n import t, get_lang


# Contact info — could be moved to config/env if needed
CONTACT_INFO = {
    "telegram": "@BossHiring",
    "whatsapp": "+855 12 345 678",
    "phone": "+855 12 345 678",
    "address": "Phnom Penh, Cambodia",
}


async def show_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Display contact information card."""
    q = update.callback_query
    asyncio.create_task(q.answer())
    lang = get_lang(ctx)

    title = t("contact.title", lang)
    body = t("contact.body", lang, **CONTACT_INFO)

    await q.edit_message_text(
        f"{title}\n\n{body}",
        reply_markup=kb.InlineKeyboardMarkup([
            [kb.back_button(lang)],
        ]),
    )
    return MAIN_MENU
