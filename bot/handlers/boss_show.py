"""bot/handlers/boss_show.py — Boss Show cooperation flow."""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import *
from bot import keyboards as kb
from bot.ui import progress, boss_show_review_card
from services.i18n import t, get_lang
from services import sheets, notifier

logger = logging.getLogger(__name__)
TS = BOSS_SHOW_TOTAL_STEPS

def _d(ctx): return ctx.user_data.setdefault("boss_show", {})
def _push(ctx, s): ctx.user_data.setdefault("state_history", []).append(s)

async def entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    ctx.user_data["boss_show"] = {}
    await q.edit_message_text(
        f"{t('boss_show.intro_title', lang)}\n\n{t('boss_show.intro_body', lang)}",
        reply_markup=kb.boss_show_intro_kb(lang))
    return BS_COMPANY

async def apply_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    if q.data == "back":
        from bot.handlers.start import show_main_menu
        return await show_main_menu(update, ctx)
    await q.edit_message_text(f"{progress(lang,1,TS)}\n\n{t('boss_show.step_company', lang)}")
    return BS_COMPANY

async def bs_company(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); _d(ctx)["company"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_COMPANY)
    await update.message.reply_text(f"{progress(lang,2,TS)}\n\n{t('boss_show.step_industry', lang)}")
    return BS_INDUSTRY

async def bs_industry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); _d(ctx)["industry"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_INDUSTRY)
    await update.message.reply_text(f"{progress(lang,3,TS)}\n\n{t('boss_show.step_contact', lang)}")
    return BS_CONTACT

async def bs_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); _d(ctx)["contact"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_CONTACT)
    await update.message.reply_text(f"{progress(lang,4,TS)}\n\n{t('boss_show.step_contact_info', lang)}")
    return BS_CONTACT_INFO

async def bs_contact_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); _d(ctx)["contact_info"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_CONTACT_INFO)
    await update.message.reply_text(f"{progress(lang,5,TS)}\n\n{t('boss_show.step_topic', lang)}")
    return BS_TOPIC

async def bs_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); _d(ctx)["topic"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_TOPIC)
    await update.message.reply_text(
        f"{progress(lang,6,TS)}\n\n{t('boss_show.step_intro', lang)}",
        reply_markup=kb.skip_back_kb(lang))
    return BS_INTRO

async def bs_intro(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "skip": d["intro"] = ""
        elif q.data == "back": return BS_TOPIC
    else:
        d["intro"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, BS_INTRO)
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text(
        f"{progress(lang,7,TS)}\n\n{t('boss_show.step_intent', lang)}",
        reply_markup=kb.boss_show_intent_kb(lang))
    return BS_INTENT

async def bs_intent(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return BS_INTRO
    intent_map = {
        "bsi_interview": t("boss_show.intent_interview", lang),
        "bsi_brand": t("boss_show.intent_brand", lang),
        "bsi_hire": t("boss_show.intent_hire", lang),
    }
    d["intent"] = intent_map.get(q.data, "")
    return await _show_review_q(q, ctx)

async def _show_review(update, ctx) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = boss_show_review_card(d, lang)
    msg = update.message or update.callback_query.message
    await msg.reply_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return BS_REVIEW

async def _show_review_q(q, ctx) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = boss_show_review_card(d, lang)
    await q.edit_message_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return BS_REVIEW

async def review(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    if q.data == "confirm_submit":
        await q.edit_message_text(t("common.submitting", lang))
        return await _submit(update, ctx)
    if q.data == "confirm_cancel":
        ctx.user_data.clear()
        await q.edit_message_text(t("common.cancel_confirm", lang))
        return ConversationHandler.END
    if q.data == "noop": return BS_REVIEW
    if q.data.startswith("edit_"):
        ctx.user_data["edit_return"] = True
        field = q.data.replace("edit_","")
        state_map = {"company":BS_COMPANY,"industry":BS_INDUSTRY,"contact":BS_CONTACT,
            "contact_info":BS_CONTACT_INFO,"topic":BS_TOPIC,"intro":BS_INTRO,"intent":BS_INTENT}
        st = state_map.get(field, BS_REVIEW)
        key_map = {"company":"boss_show.step_company","industry":"boss_show.step_industry",
            "contact":"boss_show.step_contact","contact_info":"boss_show.step_contact_info",
            "topic":"boss_show.step_topic","intro":"boss_show.step_intro","intent":"boss_show.step_intent"}
        k = key_map.get(field)
        if k:
            markup = kb.boss_show_intent_kb(lang) if field=="intent" else None
            await q.edit_message_text(t(k, lang), reply_markup=markup)
        return st
    return BS_REVIEW

async def _submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; lang = get_lang(ctx); d = _d(ctx)
    user = update.effective_user
    try:
        row = ["", "", lang, "新申请",
               d.get("company",""), d.get("industry",""), d.get("contact",""),
               d.get("contact_info",""),
               f"@{user.username}" if user.username else "",
               d.get("topic",""), d.get("intro",""), d.get("intent",""),
               "", ""]
        record_id = await sheets.append_row("boss_show", row, "B")
        await q.edit_message_text(t("boss_show.submit_success", lang))
        nd = {"record_id":record_id,"company":d.get("company",""),"industry":d.get("industry",""),
            "contact":d.get("contact",""),"contact_info":d.get("contact_info",""),
            "intent":d.get("intent",""),"topic":d.get("topic","")}
        try:
            await notifier.notify_new_boss_show(ctx.bot, nd, lang)
        except Exception as ne:
            logger.error(f"Failed to notify internal group: {ne}")
        ctx.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Boss show submit failed: {e}")
        txt, flds = boss_show_review_card(d, lang)
        error_msg = f"❌ {t('common.submit_fail', lang)}\n\n"
        try:
            await q.edit_message_text(error_msg + txt, reply_markup=kb.review_edit_kb(flds, lang))
        except Exception:
            await q.message.reply_text(error_msg + txt, reply_markup=kb.review_edit_kb(flds, lang))
        return BS_REVIEW

