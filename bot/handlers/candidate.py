"""bot/handlers/candidate.py — Full candidate (job seeker) conversation flow."""
import asyncio, json, logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import *
from bot import keyboards as kb
from bot.ui import progress, candidate_review_card
from services.i18n import t, get_lang
from services import drive, sheets, gemini, notifier
from models.candidate import CandidateRecord

logger = logging.getLogger(__name__)
TS = CANDIDATE_TOTAL_STEPS
FILE_TIMEOUTS = {
    "read_timeout": 60,
    "write_timeout": 60,
    "connect_timeout": 60,
    "pool_timeout": 60,
}
WORK_EXPERIENCE_LIMIT = 3

def _d(ctx): return ctx.user_data.setdefault("candidate", {})
def _ms(ctx, f): return ctx.user_data.setdefault(f"_ms_{f}", set())
def _push(ctx, s): ctx.user_data.setdefault("state_history", []).append(s)
def _pop(ctx): h=ctx.user_data.get("state_history",[]); return h.pop() if h else MAIN_MENU

async def _step(q, lang, step, total, key, markup):
    txt = f"{progress(lang, step, total)}\n\n{t(key, lang)}"
    await q.edit_message_text(text=txt, reply_markup=markup)

async def entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer())
    lang = get_lang(ctx); ctx.user_data["candidate"] = {}
    await q.edit_message_text(t("candidate.welcome", lang))
    await q.message.reply_text(
        f"{progress(lang,1,TS)}\n\n{t('candidate.resume_choice', lang)}",
        reply_markup=kb.resume_choice_kb(lang))
    return C_RESUME_CHOICE

async def resume_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    if q.data == "resume_upload":
        await q.edit_message_text(f"{progress(lang,1,TS)}\n\n{t('candidate.step_resume', lang)}",
            reply_markup=kb.skip_back_kb(lang))
        return C_RESUME_UPLOAD
    elif q.data == "resume_manual":
        _push(ctx, C_RESUME_CHOICE)
        await q.edit_message_text(f"{progress(lang,1,TS)}\n\n{t('candidate.step_name', lang)}")
        return C_NAME
    elif q.data == "resume_skip":
        _push(ctx, C_RESUME_CHOICE)
        await q.edit_message_text(f"{progress(lang,1,TS)}\n\n{t('candidate.step_name', lang)}")
        return C_NAME
    elif q.data == "back":
        from bot.handlers.start import show_main_menu
        return await show_main_menu(update, ctx)
    return C_RESUME_CHOICE

async def resume_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "skip":
            await q.edit_message_text(f"{progress(lang,1,TS)}\n\n{t('candidate.step_name', lang)}")
            return C_NAME
        if q.data == "back": return C_RESUME_CHOICE
    try:
        upload = await _download_candidate_file(update, "resume")
    except Exception as de:
        logger.error(f"Resume download failed: {de}")
        await update.message.reply_text(t("candidate.parse_fail", lang))
        await update.message.reply_text(f"{progress(lang,1,TS)}\n\n{t('candidate.step_name', lang)}")
        return C_NAME
    if not upload:
        await update.message.reply_text(t("candidate.step_resume", lang), reply_markup=kb.skip_back_kb(lang))
        return C_RESUME_UPLOAD
    await update.message.reply_text(t("candidate.parsing", lang))

    # Always upload to Google Drive first, even if parsing fails later
    link = ""
    try:
        link = await drive.upload_file(upload["bytes"], upload["filename"], upload["mime"])
        if link:
            d["resume_link"] = link
    except Exception as ue:
        logger.error(f"Drive upload failed: {ue}")

    parsed = await gemini.parse_resume(upload["bytes"], upload["mime"], lang, upload["filename"])
    _apply_resume_parse(d, parsed)
    txt, flds = candidate_review_card(d, lang)
    await update.message.reply_text(
        f"{t('candidate.parse_done', lang)}\n\n{txt}",
        reply_markup=kb.review_edit_kb(flds, lang))
    return C_REVIEW


