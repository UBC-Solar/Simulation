import os.path
from pathlib import Path

import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io


SCOPES = ['https://www.googleapis.com/auth/drive.file']
EVOLUTION_ROOT_ID = "1L7mqA3UHsQD4FWVdkqDEcS6TPej6h9Pq"
AUTH_FILE = "token.env"
Client = googleapiclient.discovery.Resource


class Connect:
    def __init__(self):
        self.credentials = authenticate()
        self.service = get_service(self.credentials)


def authenticate() -> Credentials:
    if os.path.exists(AUTH_FILE):
        return Credentials.from_authorized_user_file(AUTH_FILE, SCOPES)
    else:
        raise FileNotFoundError("Cannot find Google Drive API token!")


def get_service(credentials: Credentials) -> Client:
    return build("drive", "v3", credentials=credentials)


if __name__ == "__main__":
    creds: Credentials = authenticate()
    service: Client = get_service(creds)
