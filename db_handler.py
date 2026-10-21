import os
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def _connect():
    """Connect to Google Drive using credentials from st.secrets or environment variables."""
    try:
        # Check if secrets contains direct OAuth tokens
        drive_secrets = st.secrets.get("drive", {})
        client_id = drive_secrets.get("client_id") or os.getenv("CLIENT_ID")
        client_secret = drive_secrets.get("client_secret") or os.getenv("CLIENT_SECRET")
        refresh_token = drive_secrets.get("refresh_token") or os.getenv("REFRESH_TOKEN")

        if client_id and client_secret and refresh_token:
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret,
                token_uri="https://oauth2.googleapis.com/token"
            )
            service = build('drive', 'v3', credentials=creds)
            folder_id = drive_secrets.get("folder_id") or os.getenv("FOLDER_ID", "")
            return service, folder_id

        # Fallback to standard service account if configured
        if "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=creds)
            folder_id = st.secrets.get("drive", {}).get("folder_id", "")
            return service, folder_id

        raise ValueError("Missing Google Drive credentials in secrets.toml (requires client_id, client_secret, and refresh_token).")

    except Exception as e:
        raise RuntimeError(f"Database connection error: {e}")
        def is_mock():
    """Return True if mock mode is enabled in secrets or environment."""
    return st.secrets.get("drive", {}).get("use_mock", False) or os.getenv("USE_MOCK", "false").lower() == "true"