async def _download_candidate_file(update: Update, kind: str) -> dict | None:
    doc = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not doc:
        return None

    import os

    ext = "pdf"
    if getattr(doc, "file_name", None):
        _, file_ext = os.path.splitext(doc.file_name)
        if file_ext:
            ext = file_ext.lstrip(".")
    elif update.message.photo:
        ext = "jpg"
    ext = ext.lower()
    raw_mime = getattr(doc, "mime_type", None) or ("image/jpeg" if update.message.photo else None)
    filename = _candidate_drive_filename(update.effective_user, kind, ext)
    mime = gemini.normalize_mime_type(raw_mime, filename)

    f = await doc.get_file(**FILE_TIMEOUTS)
    fb = await f.download_as_bytearray(**FILE_TIMEOUTS)
    return {"bytes": bytes(fb), "filename": filename, "mime": mime}


def _candidate_drive_filename(user, kind: str, ext: str) -> str:
    import re

    def clean_name(s: str) -> str:
        if not s:
            return ""
        s = re.sub(r"\s+", "_", s.strip())
        return "".join(c for c in s if c.isalnum() or c in ("_", "-"))

    first_name_clean = clean_name(user.first_name or "")
    last_name_clean = clean_name(user.last_name or "")
    name_part = "_".join(part for part in [first_name_clean, last_name_clean] if part)
    username_part = clean_name(user.username or "")

    parts = [str(user.id)]
    if name_part:
        parts.append(name_part)
    if username_part:
        parts.append(username_part)
    parts.append(kind)
    return "_".join(parts) + f".{ext}"


def _apply_resume_parse(data: dict, parsed: dict) -> None:
    key_map = {
        "current_city": "city",
        "phone_whatsapp": "phone",
        "years_experience": "years_exp",
        "industry_experience": "industry",
        "desired_position": "position",
        "desired_salary": "salary",
        "preferred_locations": "locations",
        "available_from": "available",
        "work_experience": "work_experience",
        "cambodia_experience": "cambodia_exp",
        "needs_accommodation": "accommodation",
        "needs_visa_support": "visa",
    }
    for k, v in parsed.items():
        target_key = key_map.get(k, k)
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, list):
            data[target_key] = ", ".join(str(item) for item in v if item)
        elif isinstance(v, bool):
            data[target_key] = v
        else:
            data[target_key] = str(v).strip()
    data["raw_json"] = json.dumps(parsed, ensure_ascii=False)


async def name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return C_RESUME_CHOICE
        return C_NAME
    d["name"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_NAME)
    await update.message.reply_text(f"{progress(lang,2,TS)}\n\n{t('candidate.step_gender', lang)}",
        reply_markup=kb.gender_kb(lang))
    return C_GENDER

