"""
================================================================================
Direct Google Drive Cloud Uploader (gdrive_direct_uploader.py)
================================================================================
Uploads Excel rollups directly to Google Drive folder using the Google Drive API.
Target Folder ID: 1oyYn-Mzvcxno8DAgNoghPdOFXA4pe1R6
================================================================================
"""

import os
import sys
from typing import Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GDRIVE_API_AVAILABLE = True
except ImportError:
    GDRIVE_API_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
DEFAULT_FOLDER_ID = "1oyYn-Mzvcxno8DAgNoghPdOFXA4pe1R6"


def get_drive_service():
    """Authenticates and returns a Google Drive API service instance."""
    creds = None
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
    client_secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json")

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(client_secrets_path):
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

    if creds:
        return build('drive', 'v3', credentials=creds)
    return None


def upload_to_google_drive(
    file_path: str,
    folder_id: Optional[str] = None
) -> Optional[str]:
    """
    Directly uploads a file to the target Google Drive folder via API.
    Returns the webViewLink of the uploaded file if successful.
    """
    if not GDRIVE_API_AVAILABLE:
        print("[Google Drive API] Client libraries not installed.")
        return None

    target_folder = folder_id or os.getenv("GDRIVE_FOLDER_ID", DEFAULT_FOLDER_ID)
    service = get_drive_service()

    if not service:
        # If API credentials are not configured yet, notify cleanly
        print(f"[Google Drive Sync] File prepared for Google Drive: {os.path.basename(file_path)}")
        print(f"                     Target Cloud Folder: https://drive.google.com/drive/folders/{target_folder}")
        return None

    try:
        filename = os.path.basename(file_path)
        file_metadata = {
            'name': filename,
            'parents': [target_folder]
        }
        media = MediaFileUpload(
            file_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            resumable=True
        )

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        web_link = uploaded_file.get('webViewLink')
        print(f"[Google Drive API] SUCCESS: Uploaded to cloud folder!")
        print(f"                   File Link: {web_link}")
        return web_link
    except Exception as e:
        print(f"[Google Drive API Error]: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        upload_to_google_drive(sys.argv[1])
    else:
        sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deliverables", "daily_rollups", "daily_rollup_2026-09-03_141437.xlsx")
        if os.path.exists(sample_path):
            upload_to_google_drive(sample_path)
        else:
            print(f"No sample file found at {sample_path}")
