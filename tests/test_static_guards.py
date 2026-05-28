import ast
from pathlib import Path
import unittest

from services.i18n import validate_locales


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


if __name__ == "__main__":
    unittest.main()
