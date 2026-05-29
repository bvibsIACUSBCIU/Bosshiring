"""bot/handlers/company.py — Company hiring conversation flow."""
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import *
from bot import keyboards as kb
from bot.ui import progress, company_review_card
from services.i18n import t, get_lang
from services import drive, sheets, gemini, notifier
from models.company import CompanyRecord

logger = logging.getLogger(__name__)
TS = COMPANY_TOTAL_STEPS

def _d(ctx): return ctx.user_data.setdefault("company", {})
def _ms(ctx, f): return ctx.user_data.setdefault(f"_ms_{f}", set())
def _push(ctx, s): ctx.user_data.setdefault("state_history", []).append(s)
def _pop(ctx): h=ctx.user_data.get("state_history",[]); return h.pop() if h else MAIN_MENU

async def _step(q, lang, n, key, markup):
    await q.edit_message_text(f"{progress(lang,n,TS)}\n\n{t(key, lang)}", reply_markup=markup)

async def entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    ctx.user_data["company"] = {}
    await q.edit_message_text(t("company.welcome", lang))
    await q.message.reply_text(f"{progress(lang,1,TS)}\n\n{t('company.step_company_name', lang)}")
    return B_COMPANY_NAME

async def company_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["company_name"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_COMPANY_NAME)
    await update.message.reply_text(f"{progress(lang,2,TS)}\n\n{t('company.step_industry', lang)}",
        reply_markup=kb.industry_kb(lang, set()))
    return B_INDUSTRY

async def industry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        sel = _ms(ctx, "b_industry")
        if q.data == "back": return _pop(ctx)
        if q.data == "ms_done":
            d["industry"] = ", ".join(sel) if sel else ""
            if ctx.user_data.get("edit_return"):
                ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
            _push(ctx, B_INDUSTRY)
            await q.edit_message_text(f"{progress(lang,3,TS)}\n\n{t('company.step_address', lang)}")
            return B_ADDRESS
        if q.data.startswith("ms_"):
            val = q.data[3:]
            if val == "__other__":
                await q.edit_message_text(f"{progress(lang,2,TS)}\n\n{t('company.step_industry', lang)}\n{t('common.or_type', lang)}")
                return B_INDUSTRY
            sel.symmetric_difference_update({val})
            await q.edit_message_text(f"{progress(lang,2,TS)}\n\n{t('company.step_industry', lang)}",
                reply_markup=kb.industry_kb(lang, sel))
        return B_INDUSTRY
    d["industry"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_INDUSTRY)
    await update.message.reply_text(f"{progress(lang,3,TS)}\n\n{t('company.step_address', lang)}")
    return B_ADDRESS

async def address(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["address"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_ADDRESS)
    await update.message.reply_text(f"{progress(lang,4,TS)}\n\n{t('company.step_contact_name', lang)}")
    return B_CONTACT_NAME

async def contact_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["contact_name"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_CONTACT_NAME)
    await update.message.reply_text(f"{progress(lang,5,TS)}\n\n{t('company.step_contact_title', lang)}")
    return B_CONTACT_TITLE

async def contact_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["contact_title"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_CONTACT_TITLE)
    await update.message.reply_text(f"{progress(lang,6,TS)}\n\n{t('company.step_phone', lang)}")
    return B_PHONE

async def phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["phone"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_PHONE)
    await update.message.reply_text(f"{progress(lang,7,TS)}\n\n{t('company.step_position', lang)}")
    return B_POSITION

async def position(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx); d["position"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_POSITION)
    await update.message.reply_text(f"{progress(lang,8,TS)}\n\n{t('company.step_headcount', lang)}",
        reply_markup=kb.headcount_kb(lang))
    return B_HEADCOUNT

async def headcount(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "hc_other":
            await q.edit_message_text(f"{progress(lang,8,TS)}\n\n{t('company.step_headcount', lang)}\n{t('common.or_type', lang)}")
            return B_HEADCOUNT
        d["headcount"] = q.data.replace("hc_","")
    else:
        d["headcount"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_HEADCOUNT)
    if update.callback_query:
        await _step(update.callback_query, lang, 9, "company.step_location", kb.location_kb(lang, set()))
    else:
        await update.message.reply_text(f"{progress(lang,9,TS)}\n\n{t('company.step_location', lang)}",
            reply_markup=kb.location_kb(lang, set()))
    return B_LOCATION

async def location(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "b_location")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["location"] = ", ".join(sel)
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, B_LOCATION)
        await update.message.reply_text(f"{progress(lang,10,TS)}\n\n{t('company.step_salary', lang)}",
            reply_markup=kb.salary_company_kb(lang))
        return B_SALARY
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["location"] = ", ".join(sel) if sel else ""
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, B_LOCATION)
        await _step(q, lang, 10, "company.step_salary", kb.salary_company_kb(lang))
        return B_SALARY
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,9,TS)}\n\n{t('company.step_location', lang)}\n{t('common.or_type', lang)}")
            return B_LOCATION
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,9,TS)}\n\n{t('company.step_location', lang)}",
            reply_markup=kb.location_kb(lang, sel))
    return B_LOCATION

