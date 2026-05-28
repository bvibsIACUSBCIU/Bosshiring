## ⚠️ 终极开发铁律 (Ultimate Architecture Constraints)

1. **绝对零硬编码 (Absolute Zero Hardcoding)**:
   - 严禁在 `bot/` 目录下的任何 Handler 中出现中、英、高棉语的任何字面量（如 `"确定"`, `"Age"`, `"សូមទោស"`）。
   - 唯一的特外情况是 `start.py` 中的 `BOOTSTRAP_PROMPT` 全语种拼接常量，用于冷启动。
   - 格式化文本一律使用 `t("key.path", lang, var=value)` 形式。   

3. **智能上下文返回机制 (Smart Inline Edit Routing)**:
   - 当用户在 Review 界面点击某项数据旁的 `[✏️]` 按钮时，设置 `context.user_data["edit_return_target"] = CURRENT_REVIEW_STATE`。
   - 当用户在该状态重新输入或选择完毕后，业务代码必须检测该 Flag，如果存在，则直接用 `edit_message_text` 弹回 Review 界面，严禁让用户继续向下线性走完剩余流程。

4. **输入容错防死锁 (Input Validation & anti-deadlock)**:
   - 当进入需要按钮选择的状态（如性别、学历）时，若用户执意在输入框内打字输入，系统必须拦截并重新发送当前界面的 Inline 键盘，并附带 `t("common.or_type", lang)` 的提示，确保会话流绝不中断或卡死。# Boss Hiring — Phase 1 Build Prompt (v2)

## Project Overview

Telegram-based recruitment data collection system for **Boss Hiring** headhunting agency.  
Collects resumes from job seekers and job requirements from companies, parses documents via Gemini AI, stores data in Google Sheets, files in Google Drive, and notifies an internal Telegram group on every submission.

**Supported languages**: Chinese (zh), English (en), Khmer (km)  
**Language rule**: Zero hardcoded user-facing strings anywhere in code. Every string rendered to users must be looked up via the i18n service.

---

## Tech Stack

- **Language**: Python 3.11+
- **Bot**: `python-telegram-bot` v21 (async, `ConversationHandler`, `PicklePersistence`)
- **AI**: `google-genai` — model `gemini-2.5-flash`
- **Sheets**: `gspread` + Google Sheets API v4
- **Drive**: `google-api-python-client` Drive v3
- **Config**: `python-dotenv`

---

## Repository Structure

```
boss-hiring-bot/
├── main.py
├── config.py
├── locales/
│   ├── zh.json
│   ├── en.json
│   └── km.json
├── bot/
│   ├── handlers/
│   │   ├── start.py          # /start, language select, main menu
│   │   ├── candidate.py      # Job seeker ConversationHandler
│   │   ├── company.py        # HR / company ConversationHandler
│   │   ├── boss_show.py      # Boss Show cooperation flow
│   │   └── contact.py        # Static contact card
│   ├── keyboards.py          # All keyboard builders (lang-aware)
│   └── ui.py                 # Progress bar, card formatters
├── services/
│   ├── i18n.py               # Translation lookup, lang helpers
│   ├── gemini.py             # Document parse + summary generation
│   ├── sheets.py             # Append / seq / update
│   ├── drive.py              # Upload + share link
│   └── notifier.py           # Internal group alerts
├── models/
│   ├── candidate.py          # CandidateRecord dataclass
│   └── company.py            # CompanyRecord dataclass
├── prompts/
│   ├── candidate_parse.txt
│   ├── candidate_summary.txt
│   └── company_summary.txt
├── data/                     # Runtime data (gitignored)
│   ├── persistence.pkl
│   └── failed_submissions.jsonl
└── requirements.txt
```

---

## Environment Variables

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_INTERNAL_GROUP_ID=      # e.g. -1001234567890
GEMINI_API_KEY=
GOOGLE_SERVICE_ACCOUNT_JSON=     # path to service account key file
GOOGLE_SHEET_ID=
GOOGLE_DRIVE_FOLDER_ID=
```

---

## i18n Architecture

### `services/i18n.py`

```python
import json, os
from functools import lru_cache

