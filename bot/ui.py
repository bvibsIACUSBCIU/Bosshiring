"""
bot/ui.py — Progress bar formatter, review card builders.
"""
from services.i18n import t


def progress(lang: str, current: int, total: int) -> str:
    """Return progress indicator string like '📝 3 / 12'."""
    return t("common.progress", lang, current=current, total=total)


def candidate_review_card(data: dict, lang: str) -> tuple[str, list[tuple[str, str]]]:
    """Build candidate review text and field list for inline edit buttons.
    Returns (text, [(field_key, display_line), ...])
    """
    fields_map = [
        ("name", "candidate.field_name"),
        ("gender", "candidate.field_gender"),
        ("age", "candidate.field_age"),
        ("nationality", "candidate.field_nationality"),
        ("city", "candidate.field_city"),
        ("phone", "candidate.field_phone"),
        ("languages", "candidate.field_languages"),
        ("education", "candidate.field_education"),
        ("years_exp", "candidate.field_years_exp"),
        ("industry", "candidate.field_industry"),
        ("position", "candidate.field_position"),
        ("salary", "candidate.field_salary"),
        ("locations", "candidate.field_locations"),
        ("available", "candidate.field_available"),
        ("cambodia_exp", "candidate.field_cambodia"),
        ("accommodation", "candidate.field_accommodation"),
        ("visa", "candidate.field_visa"),
        ("resume", "candidate.field_resume"),
        ("notes", "candidate.field_notes"),
    ]

    lines = [t("candidate.review_title", lang), ""]
    field_list = []
    ns = t("common.not_specified", lang)

    for key, label_key in fields_map:
        label = t(label_key, lang)
        val = data.get(key, "")
        if isinstance(val, (list, set)):
            val = ", ".join(val) if val else ns
        elif isinstance(val, bool):
            val = t("common.yes", lang) if val else t("common.no", lang)
        elif not val:
            val = ns

        # Special handling for resume field
        if key == "resume":
            if data.get("resume_link"):
                val = t("candidate.resume_uploaded", lang)
            else:
                val = t("candidate.resume_not_uploaded", lang)

        line = t("candidate.review_field", lang, label=label, value=val)
        lines.append(line)
        field_list.append((key, line))

    text = "\n".join(lines)
    return text, field_list


def company_review_card(data: dict, lang: str) -> tuple[str, list[tuple[str, str]]]:
    """Build company review text and field list."""
    fields_map = [
        ("company_name", "company.field_company_name"),
        ("industry", "company.field_industry"),
        ("address", "company.field_address"),
        ("contact_name", "company.field_contact_name"),
        ("contact_title", "company.field_contact_title"),
        ("phone", "company.field_phone"),
        ("position", "company.field_position"),
        ("headcount", "company.field_headcount"),
        ("location", "company.field_location"),
        ("salary", "company.field_salary"),
        ("hours", "company.field_hours"),
        ("language_req", "company.field_language"),
        ("experience_req", "company.field_experience"),
        ("benefits_accommodation", "company.field_benefits_accommodation"),
        ("benefits_visa", "company.field_benefits_visa"),
        ("start_date", "company.field_start_date"),
        ("jd", "company.field_jd"),
        ("service_fee", "company.field_service_fee"),
        ("upload_link", "company.field_upload"),
        ("notes", "company.field_notes"),
    ]

    lines = [t("company.review_title", lang), ""]
    field_list = []
    ns = t("common.not_specified", lang)

    for key, label_key in fields_map:
        label = t(label_key, lang)
        val = data.get(key, "")
        if isinstance(val, (list, set)):
            val = ", ".join(val) if val else ns
        elif isinstance(val, bool):
            val = t("common.yes", lang) if val else t("common.no", lang)
        elif not val:
            val = ns
        line = f"{label}：{val}"
        lines.append(line)
        field_list.append((key, line))

    return "\n".join(lines), field_list


def boss_show_review_card(data: dict, lang: str) -> tuple[str, list[tuple[str, str]]]:
    """Build Boss Show review text and field list."""
    fields_map = [
        ("company", "boss_show.field_company"),
        ("industry", "boss_show.field_industry"),
        ("contact", "boss_show.field_contact"),
        ("contact_info", "boss_show.field_contact_info"),
        ("topic", "boss_show.field_topic"),
        ("intro", "boss_show.field_intro"),
        ("intent", "boss_show.field_intent"),
    ]

    lines = [t("boss_show.review_title", lang), ""]
    field_list = []
    ns = t("common.not_specified", lang)

    for key, label_key in fields_map:
        label = t(label_key, lang)
        val = data.get(key, "") or ns
        line = f"{label}：{val}"
        lines.append(line)
        field_list.append((key, line))

    return "\n".join(lines), field_list
