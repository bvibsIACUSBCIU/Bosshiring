"""
services/drive.py — Upload files to Google Drive and return share links.
"""
import asyncio
import io
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

import config

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive"]
_service = None


def _get_service():
    global _service
    if _service is None:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=_SCOPES
        )
        _service = build("drive", "v3", credentials=creds)
    return _service


def _upload_file_sync(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> str:
    """Synchronous implementation of file upload."""
    try:
        service = _get_service()
        file_metadata = {
            "name": filename,
            "parents": [config.GOOGLE_DRIVE_FOLDER_ID],
        }
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes), mimetype=mime_type, resumable=True
        )
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )

        # Make it readable by anyone with the link
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = file.get("webViewLink", "")
        logger.info(f"Uploaded {filename} → {link}")
        return link

    except Exception as e:
        logger.error(f"Drive upload failed for {filename}: {e}")
        return ""


async def upload_file(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> str:
    """Upload file to Drive folder and return a shareable link.
    Returns empty string on failure (does not raise).
    """
    return await asyncio.to_thread(_upload_file_sync, file_bytes, filename, mime_type)