async def salary(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        d["salary"] = q.data.replace("sal_","")
        if d["salary"] == "negotiate": d["salary"] = t("common.negotiate", lang)
    else:
        d["salary"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_SALARY)
    if update.callback_query:
        await _step(update.callback_query, lang, 11, "company.step_hours", kb.working_hours_kb(lang))
    else:
        await update.message.reply_text(f"{progress(lang,11,TS)}\n\n{t('company.step_hours', lang)}",
            reply_markup=kb.working_hours_kb(lang))
    return B_HOURS

async def hours(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return _pop(ctx)
    d["hours"] = q.data.replace("hours_","")
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
    _push(ctx, B_HOURS)
    await _step(q, lang, 12, "company.step_language", kb.language_kb(lang, set()))
    return B_LANGUAGE

async def language_req(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "b_lang_req")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["language_req"] = ", ".join(sel)
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, B_LANGUAGE)
        await update.message.reply_text(f"{progress(lang,13,TS)}\n\n{t('company.step_experience', lang)}",
            reply_markup=kb.experience_req_kb(lang))
        return B_EXPERIENCE
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["language_req"] = ", ".join(sel)
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, B_LANGUAGE)
        await _step(q, lang, 13, "company.step_experience", kb.experience_req_kb(lang))
        return B_EXPERIENCE
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,12,TS)}\n\n{t('company.step_language', lang)}\n{t('common.or_type', lang)}")
            return B_LANGUAGE
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,12,TS)}\n\n{t('company.step_language', lang)}",
            reply_markup=kb.language_kb(lang, sel))
    return B_LANGUAGE

async def experience(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return _pop(ctx)
    d["experience_req"] = q.data.replace("expreq_","")
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
    _push(ctx, B_EXPERIENCE)
    ctx.user_data["_ms_b_benefits"] = set()
    await _step(q, lang, 14, "company.step_benefits", kb.company_benefits_kb(lang, set()))
    return B_BENEFITS

async def benefits(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "b_benefits")
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["benefits_accommodation"] = "accommodation" in sel
        d["benefits_visa"] = "visa" in sel
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, B_BENEFITS)
        await _step(q, lang, 15, "company.step_start_date", kb.available_kb(lang))
        return B_START_DATE
    if q.data.startswith("ms_"):
        val = q.data[3:]
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,14,TS)}\n\n{t('company.step_benefits', lang)}",
            reply_markup=kb.company_benefits_kb(lang, sel))
    return B_BENEFITS

async def start_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "avail_other":
            await q.edit_message_text(f"{progress(lang,15,TS)}\n\n{t('company.step_start_date', lang)}\n{t('common.or_type', lang)}")
            return B_START_DATE
        d["start_date"] = q.data.replace("avail_","")
    else:
        d["start_date"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_START_DATE)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            f"{progress(lang,16,TS)}\n\n{t('company.step_jd', lang)}", reply_markup=kb.skip_back_kb(lang))
    else:
        await update.message.reply_text(
            f"{progress(lang,16,TS)}\n\n{t('company.step_jd', lang)}", reply_markup=kb.skip_back_kb(lang))
    return B_JD

async def jd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "skip": d["jd"] = ""
        elif q.data == "back": return _pop(ctx)
    else:
        d["jd"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, B_JD)
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text(f"{progress(lang,17,TS)}\n\n{t('company.step_service_fee', lang)}",
        reply_markup=kb.service_fee_kb(lang))
    return B_SERVICE_FEE