async def gender(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return _pop(ctx)
    if q.data.startswith("gender_"):
        val = q.data.replace("gender_", "")
        d["gender"] = t(f"candidate.gender_{val}", lang)
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
    _push(ctx, C_GENDER)
    await _step(q, lang, 3, TS, "candidate.step_age", kb.age_kb(lang))
    return C_AGE

async def age(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "age_other":
            await q.edit_message_text(f"{progress(lang,3,TS)}\n\n{t('candidate.step_age', lang)}\n{t('common.or_type', lang)}")
            return C_AGE
        d["age"] = q.data.replace("age_", "")
    else:
        d["age"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_AGE)
    msg = update.callback_query or update.message
    if update.callback_query:
        await _step(update.callback_query, lang, 4, TS, "candidate.step_nationality", kb.nationality_kb(lang))
    else:
        await update.message.reply_text(f"{progress(lang,4,TS)}\n\n{t('candidate.step_nationality', lang)}",
            reply_markup=kb.nationality_kb(lang))
    return C_NATIONALITY

async def nationality(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "nat_other":
            await q.edit_message_text(f"{progress(lang,4,TS)}\n\n{t('candidate.step_nationality', lang)}\n{t('common.or_type', lang)}")
            return C_NATIONALITY
        mapping = {"cn":"🇨🇳","vn":"🇻🇳","kh":"🇰🇭","ph":"🇵🇭","th":"🇹🇭"}
        code = q.data.replace("nat_","")
        opts = t("options.nationality", lang)
        vals = ["cn","vn","kh","ph","th"]
        idx = vals.index(code) if code in vals else -1
        d["nationality"] = opts[idx] if idx >= 0 else code
    else:
        d["nationality"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_NATIONALITY)
    if update.callback_query:
        await update.callback_query.edit_message_text(f"{progress(lang,5,TS)}\n\n{t('candidate.step_city', lang)}")
    else:
        await update.message.reply_text(f"{progress(lang,5,TS)}\n\n{t('candidate.step_city', lang)}")
    return C_CITY

async def city(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    d["city"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_CITY)
    await update.message.reply_text(f"{progress(lang,6,TS)}\n\n{t('candidate.step_phone', lang)}")
    return C_PHONE

async def phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    d["phone"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_PHONE)
    ctx.user_data["_ms_languages"] = set()
    await update.message.reply_text(
        f"{progress(lang,7,TS)}\n\n{t('candidate.step_languages', lang)}",
        reply_markup=kb.language_kb(lang, set()))
    return C_LANGUAGES

async def languages(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "languages")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["languages"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, C_LANGUAGES)
        await update.message.reply_text(f"{progress(lang,8,TS)}\n\n{t('candidate.step_education', lang)}",
            reply_markup=kb.education_kb(lang))
        return C_EDUCATION
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["languages"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, C_LANGUAGES)
        await _step(q, lang, 8, TS, "candidate.step_education", kb.education_kb(lang))
        return C_EDUCATION
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,7,TS)}\n\n{t('candidate.step_languages', lang)}\n{t('common.or_type', lang)}")
            return C_LANGUAGES
        sel.symmetric_difference_update({val})
        await q.edit_message_text(
            f"{progress(lang,7,TS)}\n\n{t('candidate.step_languages', lang)}",
            reply_markup=kb.language_kb(lang, sel))
    return C_LANGUAGES

async def education(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return _pop(ctx)
    d["education"] = q.data.replace("edu_", "")
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
    _push(ctx, C_EDUCATION)
    await _step(q, lang, 9, TS, "candidate.step_years_exp", kb.years_exp_kb(lang))
    return C_YEARS_EXP

async def years_exp(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    if q.data == "back": return _pop(ctx)
    d["years_exp"] = q.data.replace("yexp_", "")
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
    _push(ctx, C_YEARS_EXP)
    ctx.user_data["_ms_industry"] = set()
    await _step(q, lang, 10, TS, "candidate.step_industry", kb.industry_kb(lang, set()))
    return C_INDUSTRY

async def industry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "industry")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["industry"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, C_INDUSTRY)
        await update.message.reply_text(
            f"{progress(lang,11,TS)}\n\n{t('candidate.step_work_experience', lang)}",
            reply_markup=kb.skip_back_kb(lang))
        return C_WORK_EXPERIENCE
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["industry"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, C_INDUSTRY)
        await _step(q, lang, 11, TS, "candidate.step_work_experience", kb.skip_back_kb(lang))
        return C_WORK_EXPERIENCE
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,10,TS)}\n\n{t('candidate.step_industry', lang)}\n{t('common.or_type', lang)}")
            return C_INDUSTRY
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,10,TS)}\n\n{t('candidate.step_industry', lang)}",
            reply_markup=kb.industry_kb(lang, sel))
    return C_INDUSTRY

async def work_experience(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "skip":
            d["work_experience"] = ""
    else:
        d["work_experience"] = _limit_work_experience(update.message.text.strip())
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_WORK_EXPERIENCE)
    ctx.user_data["_ms_position"] = set()
    msg = update.message or update.callback_query
    if update.callback_query:
        await _step(update.callback_query, lang, 12, TS, "candidate.step_position", kb.position_kb(lang, set()))
    else:
        await msg.reply_text(f"{progress(lang,12,TS)}\n\n{t('candidate.step_position', lang)}",
            reply_markup=kb.position_kb(lang, set()))
    return C_POSITION


def _limit_work_experience(text: str) -> str:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if len(blocks) <= WORK_EXPERIENCE_LIMIT:
        return text
    return "\n\n".join(blocks[:WORK_EXPERIENCE_LIMIT])

