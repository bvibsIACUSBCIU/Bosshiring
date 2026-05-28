"""
main.py — Register all handlers and run the bot.
"""
import logging
import os
import urllib.request

# Auto-detect and set system proxy environment variables
for proto, url in urllib.request.getproxies().items():
    env_key = f"{proto}_proxy"
    if env_key not in os.environ:
        os.environ[env_key] = url
        os.environ[env_key.upper()] = url

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, PicklePersistence, filters,
    ContextTypes,
)

import config
from bot.states import *
from bot.handlers import start, candidate, company, boss_show, contact
from services.i18n import validate_locales

logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    # Validate locale files have identical key sets
    validate_locales()
    logger.info("Locale validation passed ✓")

    # Ensure data dir exists
    os.makedirs("data", exist_ok=True)

    persistence = PicklePersistence(filepath="data/persistence.pkl")

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start.start),
            CommandHandler("lang", start.lang_command),
        ],
        states={
            # Language & Menu
            LANG_SELECT: [
                CallbackQueryHandler(start.lang_selected, pattern=r"^lang_"),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(candidate.entry, pattern=r"^menu_candidate$"),
                CallbackQueryHandler(company.entry, pattern=r"^menu_company$"),
                CallbackQueryHandler(boss_show.entry, pattern=r"^menu_boss_show$"),
                CallbackQueryHandler(contact.show_contact, pattern=r"^menu_contact$"),
                CallbackQueryHandler(start.show_main_menu, pattern=r"^back$"),
            ],

            # ── Candidate flow ──
            C_RESUME_CHOICE: [
                CallbackQueryHandler(candidate.resume_choice, pattern=r"^(resume_upload|resume_manual|resume_skip|back)$"),
            ],
            C_RESUME_UPLOAD: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, candidate.resume_upload),
                CallbackQueryHandler(candidate.resume_upload, pattern=r"^(skip|back)$"),
            ],
            C_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.name),
                CallbackQueryHandler(candidate.name, pattern=r"^back$"),
            ],
            C_GENDER: [CallbackQueryHandler(candidate.gender, pattern=r"^(gender_|back)")],
            C_AGE: [
                CallbackQueryHandler(candidate.age, pattern=r"^(age_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.age),
            ],
            C_NATIONALITY: [
                CallbackQueryHandler(candidate.nationality, pattern=r"^(nat_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.nationality),
            ],
            C_CITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.city),
            ],
            C_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.phone),
            ],
            C_LANGUAGES: [
                CallbackQueryHandler(candidate.languages, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.languages),
            ],
            C_EDUCATION: [CallbackQueryHandler(candidate.education, pattern=r"^(edu_|back$)")],
            C_YEARS_EXP: [CallbackQueryHandler(candidate.years_exp, pattern=r"^(yexp_|back$)")],
            C_INDUSTRY: [
                CallbackQueryHandler(candidate.industry, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.industry),
            ],
            C_POSITION: [
                CallbackQueryHandler(candidate.position, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.position),
            ],
            C_SALARY: [
                CallbackQueryHandler(candidate.salary, pattern=r"^(sal_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.salary),
            ],
            C_LOCATIONS: [
                CallbackQueryHandler(candidate.locations, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.locations),
            ],
            C_AVAILABLE: [
                CallbackQueryHandler(candidate.available, pattern=r"^(avail_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.available),
            ],
            C_EXTRAS: [CallbackQueryHandler(candidate.extras, pattern=r"^(ms_|back$)")],
            C_NOTES: [
                CallbackQueryHandler(candidate.notes, pattern=r"^(skip|back)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, candidate.notes),
            ],
            C_REVIEW: [CallbackQueryHandler(candidate.review, pattern=r"^(confirm_submit|confirm_cancel|noop|edit_)")],

            # ── Company flow ──
            B_COMPANY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.company_name)],
            B_INDUSTRY: [
                CallbackQueryHandler(company.industry, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.industry),
            ],
            B_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.address)],
            B_CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.contact_name)],
            B_CONTACT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.contact_title)],
            B_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.phone)],
            B_POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, company.position)],
            B_HEADCOUNT: [
                CallbackQueryHandler(company.headcount, pattern=r"^(hc_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.headcount),
            ],
            B_LOCATION: [
                CallbackQueryHandler(company.location, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.location),
            ],
            B_SALARY: [
                CallbackQueryHandler(company.salary, pattern=r"^(sal_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.salary),
            ],
            B_HOURS: [CallbackQueryHandler(company.hours, pattern=r"^(hours_|back$)")],
            B_LANGUAGE: [
                CallbackQueryHandler(company.language_req, pattern=r"^(ms_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.language_req),
            ],
            B_EXPERIENCE: [CallbackQueryHandler(company.experience, pattern=r"^(expreq_|back$)")],
            B_BENEFITS: [CallbackQueryHandler(company.benefits, pattern=r"^(ms_|back$)")],
            B_START_DATE: [
                CallbackQueryHandler(company.start_date, pattern=r"^(avail_|back$)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.start_date),
            ],
            B_JD: [
                CallbackQueryHandler(company.jd, pattern=r"^(skip|back)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, company.jd),
            ],
            B_SERVICE_FEE: [CallbackQueryHandler(company.service_fee, pattern=r"^fee_")],
            B_REVIEW: [CallbackQueryHandler(company.review, pattern=r"^(confirm_submit|confirm_cancel|noop|edit_)")],

            # ── Boss Show flow ──
            BS_COMPANY: [
                CallbackQueryHandler(boss_show.apply_start, pattern=r"^bs_apply$"),
                CallbackQueryHandler(boss_show.apply_start, pattern=r"^back$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_company),
            ],
            BS_INDUSTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_industry)],
            BS_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_contact)],
            BS_CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_contact_info)],
            BS_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_topic)],
            BS_INTRO: [
                CallbackQueryHandler(boss_show.bs_intro, pattern=r"^(skip|back)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, boss_show.bs_intro),
            ],
            BS_INTENT: [CallbackQueryHandler(boss_show.bs_intent, pattern=r"^(bsi_|back$)")],
            BS_REVIEW: [CallbackQueryHandler(boss_show.review, pattern=r"^(confirm_submit|confirm_cancel|noop|edit_)")],
        },
        fallbacks=[
            CommandHandler("cancel", start.cancel),
            CommandHandler("lang", start.lang_command),
            CommandHandler("start", start.start),
        ],
        name="main_conversation",
        persistent=True,
        conversation_timeout=config.CONVERSATION_TIMEOUT,
    )

    app.add_handler(conv)

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            from services.i18n import get_lang, t
            lang = get_lang(context)
            try:
                await update.effective_message.reply_text(t("common.submit_fail", lang))
            except Exception as e:
                logger.error(f"Failed to send error message to user: {e}")

    app.add_error_handler(error_handler)
    logger.info("Bot starting... 🚀")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