async def service_fee(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "fee_accept":
        d["service_fee"] = t("common.yes", lang)
        return await _show_review_q(q, ctx)
    elif q.data == "fee_decline":
        await q.edit_message_text(t("company.service_fee_declined", lang))
        ctx.user_data.clear()
        return ConversationHandler.END
    return B_SERVICE_FEE

async def _show_review(update, ctx) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = company_review_card(d, lang)
    msg = update.message or update.callback_query.message
    await msg.reply_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return B_REVIEW

async def _show_review_q(q, ctx) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = company_review_card(d, lang)
    await q.edit_message_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return B_REVIEW

async def review(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    if q.data == "confirm_submit":
        await q.edit_message_text(t("common.submitting", lang))
        return await _submit(update, ctx)
    if q.data == "confirm_cancel":
        ctx.user_data.clear()
        await q.edit_message_text(t("common.cancel_confirm", lang))
        return ConversationHandler.END
    if q.data == "noop": return B_REVIEW
    if q.data.startswith("edit_"):
        ctx.user_data["edit_return"] = True
        field = q.data.replace("edit_","")
        txt_steps = {
            "company_name": ("company.step_company_name", None),
            "address": ("company.step_address", None),
            "contact_name": ("company.step_contact_name", None),
            "contact_title": ("company.step_contact_title", None),
            "phone": ("company.step_phone", None),
            "position": ("company.step_position", None),
            "headcount": ("company.step_headcount", kb.headcount_kb(lang)),
            "salary": ("company.step_salary", kb.salary_company_kb(lang)),
            "hours": ("company.step_hours", kb.working_hours_kb(lang)),
            "jd": ("company.step_jd", kb.skip_back_kb(lang)),
            "notes": ("company.step_notes", kb.skip_back_kb(lang)),
        }
        state_map = {
            "company_name": B_COMPANY_NAME, "industry": B_INDUSTRY, "address": B_ADDRESS,
            "contact_name": B_CONTACT_NAME, "contact_title": B_CONTACT_TITLE,
            "phone": B_PHONE, "position": B_POSITION, "headcount": B_HEADCOUNT,
            "location": B_LOCATION, "salary": B_SALARY, "hours": B_HOURS,
            "language_req": B_LANGUAGE, "experience_req": B_EXPERIENCE,
            "benefits_accommodation": B_BENEFITS, "benefits_visa": B_BENEFITS,
            "start_date": B_START_DATE, "jd": B_JD, "notes": B_NOTES,
        }
        info = txt_steps.get(field)
        st = state_map.get(field, B_REVIEW)
        if info:
            key, markup = info
            await q.edit_message_text(t(key, lang), reply_markup=markup)
        return st
    return B_REVIEW

async def _submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; lang = get_lang(ctx); d = _d(ctx)
    user = update.effective_user
    try:
        rec = CompanyRecord(
            lang=lang, company_name=d.get("company_name",""),
            industry=d.get("industry",""), company_address=d.get("address",""),
            contact_name=d.get("contact_name",""), contact_title=d.get("contact_title",""),
            telegram_username=f"@{user.username}" if user.username else "",
            telegram_user_id=user.id, phone_whatsapp=d.get("phone",""),
            position_title=d.get("position",""), headcount=d.get("headcount",""),
            work_location=d.get("location",""), salary_range=d.get("salary",""),
            working_hours=d.get("hours",""), language_requirement=d.get("language_req",""),
            experience_requirement=d.get("experience_req",""),
            provides_accommodation="Yes" if d.get("benefits_accommodation") else "No",
            provides_visa="Yes" if d.get("benefits_visa") else "No",
            start_date_requirement=d.get("start_date",""),
            job_description=d.get("jd",""),
            accepts_service_fee_terms="Yes" if d.get("service_fee") else "No",
            notes=d.get("notes",""),
        )
        ai = await gemini.generate_company_summary(d, lang)
        rec.ai_summary = ai.get("ai_summary","")
        rec.ai_tags = ai.get("ai_tags","")
        row = rec.to_row()
        record_id = await sheets.append_row("companies", row, "J")
        rec.record_id = record_id
        await q.edit_message_text(t("company.submit_success", lang))
        nd = {"record_id":record_id,"company_name":rec.company_name,"industry":rec.industry,
            "contact_name":rec.contact_name,"contact_title":rec.contact_title,
            "position":rec.position_title,"headcount":rec.headcount,
            "location":rec.work_location,"salary":rec.salary_range,
            "language_req":rec.language_requirement,"start_date":rec.start_date_requirement,
            "ai_tags":rec.ai_tags,"ai_summary":rec.ai_summary}
        try:
            await notifier.notify_new_company(ctx.bot, nd, lang)
        except Exception as ne:
            logger.error(f"Failed to notify internal group: {ne}")
        ctx.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Company submit failed: {e}")
        txt, flds = company_review_card(d, lang)
        error_msg = f"❌ {t('common.submit_fail', lang)}\n\n"
        try:
            await q.edit_message_text(error_msg + txt, reply_markup=kb.review_edit_kb(flds, lang))
        except Exception:
            await q.message.reply_text(error_msg + txt, reply_markup=kb.review_edit_kb(flds, lang))
        return B_REVIEW