async def position(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "position")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["position"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, C_POSITION)
        await update.message.reply_text(f"{progress(lang,13,TS)}\n\n{t('candidate.step_salary', lang)}",
            reply_markup=kb.salary_candidate_kb(lang))
        return C_SALARY
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["position"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, C_POSITION)
        await _step(q, lang, 13, TS, "candidate.step_salary", kb.salary_candidate_kb(lang))
        return C_SALARY
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,12,TS)}\n\n{t('candidate.step_position', lang)}\n{t('common.or_type', lang)}")
            return C_POSITION
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,12,TS)}\n\n{t('candidate.step_position', lang)}",
            reply_markup=kb.position_kb(lang, sel))
    return C_POSITION

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
    _push(ctx, C_SALARY)
    ctx.user_data["_ms_locations"] = set()
    if update.callback_query:
        await _step(update.callback_query, lang, 14, TS, "candidate.step_locations", kb.location_kb(lang, set()))
    else:
        await update.message.reply_text(f"{progress(lang,14,TS)}\n\n{t('candidate.step_locations', lang)}",
            reply_markup=kb.location_kb(lang, set()))
    return C_LOCATIONS

async def locations(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "locations")
    if not update.callback_query:
        sel.add(update.message.text.strip())
        d["locations"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
        _push(ctx, C_LOCATIONS)
        await update.message.reply_text(f"{progress(lang,15,TS)}\n\n{t('candidate.step_available', lang)}",
            reply_markup=kb.available_kb(lang))
        return C_AVAILABLE
    q = update.callback_query; asyncio.create_task(q.answer())
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["locations"] = sel.copy()
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, C_LOCATIONS)
        await _step(q, lang, 15, TS, "candidate.step_available", kb.available_kb(lang))
        return C_AVAILABLE
    if q.data.startswith("ms_"):
        val = q.data[3:]
        if val == "__other__":
            await q.edit_message_text(f"{progress(lang,14,TS)}\n\n{t('candidate.step_locations', lang)}\n{t('common.or_type', lang)}")
            return C_LOCATIONS
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,14,TS)}\n\n{t('candidate.step_locations', lang)}",
            reply_markup=kb.location_kb(lang, sel))
    return C_LOCATIONS

