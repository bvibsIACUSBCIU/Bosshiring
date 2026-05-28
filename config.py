"""
Configuration module — loads all environment variables at import time.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_INTERNAL_GROUP_ID: int = int(os.environ["TELEGRAM_INTERNAL_GROUP_ID"])

# Gemini AI
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

# Google Service Account
GOOGLE_SERVICE_ACCOUNT_JSON: str = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json"
)

# Google Sheets
GOOGLE_SHEET_ID: str = os.environ["GOOGLE_SHEET_ID"]

# Google Drive
GOOGLE_DRIVE_FOLDER_ID: str = os.environ["GOOGLE_DRIVE_FOLDER_ID"]

# Conversation timeout (seconds)
CONVERSATION_TIMEOUT: int = 30 * 60  # 30 minutes
