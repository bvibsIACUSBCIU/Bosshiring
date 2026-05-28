"""
bot/handlers/start.py — /start, language selection, main menu, /cancel, /lang.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.states import LANG_SELECT, MAIN_MENU
from bot.keyboards import lang_select_kb, main_menu_kb
from services.i18n import t, get_lang

logger = logging.getLogger(__name__)

# Bootstrap prompt — trilingual, hardcoded per spec
BOOTSTRAP_PROMPT = "请选择语言 / Please select language / សូមជ្រើសរើសភាសា"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — show language selection."""
    context.user_data.clear()
    await update.message.reply_text(
        BOOTSTRAP_PROMPT,
        reply_markup=lang_select_kb(),
    )
    return LANG_SELECT


async def lang_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection callback."""
    query = update.callback_query
    asyncio.create_task(query.answer())

    lang_code = query.data.replace("lang_", "")  # lang_zh -> zh
    context.user_data["lang"] = lang_code
    context.user_data["state_history"] = []

    await query.edit_message_text(
        text=t("menu.title", lang_code),
        reply_markup=main_menu_kb(lang_code),
    )
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel command at any state."""
    lang = get_lang(context)
    context.user_data.clear()
    await update.message.reply_text(t("common.cancel_confirm", lang))
    return ConversationHandler.END


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /lang command — restart from language select."""
    context.user_data.clear()
    await update.message.reply_text(
        BOOTSTRAP_PROMPT,
        reply_markup=lang_select_kb(),
    )
    return LANG_SELECT


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    lang = get_lang(context)
    if update.effective_message:
        await update.effective_message.reply_text(t("common.timeout_msg", lang))
    context.user_data.clear()
    return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the main menu (used for 'back' navigation)."""
    lang = get_lang(context)
    query = update.callback_query
    if query:
        asyncio.create_task(query.answer())
        await query.edit_message_text(
            text=t("menu.title", lang),
            reply_markup=main_menu_kb(lang),
        )
    return MAIN_MENU
