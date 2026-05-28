#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-test-token}"
export TELEGRAM_INTERNAL_GROUP_ID="${TELEGRAM_INTERNAL_GROUP_ID:--1001234567890}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-test-gemini-key}"
export GOOGLE_SHEET_ID="${GOOGLE_SHEET_ID:-test-sheet-id}"
export GOOGLE_DRIVE_FOLDER_ID="${GOOGLE_DRIVE_FOLDER_ID:-test-drive-folder}"

PYTHON="${PYTHON:-.venv/bin/python}"

"$PYTHON" -m compileall -q \
  main.py bot services models scripts tests
"$PYTHON" -m unittest discover -s tests -v
