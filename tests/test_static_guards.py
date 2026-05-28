import ast
from pathlib import Path
import unittest

from services.i18n import validate_locales
from services import sheets


ROOT = Path(__file__).resolve().parents[1]


class StaticGuardTests(unittest.TestCase):
    def test_all_locales_have_identical_keys(self):
        validate_locales()

    def test_all_python_files_compile(self):
        for path in ROOT.rglob("*.py"):
            if any(part in {".venv", "__pycache__"} for part in path.parts):
                continue
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")

    def test_conversation_callback_handlers_are_pattern_limited(self):
        tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        missing = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "CallbackQueryHandler":
                continue
            if not node.args:
                continue
            callback = node.args[0]
            if not isinstance(callback, ast.Attribute):
                continue
            if not isinstance(callback.value, ast.Name):
                continue
            if callback.value.id not in {"candidate", "company", "boss_show", "start", "contact"}:
                continue
            has_pattern = any(keyword.arg == "pattern" for keyword in node.keywords)
            if not has_pattern:
                missing.append(f"{callback.value.id}.{callback.attr}:{node.lineno}")

        self.assertEqual(missing, [])

    def test_sheet_header_initializes_only_empty_first_row(self):
        class FakeWorksheet:
            def __init__(self, first_row):
                self.first_row = first_row
                self.updates = []

            def row_values(self, row):
                self.assert_row = row
                return self.first_row

            def update(self, cell, values, value_input_option=None):
                self.updates.append((cell, values, value_input_option))

        empty = FakeWorksheet([])
        sheets._ensure_header(empty, "candidates")

        self.assertEqual(empty.updates[0][0], "A1")
        self.assertEqual(empty.updates[0][1][0][0], "记录ID")
        self.assertEqual(empty.updates[0][2], "USER_ENTERED")

        existing = FakeWorksheet(["记录ID"])
        sheets._ensure_header(existing, "candidates")

        self.assertEqual(existing.updates, [])


if __name__ == "__main__":
    unittest.main()