async def available(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "back": return _pop(ctx)
        if q.data == "avail_other":
            await q.edit_message_text(f"{progress(lang,15,TS)}\n\n{t('candidate.step_available', lang)}\n{t('common.or_type', lang)}")
            return C_AVAILABLE
        d["available"] = q.data.replace("avail_","")
    else:
        d["available"] = update.message.text.strip()
    if ctx.user_data.get("edit_return"):
        ctx.user_data.pop("edit_return"); return await _show_review(update, ctx)
    _push(ctx, C_AVAILABLE)
    ctx.user_data["_ms_extras"] = set()
    if update.callback_query:
        await _step(update.callback_query, lang, 16, TS, "candidate.step_extras", kb.extras_kb(lang, set()))
    else:
        await update.message.reply_text(f"{progress(lang,16,TS)}\n\n{t('candidate.step_extras', lang)}",
            reply_markup=kb.extras_kb(lang, set()))
    return C_EXTRAS

async def extras(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx); d = _d(ctx)
    sel = _ms(ctx, "extras")
    if q.data == "back": return _pop(ctx)
    if q.data == "ms_done":
        d["cambodia_exp"] = "cambodia_exp" in sel
        d["accommodation"] = "accommodation" in sel
        d["visa"] = "visa" in sel
        if ctx.user_data.get("edit_return"):
            ctx.user_data.pop("edit_return"); return await _show_review_q(q, ctx)
        _push(ctx, C_EXTRAS)
        await q.edit_message_text(f"{progress(lang,17,TS)}\n\n{t('candidate.step_notes', lang)}",
            reply_markup=kb.skip_back_kb(lang))
        return C_NOTES
    if q.data.startswith("ms_"):
        val = q.data[3:]
        sel.symmetric_difference_update({val})
        await q.edit_message_text(f"{progress(lang,16,TS)}\n\n{t('candidate.step_extras', lang)}",
            reply_markup=kb.extras_kb(lang, sel))
    return C_EXTRAS

async def notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    if update.callback_query:
        q = update.callback_query; asyncio.create_task(q.answer())
        if q.data == "skip": d["notes"] = ""
        elif q.data == "back": return _pop(ctx)
    else:
        d["notes"] = update.message.text.strip()
    return await _show_review(update, ctx)

async def _show_review(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = candidate_review_card(d, lang)
    msg = update.message or update.callback_query.message
    await msg.reply_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return C_REVIEW

async def _show_review_q(q, ctx) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    txt, flds = candidate_review_card(d, lang)
    await q.edit_message_text(txt, reply_markup=kb.review_edit_kb(flds, lang))
    return C_REVIEW

# Map field keys to states for inline editing
_EDIT_MAP = {
    "name": C_NAME, "gender": C_GENDER, "age": C_AGE,
    "nationality": C_NATIONALITY, "city": C_CITY, "phone": C_PHONE,
    "languages": C_LANGUAGES, "education": C_EDUCATION,
    "years_exp": C_YEARS_EXP, "industry": C_INDUSTRY,
    "work_experience": C_WORK_EXPERIENCE,
    "position": C_POSITION, "salary": C_SALARY,
    "locations": C_LOCATIONS, "available": C_AVAILABLE,
    "cambodia_exp": C_EXTRAS, "accommodation": C_EXTRAS,
    "visa": C_EXTRAS, "notes": C_NOTES,
}

async def review(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; asyncio.create_task(q.answer()); lang = get_lang(ctx)
    if q.data == "confirm_submit": return await _submit(update, ctx)
    if q.data == "confirm_cancel":
        ctx.user_data.clear()
        await q.edit_message_text(t("common.cancel_confirm", lang))
        return ConversationHandler.END
    if q.data in {"skip", "back"} and ctx.user_data.get("candidate_upload_kind"):
        ctx.user_data.pop("candidate_upload_kind", None)
        return await _show_review_q(q, ctx)
    if q.data == "noop": return C_REVIEW
    if q.data in {"upload_resume", "upload_attachment"}:
        kind = "resume" if q.data == "upload_resume" else "attachment"
        ctx.user_data["candidate_upload_kind"] = kind
        key = "candidate.step_resume" if kind == "resume" else "candidate.step_attachment"
        await q.edit_message_text(t(key, lang), reply_markup=kb.skip_back_kb(lang))
        return C_REVIEW
    if q.data.startswith("edit_"):
        field = q.data.replace("edit_", "")
        if field in {"resume", "attachments"}:
            kind = "resume" if field == "resume" else "attachment"
            ctx.user_data["candidate_upload_kind"] = kind
            key = "candidate.step_resume" if kind == "resume" else "candidate.step_attachment"
            await q.edit_message_text(t(key, lang), reply_markup=kb.skip_back_kb(lang))
            return C_REVIEW
        ctx.user_data["edit_return"] = True
        state = _EDIT_MAP.get(field, C_REVIEW)
        # Re-send the appropriate step
        step_map = {
            C_NAME: ("candidate.step_name", None, 1),
            C_GENDER: ("candidate.step_gender", kb.gender_kb(lang), 2),
            C_AGE: ("candidate.step_age", kb.age_kb(lang), 3),
            C_NATIONALITY: ("candidate.step_nationality", kb.nationality_kb(lang), 4),
            C_CITY: ("candidate.step_city", None, 5),
            C_PHONE: ("candidate.step_phone", None, 6),
            C_LANGUAGES: ("candidate.step_languages", kb.language_kb(lang, set()), 7),
            C_EDUCATION: ("candidate.step_education", kb.education_kb(lang), 8),
            C_YEARS_EXP: ("candidate.step_years_exp", kb.years_exp_kb(lang), 9),
            C_INDUSTRY: ("candidate.step_industry", kb.industry_kb(lang, set()), 10),
            C_WORK_EXPERIENCE: ("candidate.step_work_experience", kb.skip_back_kb(lang), 11),
            C_POSITION: ("candidate.step_position", kb.position_kb(lang, set()), 12),
            C_SALARY: ("candidate.step_salary", kb.salary_candidate_kb(lang), 13),
            C_LOCATIONS: ("candidate.step_locations", kb.location_kb(lang, set()), 14),
            C_AVAILABLE: ("candidate.step_available", kb.available_kb(lang), 15),
            C_EXTRAS: ("candidate.step_extras", kb.extras_kb(lang, set()), 16),
            C_NOTES: ("candidate.step_notes", kb.skip_back_kb(lang), 17),
        }
        info = step_map.get(state)
        if info:
            key, markup, step = info
            txt = f"{progress(lang, step, TS)}\n\n{t(key, lang)}"
            await q.edit_message_text(txt, reply_markup=markup)
        return state
    return C_REVIEW


async def review_upload(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_lang(ctx); d = _d(ctx)
    kind = ctx.user_data.pop("candidate_upload_kind", "attachment")
    try:
        upload = await _download_candidate_file(update, kind)
        if not upload:
            await update.message.reply_text(t("candidate.step_attachment", lang), reply_markup=kb.skip_back_kb(lang))
            return C_REVIEW
        link = await drive.upload_file(upload["bytes"], upload["filename"], upload["mime"])
        if not link:
            raise ValueError("empty drive link")
        if kind == "resume":
            d["resume_link"] = link
        else:
            d["attachment_link"] = link
        await update.message.reply_text(t("common.upload_success", lang))
    except Exception as e:
        logger.error(f"Candidate {kind} upload failed: {e}")
        await update.message.reply_text(t("common.upload_fail", lang))
    return await _show_review(update, ctx)

async def _submit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query; lang = get_lang(ctx); d = _d(ctx)
    user = update.effective_user
    try:
        rec = CandidateRecord(
            lang=lang, name=d.get("name",""), gender=d.get("gender",""),
            age=str(d.get("age","")), nationality=d.get("nationality",""),
            current_city=d.get("city",""),
            telegram_username=f"@{user.username}" if user.username else "",
            telegram_user_id=user.id, phone_whatsapp=d.get("phone",""),
            languages=", ".join(d["languages"]) if isinstance(d.get("languages"), set) else str(d.get("languages","")),
            education=d.get("education",""), years_experience=d.get("years_exp",""),
            industry_experience=", ".join(d["industry"]) if isinstance(d.get("industry"), set) else str(d.get("industry","")),
            work_experience=d.get("work_experience",""),
            desired_position=", ".join(d["position"]) if isinstance(d.get("position"), set) else str(d.get("position","")),
            desired_salary=d.get("salary",""),
            preferred_locations=", ".join(d["locations"]) if isinstance(d.get("locations"), set) else str(d.get("locations","")),
            available_from=d.get("available",""),
            cambodia_experience="Yes" if d.get("cambodia_exp") else "No",
            needs_accommodation="Yes" if d.get("accommodation") else "No",
            needs_visa_support="Yes" if d.get("visa") else "No",
            resume_drive_link=d.get("resume_link",""),
            attachment_drive_link=d.get("attachment_link",""),
            notes=d.get("notes",""),
            raw_json=d.get("raw_json",""),
        )
        # Generate AI summary
        ai = await gemini.generate_candidate_summary(d, lang)
        rec.ai_summary = ai.get("ai_summary","")
        rec.ai_tags = ai.get("ai_tags","")
        rec.ai_recommended_roles = ai.get("ai_recommended_roles","")
        rec.ai_risk_notes = ai.get("ai_risk_notes","")
        # Save to sheets
        row = rec.to_row()
        record_id = await sheets.append_row("candidates", row, "C")
        rec.record_id = record_id
        await q.edit_message_text(t("candidate.submit_success", lang))
        # Notify internal group
        notify_data = {
            "record_id": record_id, "name": rec.name, "nationality": rec.nationality,
            "age": rec.age, "city": rec.current_city, "languages": rec.languages,
            "position": rec.desired_position, "salary": rec.desired_salary,
            "resume_link": rec.resume_drive_link or "无",
            "ai_tags": rec.ai_tags, "ai_summary": rec.ai_summary,
        }
        try:
            await notifier.notify_new_candidate(ctx.bot, notify_data, lang)
        except Exception as ne:
            logger.error(f"Failed to notify internal group: {ne}")
        ctx.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Candidate submit failed: {e}")
        await q.edit_message_text(t("common.submit_fail", lang))
        return C_REVIEW