SUPPORTED_LANGS = ["zh", "en", "km"]
DEFAULT_LANG = "zh"

@lru_cache(maxsize=3)
def _load(lang: str) -> dict:
    path = os.path.join("locales", f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def t(key: str, lang: str, **kwargs) -> str:
    """Lookup translation by dot-notation key, interpolate {placeholders}."""
    data = _load(lang if lang in SUPPORTED_LANGS else DEFAULT_LANG)
    keys = key.split(".")
    val = data
    for k in keys:
        val = val.get(k, key)  # fall back to key string if missing
    return val.format(**kwargs) if kwargs else val

def get_lang(context) -> str:
    return context.user_data.get("lang", DEFAULT_LANG)
```

**Usage in all handlers**: `t("menu.title", get_lang(context))`  
**Rule**: `t()` is the ONLY way to produce user-facing text. No f-strings, no string literals sent to users.

---

### Locale File Structure (`locales/zh.json` — representative)

```json
{
  "lang_select": {
    "prompt": "请选择语言 / Please select language / សូមជ្រើសរើសភាសា"
  },
  "menu": {
    "title": "👋 你好！欢迎使用 Boss Hiring。\n请选择服务：",
    "candidate": "💼 我要找工作",
    "company": "🏢 企业招聘",
    "boss_show": "🎬 了解Boss来了",
    "contact": "📞 联系客服"
  },
  "common": {
    "yes": "是",
    "no": "否",
    "skip": "跳过",
    "back": "◀ 返回",
    "cancel": "✖ 取消",
    "confirm": "✅ 确认提交",
    "re_enter": "✏️ 重新填写",
    "done": "完成 ✓",
    "other": "其他",
    "not_specified": "未填写",
    "progress": "📝 {current} / {total}",
    "or_type": "或直接输入：",
    "upload_success": "✅ 文件已上传",
    "upload_fail": "⚠️ 上传失败，请重试或跳过",
    "cancel_confirm": "已取消。发送 /start 重新开始。",
    "timeout_msg": "⏱ 会话已超时。发送 /start 重新开始。"
  },
  "candidate": {
    "welcome": "💼 求职登记\n\n我会引导您填写资料。随时可发送 /cancel 取消。",
    "step_name": "请输入您的姓名：",
    "step_gender": "请选择性别：",
    "step_age": "请选择或输入您的年龄：",
    "step_nationality": "请选择国籍：",
    "step_city": "您目前居住的城市：",
    "step_phone": "您的电话 / WhatsApp 号码：",
    "step_languages": "您会哪些语言？（可多选，选完点「完成」）",
    "step_education": "最高学历：",
    "step_years_exp": "工作年限：",
    "step_industry": "过往行业经验（可多选）：",
    "step_position": "期望岗位（可多选）：",
    "step_salary": "期望薪资范围：",
    "step_locations": "可接受工作地点（可多选）：",
    "step_available": "可入职时间：",
    "step_extras": "以下选项请勾选适用项：",
    "step_resume": "请上传简历（PDF / Word / 图片），或点击「跳过」：",
    "step_notes": "其他备注（可选）：",
    "parsing": "⏳ AI 正在解析您的简历，请稍候...",
    "parse_done": "✅ 解析完成！请确认或补充以下信息：",
    "parse_fail": "⚠️ 解析失败，请手动填写。",
    "review_title": "📋 请确认您的求职资料：",
    "review_field": "{label}：{value}",
    "submit_success": "✅ 您的求职资料已提交成功。Boss Hiring 顾问会审核您的资料，并在有合适岗位时联系您。请保持 Telegram 或电话畅通。",
    "gender_male": "男",
    "gender_female": "女",
    "gender_other": "其他",
    "field_name": "姓名",
    "field_gender": "性别",
    "field_age": "年龄",
    "field_nationality": "国籍",
    "field_city": "城市",
    "field_phone": "电话/WA",
    "field_languages": "语言",
    "field_education": "学历",
    "field_years_exp": "工作年限",
    "field_industry": "行业经验",
    "field_position": "期望岗位",
    "field_salary": "期望薪资",
    "field_locations": "工作地点",
    "field_available": "可入职",
    "field_cambodia": "柬埔寨经验",
    "field_accommodation": "需要住宿",
    "field_visa": "需要签证/工作证",
    "field_resume": "简历",
    "field_notes": "备注"
  },
  "company": {
    "welcome": "🏢 企业招聘需求登记\n\n我会引导您填写招聘信息。随时可发送 /cancel 取消。",
    "step_company_name": "公司名称：",
    "step_industry": "所属行业：",
    "step_address": "公司地址：",
    "step_contact_name": "联系人姓名：",
    "step_contact_title": "联系人职位：",
    "step_phone": "联系电话 / WhatsApp：",
    "step_position": "招聘岗位名称：",
    "step_headcount": "招聘人数：",
    "step_location": "工作地点：",
    "step_salary": "薪资范围：",
    "step_hours": "工作时间：",
    "step_language": "语言要求：",
    "step_experience": "工作经验要求：",
    "step_benefits": "以下福利请勾选提供项：",
    "step_start_date": "期望到岗时间：",
    "step_jd": "岗位描述（可选，输入详情或跳过）：",
    "step_service_fee": "📋 服务费规则说明\n\n招聘成功后，服务费为员工入职月薪的 80%，到岗后支付。\n\n请确认是否接受：",
    "service_fee_accept": "✅ 接受服务条款",
    "service_fee_decline": "❌ 不接受",
    "service_fee_declined": "感谢您的咨询。如有疑问，欢迎联系我们的客服团队进一步沟通。",
    "step_upload": "上传企业资料 / 营业执照（可选）：",
    "step_notes": "其他备注（可选）：",
    "review_title": "📋 请确认招聘需求：",
    "submit_success": "✅ 您的招聘需求已提交成功。Boss Hiring 顾问会尽快联系您，确认岗位细节和合作流程。"
  },
  "boss_show": {
    "intro_title": "🎬 Boss来了",
    "intro_body": "《Boss来了》是 Boss Hiring 出品的招聘访谈节目，深入企业一线，展示真实工作环境与企业文化。\n\n如需申请企业采访或品牌合作，请点击下方按钮：",
    "apply_btn": "📝 申请合作",
    "step_company": "企业名称：",
    "step_industry": "所属行业：",
    "step_contact": "联系人姓名：",
    "step_contact_info": "联系方式（电话 / WhatsApp）：",
    "step_topic": "采访主题 / 合作意向简介：",
    "step_intro": "企业简介（可选）：",
    "step_intent": "合作类型：",
    "intent_interview": "企业采访",
    "intent_brand": "品牌曝光",
    "intent_hire": "招聘合作",
    "submit_success": "✅ 合作申请已提交！我们的负责人会尽快与您联系。"
  },
  "contact": {
    "title": "📞 联系 Boss Hiring",
    "body": "Telegram：{telegram}\nWhatsApp：{whatsapp}\n电话：{phone}\n工作时间：周一至周五 09:00–18:00 (GMT+7)\n地址：{address}"
  },
  "notify": {
    "new_candidate": "🆕 【新求职者】#{record_id}\n\n👤 {name} | {nationality} | {age}岁\n📍 {city}\n🗣 {languages}\n💼 {position}\n💰 {salary}\n📎 简历：{resume_link}\n\n🏷 {tags}\n📝 {summary}\n\n⚡️ 请 HR 跟进",
    "new_company": "🆕 【新招聘需求】#{record_id}\n\n🏢 {company} | {industry}\n👤 {contact} ({title})\n📌 {position} × {headcount}人\n📍 {location} | 💰 {salary}\n🗣 {language_req}\n📅 到岗：{start_date}\n\n🏷 {tags}\n📝 {summary}\n\n⚡️ 请 HR 联系企业",
    "new_boss_show": "🆕 【Boss来了合作申请】#{record_id}\n\n🏢 {company} | {industry}\n👤 {contact} | {contact_info}\n🎯 {intent}\n📋 {topic}\n\n⚡️ 请负责人跟进"
  }
}
```

Create `en.json` and `km.json` with **identical key structure**, translated values.  
`km.json` must use proper Unicode Khmer script for all values.

**Validation rule**: On startup, `i18n.py` must assert that all three locale files contain identical key sets. Raise `KeyError` with the missing key if any mismatch is found.

---

## UX Design Principles

### 1. Reduce Typing — Inline Keyboards Everywhere
Use `InlineKeyboardMarkup` for all fixed-choice fields. Text input only for: name, phone, free-text address, job description, notes.

### 2. Progress Indicator
Every step message includes a header line:  
`t("common.progress", lang, current=3, total=12)`  
→ `📝 3 / 12`

### 3. Multi-Select Pattern
For fields accepting multiple values (languages, industries, locations):
- Show toggle buttons: `☐ English`, `☑ 中文`, `☐ ភាសាខ្មែរ`
- Tapping a button toggles its state and edits the message in-place (`edit_message_text`)
- A `t("common.done", lang)` button finalises the selection
- Store selected values in `context.user_data["_multiselect_{field}"]`

```python
# keyboards.py — multi-select builder
def multiselect_kb(options: list[tuple[str,str]], selected: set[str], done_label: str) -> InlineKeyboardMarkup:
    """options = [(display_text, value), ...]"""
    rows = []
    for label, val in options:
        prefix = "☑ " if val in selected else "☐ "
        rows.append([InlineKeyboardButton(prefix + label, callback_data=f"ms_{val}")])
    rows.append([InlineKeyboardButton(done_label, callback_data="ms_done")])
    return InlineKeyboardMarkup(rows)
```

### 4. Quick-Option + Free-Text Fallback
For semi-fixed fields (salary, age, nationality), offer preset buttons plus an `t("common.other", lang)` button that switches to text-input mode.

```
Salary buttons:
[$400–600]  [$600–900]  [$900–1200]  [$1200–1800]  [$1800+]  [Negotiate]
```

### 5. Group Boolean Questions
Instead of asking accommodation/visa/Cambodia experience separately, batch them in one message:

```
⚙️ 其他需求 (1/1)

请勾选适用项：

☑ 有柬埔寨工作经验
☐ 需要住宿支持  
☐ 需要签证/工作证支持

[完成 ✓]
```

Use the same `multiselect_kb` pattern; field values map to boolean flags.

### 6. Resume Upload — Smart Branch

```
Step A: "上传简历，或选择手动填写"
  [📎 上传文件]   [✏️ 手动填写]

If upload:
  → Receive file → upload to Drive → Gemini parse
  → Show pre-filled review card with [✏️ Edit] per field
  → User corrects only missing/wrong fields
  → [✅ 确认提交]

If manual:
  → Step-by-step text/button inputs (normal flow)
```

### 7. Review Card with Inline Editing

After all fields collected, show a summary card. Each field line has an inline `[✏️]` button that jumps back to that field's input state, then returns to review after re-entry.

```
📋 求职资料确认 — 📝 12 / 12

姓名：张伟             [✏️]
性别：男               [✏️]
年龄：28               [✏️]
国籍：中国             [✏️]
城市：金边             [✏️]
电话：+855 12 345 678  [✏️]
语言：中文、英语       [✏️]
学历：本科             [✏️]
工作年限：3年          [✏️]
期望岗位：客服、销售   [✏️]
期望薪资：$800–$1200   [✏️]
简历：✅ 已上传        [✏️]

[✅ 确认提交]   [✖ 取消]
```

Implement with `context.user_data["edit_return"] = True` flag. After any field edit, `ConversationHandler` returns to `REVIEW` state.

### 8. Back Navigation
Every step includes a `t("common.back", lang)` inline button that returns to the previous state.  
Implement with a `state_history: list[int]` in `context.user_data`.

### 9. Language Persistence
Store selected language in `context.user_data["lang"]`. Since `PicklePersistence` is used, it persists across bot restarts per user.  
Allow language change via `/lang` command at any time (resets to language select screen).

### 10. Smart Keyboards — Pre-built Option Lists

Define all option lists in `keyboards.py` as functions that accept `lang` and return translated `InlineKeyboardMarkup`:

```python
def gender_kb(lang): ...        # 3 buttons
def age_kb(lang): ...           # ranges: <25 / 25-30 / 31-35 / 36-40 / 40+ / custom
def nationality_kb(lang): ...   # 🇨🇳 🇻🇳 🇰🇭 🇵🇭 🇹🇭 + Other
def language_kb(lang, selected): ... # multiselect
def education_kb(lang): ...     # High school / Diploma / Bachelor / Master / PhD
def years_exp_kb(lang): ...     # <1 / 1-2 / 3-5 / 5-10 / 10+
def industry_kb(lang, selected): ... # multiselect: Sales / CS / Finance / IT / Marketing / Logistics / Other
def salary_candidate_kb(lang): ... # $400-600 / $600-900 / $900-1200 / $1200-1800 / $1800+ / Negotiate
def salary_company_kb(lang): ...
def location_kb(lang, selected): ... # multiselect: Phnom Penh / Sihanoukville / Siem Reap / Bangkok / Remote / Other
def available_kb(lang): ...     # ASAP / 1 week / 2 weeks / 1 month / Custom
def yes_no_kb(lang): ...        # Yes / No buttons
def confirm_kb(lang): ...       # ✅ Confirm / ✏️ Edit / ✖ Cancel
```

---

## Conversation Flow Implementation

### `/start` Handler (`start.py`)

```
State: LANG_SELECT

1. Send language select message (trilingual prompt — no i18n needed here, it's hardcoded as the bootstrap):
   "请选择语言 / Please select language / សូមជ្រើសរើសភាសា"
   Buttons: [🇨🇳 中文] [🇺🇸 English] [🇰🇭 ភាសាខ្មែរ]

2. On selection: store context.user_data["lang"] = selected_lang

3. Send main menu using t() for all strings:
   [💼 {menu.candidate}]  [🏢 {menu.company}]
   [🎬 {menu.boss_show}]  [📞 {menu.contact}]
```

---

### Candidate Flow States

```python
(
    LANG_SELECT, MAIN_MENU,
    # Candidate
    C_RESUME_CHOICE, C_RESUME_UPLOAD, C_REVIEW_PARSED,
    C_NAME, C_GENDER, C_AGE, C_NATIONALITY, C_CITY,
    C_PHONE, C_LANGUAGES, C_EDUCATION, C_YEARS_EXP,
    C_INDUSTRY, C_POSITION, C_SALARY, C_LOCATIONS,
    C_AVAILABLE, C_EXTRAS, C_NOTES, C_REVIEW, C_CONFIRM,
    # Company
    B_COMPANY_NAME, B_INDUSTRY, B_ADDRESS, B_CONTACT_NAME,
    B_CONTACT_TITLE, B_PHONE, B_POSITION, B_HEADCOUNT,
    B_LOCATION, B_SALARY, B_HOURS, B_LANGUAGE, B_EXPERIENCE,
    B_BENEFITS, B_START_DATE, B_JD, B_SERVICE_FEE, B_UPLOAD, B_NOTES,
    B_REVIEW, B_CONFIRM,
    # Boss Show
    BS_COMPANY, BS_INDUSTRY, BS_CONTACT, BS_CONTACT_INFO,
    BS_TOPIC, BS_INTRO, BS_INTENT, BS_REVIEW, BS_CONFIRM,
) = range(43)
```

**Candidate flow — step count display**:
- If resume uploaded and parsed: steps 1/X only covers review + corrections → display "📝 {n} / 12" for each correction step
- If manual: steps 1–12 linear

---

## Gemini Integration (`services/gemini.py`)

### `parse_resume(file_bytes, mime_type, lang) → dict`

1. Send file bytes via `types.Part.from_bytes(...)`.
2. Call model with `prompts/candidate_parse.txt` (language-agnostic — always returns JSON).
3. Return parsed dict; on any exception return `{}`.

### `generate_candidate_summary(data: dict, lang: str) → dict`

Prompt (`prompts/candidate_summary.txt`) instructs Gemini to output summary and tags **in the language specified by `lang`**:

```
Generate the summary and tags in the following language: {lang_instruction}
Where lang_instruction maps: zh → "Simplified Chinese", en → "English", km → "Khmer (ភាសាខ្មែរ)"
```

Returns: `{ai_summary, ai_tags, ai_recommended_roles, ai_risk_notes}`

### `generate_company_summary(data: dict, lang: str) → dict`

Same pattern. Returns: `{ai_summary, ai_tags}`

---

## Google Sheets Schema

### Tab: `candidates`

| Col | Field | Notes |
|-----|-------|-------|
| A | record_id | `C-YYYYMMDD-XXXX` |
| B | submitted_at | ISO 8601 |
| C | lang | zh / en / km |
| D | status | 新提交 / 待联系 / 已联系 / 资料待补充 / 可推荐 / 已推荐 / 面试中 / 已入职 / 不合适 / 暂不找工作 |
| E | name | |
| F | gender | |
| G | age | integer |
| H | nationality | |
| I | current_city | |
| J | telegram_username | @handle |
| K | telegram_user_id | integer |
| L | phone_whatsapp | |
| M | languages | comma-separated |
| N | education | |
| O | years_experience | integer |
| P | industry_experience | |
| Q | desired_position | |
| R | desired_salary | |
| S | preferred_locations | |
| T | available_from | |
| U | cambodia_experience | Yes / No |
| V | needs_accommodation | Yes / No / Not specified |
| W | needs_visa_support | Yes / No / Not specified |
| X | resume_drive_link | |
| Y | attachment_drive_link | |
| Z | notes | |
| AA | ai_summary | |
| AB | ai_tags | |
| AC | ai_recommended_roles | |
| AD | ai_risk_notes | |
| AE | raw_json | minified JSON from Gemini parse |
| AF | internal_notes | HR editable |
| AG | assigned_hr | |
| AH | last_updated | |

### Tab: `companies`

| Col | Field | Notes |
|-----|-------|-------|
| A | record_id | `J-YYYYMMDD-XXXX` |
| B | submitted_at | |
| C | lang | |
| D | status | 新需求 / 待联系 / 已联系 / 待确认合作 / 招聘中 / 已推荐候选人 / 面试中 / 已入职 / 已收款 / 已关闭 |
| E | company_name | |
| F | industry | |
| G | company_address | |
| H | contact_name | |
| I | contact_title | |
| J | telegram_username | |
| K | telegram_user_id | |
| L | phone_whatsapp | |
| M | position_title | |
| N | headcount | |
| O | work_location | |
| P | salary_range | |
| Q | working_hours | |
| R | language_requirement | |
| S | experience_requirement | |
| T | provides_accommodation | Yes / No |
| U | provides_visa | Yes / No |
| V | start_date_requirement | |
| W | job_description | |
| X | accepts_service_fee_terms | Yes / No |
| Y | company_docs_drive_link | |
| Z | notes | |
| AA | ai_summary | |
| AB | ai_tags | |
| AC | raw_json | |
| AD | internal_notes | |
| AE | assigned_hr | |
| AF | last_updated | |

### Tab: `boss_show`

| Col | Field | Notes |
|-----|-------|-------|
| A | record_id | `B-YYYYMMDD-XXXX` |
| B | submitted_at | |
| C | lang | |
| D | status | 新申请 / 已联系 / 合作中 / 已完成 / 不合适 |
| E | company_name | |
| F | industry | |
| G | contact_name | |
| H | contact_info | |
| I | telegram_username | |
| J | interview_topic | |
| K | company_intro | |
| L | cooperation_intent | |
| M | notes | |
| N | internal_notes | |

---

## Internal Notification Format (`notifier.py`)

Notifications use `t("notify.*", lang="zh")` — internal group always receives Chinese regardless of user's language. The user's lang is appended as a metadata line.

**New Candidate**:
```
🆕 【新求职者】#C-20250528-0001

👤 张伟 | 中国 | 28岁
📍 金边
🗣 中文、英语
💼 客服、销售
💰 $800–$1200
📎 简历：[查看文件](https://drive.google.com/...)

🏷 中文客服 / 销售 / 金边 / 立即可入职
📝 候选人具有3年客服经验，中英双语流利，有意向在金边从事销售或客服类工作。

🌐 用户语言：中文
⚡️ 请 HR 跟进
```

**New Company**:
```
🆕 【新招聘需求】#J-20250528-0001

🏢 XX科技有限公司 | 互联网
👤 李总 (HR Manager)
📌 中文客服 × 3人
📍 金边 | 💰 $700–$900
🗣 中文流利
📅 到岗：2周内

🏷 中文客服 / 金边 / 急招
📝 招聘中文客服3人，要求中文流利，有客服经验优先，薪资$700-$900。

🌐 用户语言：中文
⚡️ 请 HR 联系企业
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `/cancel` at any state | Clear `user_data`, send `t("common.cancel_confirm")`, return `ConversationHandler.END` |
| `/lang` at any state | Clear conversation state, restart from language select |
| Conversation timeout (30 min inactivity) | Send `t("common.timeout_msg")`, end conversation |
| Gemini parse failure | Skip AI step, mark `ai_summary = "AI解析失败"`, continue flow |
| Sheets append failure | Retry once after 3s; on second failure write to `data/failed_submissions.jsonl`, notify user of success (don't expose backend errors) |
| Drive upload failure | Continue without link, set field to empty string, log warning |
| Invalid input type (e.g. text when expecting button) | Re-send same step message with hint: `t("common.or_type")` |

---

## Implementation Order

1. `config.py`, `.env.example`, `requirements.txt`
2. `locales/zh.json` + `en.json` + `km.json` with full key set; `services/i18n.py` with startup validation
3. `bot/keyboards.py` — all keyboard builder functions (lang-aware, no strings)
4. `bot/ui.py` — progress bar formatter, review card builder
5. `services/sheets.py` — append + seq ID generation (test with dummy data)
6. `services/drive.py` — upload + share link
7. `services/notifier.py` — formatted group alerts
8. `bot/handlers/start.py` — language select + main menu
9. `bot/handlers/candidate.py` — **full flow, no AI** (manual path only)
10. `bot/handlers/company.py` — **full flow, no AI**
11. `main.py` — register all handlers, run polling
12. ✅ **End-to-end test**: Bot → Sheets → Drive → Notify (all three languages)
13. `services/gemini.py` — parse + summary functions
14. Integrate Gemini into candidate flow (resume upload branch + summary generation)
15. Integrate Gemini into company flow (summary generation)
16. `bot/handlers/boss_show.py` + `bot/handlers/contact.py`
17. Error handling: timeout, retry, `/cancel`, `/lang`, failed_submissions fallback

---

## Requirements (`requirements.txt`)

```
python-telegram-bot[job-queue]==21.*
google-genai>=2.7
gspread>=6.0
google-api-python-client>=2.100
google-auth>=2.22
python-dotenv>=1.0
python-docx>=1.1
```
