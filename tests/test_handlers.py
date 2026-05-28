import asyncio
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_INTERNAL_GROUP_ID", "-1001234567890")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("GOOGLE_SHEET_ID", "test-sheet-id")
os.environ.setdefault("GOOGLE_DRIVE_FOLDER_ID", "test-drive-folder")

from bot.handlers import candidate, company, start
from bot.states import (
    B_EXPERIENCE,
    B_SALARY,
    C_EDUCATION,
    C_INDUSTRY,
    C_LOCATIONS,
    C_NAME,
    C_POSITION,
    C_REVIEW,
    C_RESUME_CHOICE,
    C_WORK_EXPERIENCE,
    MAIN_MENU,
)


class FakeMessage:
    def __init__(self, text="", document=None, photo=None):
        self.text = text
        self.document = document
        self.photo = photo or []
        self.replies = []

    async def reply_text(self, text, reply_markup=None):
        self.replies.append((text, reply_markup))


class FakeCallbackQuery:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()
        self.answered = False
        self.edits = []

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, text, reply_markup=None):
        self.edits.append((text, reply_markup))


class FakeUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query
        self.effective_user = type(
            "User",
            (),
            {"id": 123, "first_name": "Test", "last_name": "", "username": "tester"},
        )()


class FakeContext:
    def __init__(self):
        self.user_data = {"lang": "zh"}


class FakeTelegramFile:
    download_kwargs = None

    async def download_as_bytearray(self, **kwargs):
        self.download_kwargs = kwargs
        return bytearray(b"resume bytes")


class FakeDocument:
    file_name = "resume.pdf"
    mime_type = "application/pdf"
    last_file = None
    get_file_kwargs = None

    async def get_file(self, **kwargs):
        self.get_file_kwargs = kwargs
        self.last_file = FakeTelegramFile()
        return self.last_file


def run(coro):
    return asyncio.run(coro)


class CandidateHandlerTests(unittest.TestCase):
    def test_start_defaults_to_chinese_main_menu_with_language_row(self):
        ctx = FakeContext()
        ctx.user_data = {"lang": "en", "stale": True}
        update = FakeUpdate(message=FakeMessage())

        state = run(start.start(update, ctx))

        self.assertEqual(state, MAIN_MENU)
        self.assertEqual(ctx.user_data["lang"], "zh")
        text, markup = update.message.replies[0]
        self.assertIn("请选择服务", text)
        first_row = markup.inline_keyboard[0]
        self.assertEqual([button.callback_data for button in first_row], ["lang_zh", "lang_en", "lang_km"])

    def test_name_callback_does_not_require_message(self):
        ctx = FakeContext()
        update = FakeUpdate(callback_query=FakeCallbackQuery("menu_candidate"))

        state = run(candidate.name(update, ctx))

        self.assertEqual(state, C_NAME)
        self.assertEqual(ctx.user_data["candidate"], {})

    def test_name_back_callback_returns_resume_choice(self):
        ctx = FakeContext()
        update = FakeUpdate(callback_query=FakeCallbackQuery("back"))

        state = run(candidate.name(update, ctx))

        self.assertEqual(state, C_RESUME_CHOICE)

    def test_language_other_text_advances_to_education(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Italian"))

        state = run(candidate.languages(update, ctx))

        self.assertEqual(state, C_EDUCATION)
        self.assertEqual(ctx.user_data["candidate"]["languages"], {"Italian"})
        self.assertEqual(len(update.message.replies), 1)

    def test_industry_other_text_advances_to_work_experience(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Aviation"))

        state = run(candidate.industry(update, ctx))

        self.assertEqual(state, C_WORK_EXPERIENCE)
        self.assertEqual(ctx.user_data["candidate"]["industry"], {"Aviation"})

    def test_work_experience_text_advances_to_position(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("ABC Tech | Sales | 2022-2024 | Signed 18 clients."))

        state = run(candidate.work_experience(update, ctx))

        self.assertEqual(state, C_POSITION)
        self.assertIn("ABC Tech", ctx.user_data["candidate"]["work_experience"])

    def test_position_other_text_advances_to_salary(self):
        from bot.states import C_SALARY

        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Dispatcher"))

        state = run(candidate.position(update, ctx))

        self.assertEqual(state, C_SALARY)
        self.assertEqual(ctx.user_data["candidate"]["position"], {"Dispatcher"})

    def test_location_other_text_advances_to_available(self):
        from bot.states import C_AVAILABLE

        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Siem Reap"))

        state = run(candidate.locations(update, ctx))

        self.assertEqual(state, C_AVAILABLE)
        self.assertEqual(ctx.user_data["candidate"]["locations"], {"Siem Reap"})

    def test_resume_upload_empty_parse_still_opens_review(self):
        ctx = FakeContext()
        doc = FakeDocument()
        update = FakeUpdate(message=FakeMessage(document=doc))

        async def parse_empty(*args):
            return {
                "name": "",
                "gender": "",
                "age": "",
                "nationality": "",
                "current_city": "",
                "phone_whatsapp": "",
                "languages": [],
                "education": "",
                "years_experience": "",
                "industry_experience": [],
                "work_experience": "",
                "desired_position": [],
                "desired_salary": "",
                "preferred_locations": [],
                "available_from": "",
                "cambodia_experience": False,
                "needs_accommodation": False,
                "needs_visa_support": False,
                "notes": "",
            }

        with patch.object(candidate.drive, "upload_file", return_value="") as upload, \
                patch.object(candidate.gemini, "parse_resume", side_effect=parse_empty):
            state = run(candidate.resume_upload(update, ctx))

        self.assertEqual(state, C_REVIEW)
        self.assertEqual(doc.get_file_kwargs["read_timeout"], 60)
        self.assertEqual(doc.last_file.download_kwargs["read_timeout"], 60)
        uploaded_filename = upload.call_args.args[1]
        self.assertEqual(uploaded_filename, "123_Test_tester_resume.pdf")
        self.assertIn("raw_json", ctx.user_data["candidate"])
        markup = update.message.replies[-1][1]
        upload_row = markup.inline_keyboard[-2]
        self.assertEqual([button.callback_data for button in upload_row], ["upload_resume", "upload_attachment"])
        self.assertTrue(any("解析完成" in reply[0] for reply in update.message.replies))

    def test_review_attachment_upload_sets_attachment_link(self):
        ctx = FakeContext()
        ctx.user_data["candidate_upload_kind"] = "attachment"
        doc = FakeDocument()
        update = FakeUpdate(message=FakeMessage(document=doc))

        with patch.object(candidate.drive, "upload_file", return_value="https://drive.example/file") as upload:
            state = run(candidate.review_upload(update, ctx))

        self.assertEqual(state, C_REVIEW)
        self.assertEqual(ctx.user_data["candidate"]["attachment_link"], "https://drive.example/file")
        self.assertEqual(upload.call_args.args[1], "123_Test_tester_attachment.pdf")


class CompanyHandlerTests(unittest.TestCase):
    def test_location_other_text_advances_to_salary(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Sihanoukville"))

        state = run(company.location(update, ctx))

        self.assertEqual(state, B_SALARY)
        self.assertEqual(ctx.user_data["company"]["location"], "Sihanoukville")

    def test_language_other_text_advances_to_experience(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Thai"))

        state = run(company.language_req(update, ctx))

        self.assertEqual(state, B_EXPERIENCE)
        self.assertEqual(ctx.user_data["company"]["language_req"], "Thai")


if __name__ == "__main__":
    unittest.main()
