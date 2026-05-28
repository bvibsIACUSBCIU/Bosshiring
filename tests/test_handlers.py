import asyncio
import os
import unittest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_INTERNAL_GROUP_ID", "-1001234567890")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("GOOGLE_SHEET_ID", "test-sheet-id")
os.environ.setdefault("GOOGLE_DRIVE_FOLDER_ID", "test-drive-folder")

from bot.handlers import candidate, company
from bot.states import (
    B_EXPERIENCE,
    B_SALARY,
    C_EDUCATION,
    C_INDUSTRY,
    C_LOCATIONS,
    C_NAME,
    C_POSITION,
    C_RESUME_CHOICE,
)


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
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


class FakeContext:
    def __init__(self):
        self.user_data = {"lang": "zh"}


def run(coro):
    return asyncio.run(coro)


class CandidateHandlerTests(unittest.TestCase):
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

    def test_industry_other_text_advances_to_position(self):
        ctx = FakeContext()
        update = FakeUpdate(message=FakeMessage("Aviation"))

        state = run(candidate.industry(update, ctx))

        self.assertEqual(state, C_POSITION)
        self.assertEqual(ctx.user_data["candidate"]["industry"], {"Aviation"})

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
