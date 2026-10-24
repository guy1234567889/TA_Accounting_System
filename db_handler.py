import os
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass

def _connect():
    """Connect to Google Drive using credentials from st.secrets or environment variables."""
    try:
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

        if "gcp_service_account" in st.secrets:
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=['https://www.googleapis.com/auth/drive']
            )
            service = build('drive', 'v3', credentials=creds)
            folder_id = st.secrets.get("drive", {}).get("folder_id", "")
            return service, folder_id

        raise DatabaseError("Missing Google Drive credentials.")

    except Exception as e:
        raise DatabaseError(f"Database connection error: {e}")

def is_mock():
    return st.secrets.get("drive", {}).get("use_mock", False) or os.getenv("USE_MOCK", "false").lower() == "true"

def get_all_clients(fresh=False):
    """Retrieve all clients from storage or mock data."""
    if is_mock():
        return []  # מחזיר רשימה ריקה במצב הדגמה להתחלה חלקית
    
    # כאן יבוא הלוגיקה המלאה לשליפה מהדרייב אם אינו במצב מוק
    return []

def normalize_id(id_str):
    """מנרמל תעודת זהות: מסיר תווים מיותרים ומשלים ל-9 ספרות עם אפסים מובילים."""
    if not id_str:
        return ""
    
    # המרה למחרוזת והסרת רווחים או מקפים
    cleaned = str(id_str).strip().replace("-", "").replace(" ", "")
    
    # אם מדובר במספר באורך של עד 9 ספרות, הוסף אפסים מובילים
    if cleaned.isdigit() and len(cleaned) <= 9:
        return cleaned.zfill(9)
        
    return cleaned

def is_valid_israeli_id(id_str):
    """בודק אם תעודת הזהות תקינה לפי אלגוריתם ספרת ביקורת."""
    if not id_str or not isinstance(id_str, str) or not id_str.isdigit() or len(id_str) != 9:
        return False
        
    total = 0
    for i in range(9):
        val = int(id_str[i]) * (1 if i % 2 == 0 else 2)
        total += val if val < 10 else (val % 10 + 1)
        
    return total % 10 == 0

def add_client(tz, name, phone, btype, stage):
    """מוסיף לקוח חדש למסד הנתונים."""
    if is_mock():
        return True
        
    # כאן נכניס בהמשך את הקוד שכותב את השורה בפועל ל-Google Sheets
    # בינתיים נחזיר אישור כדי למנוע קריסה ולאפשר לממשק להמשיך
    return True
