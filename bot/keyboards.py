"""
bot/keyboards.py — All keyboard builders (lang-aware, zero hardcoded strings).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from services.i18n import t


# ---------------------------------------------------------------------------
#  Generic builders
# ---------------------------------------------------------------------------

def multiselect_kb(
    options: list[tuple[str, str]],
    selected: set[str],
    done_label: str,
) -> InlineKeyboardMarkup:
    """Toggle-style multi-select keyboard.
    options = [(display_text, callback_value), ...]
    """
    rows = []
    for label, val in options:
        prefix = "☑ " if val in selected else "☐ "
        rows.append([InlineKeyboardButton(prefix + label, callback_data=f"ms_{val}")])
    rows.append([InlineKeyboardButton(done_label, callback_data="ms_done")])
    return InlineKeyboardMarkup(rows)


def single_select_kb(
    options: list[tuple[str, str]],
    prefix: str = "sel",
) -> InlineKeyboardMarkup:
    """One-tap single-choice keyboard."""
    rows = [[InlineKeyboardButton(label, callback_data=f"{prefix}_{val}")]
            for label, val in options]
    return InlineKeyboardMarkup(rows)


def back_button(lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(t("common.back", lang), callback_data="back")


def skip_button(lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(t("common.skip", lang), callback_data="skip")


def _with_back(rows: list[list[InlineKeyboardButton]], lang: str) -> InlineKeyboardMarkup:
    """Append a back-button row."""
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def _opts(key: str, lang: str) -> list[str]:
    """Load option list from locale."""
    return t(key, lang)


# ---------------------------------------------------------------------------
#  Language selection (bootstrap — trilingual, hardcoded per spec)
# ---------------------------------------------------------------------------

def lang_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇰🇭 ភាសាខ្មែរ", callback_data="lang_km")],
    ])


# ---------------------------------------------------------------------------
#  Main menu
# ---------------------------------------------------------------------------

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("menu.candidate", lang), callback_data="menu_candidate")],
        [InlineKeyboardButton(t("menu.company", lang), callback_data="menu_company")],
        [InlineKeyboardButton(t("menu.boss_show", lang), callback_data="menu_boss_show")],
        [InlineKeyboardButton(t("menu.contact", lang), callback_data="menu_contact")],
    ])


# ---------------------------------------------------------------------------
#  Candidate keyboards
# ---------------------------------------------------------------------------

def gender_kb(lang: str) -> InlineKeyboardMarkup:
    labels = _opts("options.gender", lang)
    vals = ["male", "female", "other"]
    rows = [[InlineKeyboardButton(labels[i], callback_data=f"gender_{vals[i]}")]
            for i in range(len(labels))]
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def age_kb(lang: str) -> InlineKeyboardMarkup:
    ranges = _opts("options.age_ranges", lang)
    rows = [[InlineKeyboardButton(r, callback_data=f"age_{r}")] for r in ranges]
    rows.append([InlineKeyboardButton(t("common.other", lang), callback_data="age_other")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def nationality_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.nationality", lang)
    vals = ["cn", "vn", "kh", "ph", "th"]
    rows = [[InlineKeyboardButton(items[i], callback_data=f"nat_{vals[i]}")]
            for i in range(len(items))]
    rows.append([InlineKeyboardButton(t("common.other", lang), callback_data="nat_other")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def language_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    items = _opts("options.languages", lang)
    opts = [(lbl, lbl) for lbl in items]
    opts.append((t("common.other", lang), "__other__"))
    return multiselect_kb(opts, selected, t("common.done", lang))


def education_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.education", lang)
    rows = [[InlineKeyboardButton(e, callback_data=f"edu_{e}")] for e in items]
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def years_exp_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.years_exp", lang)
    rows = [[InlineKeyboardButton(e, callback_data=f"yexp_{e}")] for e in items]
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def industry_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    items = _opts("options.industry", lang)
    opts = [(lbl, lbl) for lbl in items]
    opts.append((t("common.other", lang), "__other__"))
    return multiselect_kb(opts, selected, t("common.done", lang))


def position_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    items = _opts("options.position", lang)
    opts = [(lbl, lbl) for lbl in items]
    opts.append((t("common.other", lang), "__other__"))
    return multiselect_kb(opts, selected, t("common.done", lang))


def salary_candidate_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.salary_candidate", lang)
    rows = [[InlineKeyboardButton(s, callback_data=f"sal_{s}")] for s in items]
    rows.append([InlineKeyboardButton(t("common.negotiate", lang), callback_data="sal_negotiate")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def salary_company_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.salary_company", lang)
    rows = [[InlineKeyboardButton(s, callback_data=f"sal_{s}")] for s in items]
    rows.append([InlineKeyboardButton(t("common.negotiate", lang), callback_data="sal_negotiate")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def location_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    items = _opts("options.locations", lang)
    opts = [(lbl, lbl) for lbl in items]
    opts.append((t("common.other", lang), "__other__"))
    return multiselect_kb(opts, selected, t("common.done", lang))


def available_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.available", lang)
    rows = [[InlineKeyboardButton(a, callback_data=f"avail_{a}")] for a in items]
    rows.append([InlineKeyboardButton(t("common.other", lang), callback_data="avail_other")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def extras_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    items = _opts("options.extras", lang)
    vals = ["cambodia_exp", "accommodation", "visa"]
    opts = [(items[i], vals[i]) for i in range(len(items))]
    return multiselect_kb(opts, selected, t("common.done", lang))


def resume_choice_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("common.upload_file", lang), callback_data="resume_upload")],
        [InlineKeyboardButton(t("common.manual_fill", lang), callback_data="resume_manual")],
        [InlineKeyboardButton(t("common.skip", lang), callback_data="resume_skip")],
        [back_button(lang)],
    ])


def yes_no_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("common.yes", lang), callback_data="yn_yes"),
         InlineKeyboardButton(t("common.no", lang), callback_data="yn_no")],
        [back_button(lang)],
    ])


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("common.confirm", lang), callback_data="confirm_submit")],
        [InlineKeyboardButton(t("common.re_enter", lang), callback_data="confirm_edit")],
        [InlineKeyboardButton(t("common.cancel", lang), callback_data="confirm_cancel")],
    ])


def skip_back_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [skip_button(lang)],
        [back_button(lang)],
    ])


# ---------------------------------------------------------------------------
#  Company keyboards
# ---------------------------------------------------------------------------

def headcount_kb(lang: str) -> InlineKeyboardMarkup:
    items = t("company.headcount_options", lang)
    rows = [[InlineKeyboardButton(h, callback_data=f"hc_{h}")] for h in items]
    rows.append([InlineKeyboardButton(t("common.other", lang), callback_data="hc_other")])
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def working_hours_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.working_hours", lang)
    rows = [[InlineKeyboardButton(h, callback_data=f"hours_{h}")] for h in items]
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def experience_req_kb(lang: str) -> InlineKeyboardMarkup:
    items = _opts("options.experience_req", lang)
    rows = [[InlineKeyboardButton(e, callback_data=f"expreq_{e}")] for e in items]
    rows.append([back_button(lang)])
    return InlineKeyboardMarkup(rows)


def company_benefits_kb(lang: str, selected: set[str]) -> InlineKeyboardMarkup:
    opts = [
        (t("company.benefits_accommodation", lang), "accommodation"),
        (t("company.benefits_visa", lang), "visa"),
    ]
    return multiselect_kb(opts, selected, t("common.done", lang))


def service_fee_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("company.service_fee_accept", lang), callback_data="fee_accept")],
        [InlineKeyboardButton(t("company.service_fee_decline", lang), callback_data="fee_decline")],
    ])


# ---------------------------------------------------------------------------
#  Boss Show keyboards
# ---------------------------------------------------------------------------

def boss_show_intro_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("boss_show.apply_btn", lang), callback_data="bs_apply")],
        [back_button(lang)],
    ])


def boss_show_intent_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("boss_show.intent_interview", lang), callback_data="bsi_interview")],
        [InlineKeyboardButton(t("boss_show.intent_brand", lang), callback_data="bsi_brand")],
        [InlineKeyboardButton(t("boss_show.intent_hire", lang), callback_data="bsi_hire")],
        [back_button(lang)],
    ])


# ---------------------------------------------------------------------------
#  Review card edit buttons
# ---------------------------------------------------------------------------

def review_edit_kb(fields: list[tuple[str, str]], lang: str) -> InlineKeyboardMarkup:
    """Build review card with [✏️] buttons per field.
    fields = [(field_key, display_line), ...]
    """
    rows = []
    for fkey, line in fields:
        rows.append([
            InlineKeyboardButton(line, callback_data="noop"),
            InlineKeyboardButton("✏️", callback_data=f"edit_{fkey}"),
        ])
    rows.append([
        InlineKeyboardButton(t("common.confirm", lang), callback_data="confirm_submit"),
        InlineKeyboardButton(t("common.cancel", lang), callback_data="confirm_cancel"),
    ])
    return InlineKeyboardMarkup(rows)
