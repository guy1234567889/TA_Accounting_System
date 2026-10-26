import os
import streamlit as st
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class DatabaseError(Exception):
    pass

def _get_credentials():
    drive_secrets = st.secrets.get("drive", {})
    client_id = drive_secrets.get("client_id") or os.getenv("CLIENT_ID")
    client_secret = drive_secrets.get("client_secret") or os.getenv("CLIENT_SECRET")
    refresh_token = drive_secrets.get("refresh_token") or os.getenv("REFRESH_TOKEN")

    if client_id and client_secret and refresh_token:
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token"
        )
    
    raise DatabaseError("Missing Google Drive/Sheets credentials.")

def _connect():
    try:
        creds = _get_credentials()
        service = build('drive', 'v3', credentials=creds)
        folder_id = st.secrets.get("drive", {}).get("folder_id", "") or os.getenv("FOLDER_ID", "")
        return service, folder_id
    except Exception as e:
        raise DatabaseError(f"Database connection error: {e}")

def _get_sheets_service():
    try:
        creds = _get_credentials()
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        raise DatabaseError(f"Sheets connection error: {e}")

def is_mock():
    return st.secrets.get("drive", {}).get("use_mock", False)

def get_all_clients(fresh=False):
    if is_mock():
        return []
        
    try:
        service = _get_sheets_service()
        sheet_id = st.secrets.get("drive", {}).get("spreadsheet_id", "")
        if not sheet_id:
            return []
            
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="A:E"
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            return []
            
        clients = []
        # מדלגים על השורה הראשונה אם היא שורת כותרות
        start_idx = 1 if rows[0] and "תעודת זהות" in rows[0][0] else 0
        
        for row in rows[start_idx:]:
            # השלמת עמודות חסרות למקרה של שורה קצרה
            row += [""] * (5 - len(row))
            clients.append({
                "tz": row[0],
                "name": row[1],
                "phone": row[2],
                "btype": row[3],
                "stage": row[4]
            })
        return clients
    except Exception as e:
        print(f"Error fetching clients: {e}")
        return []

def normalize_id(id_str):
    if not id_str:
        return ""
    cleaned = str(id_str).strip().replace("-", "").replace(" ", "")
    if cleaned.isdigit() and len(cleaned) <= 9:
        return cleaned.zfill(9)
    return cleaned

def is_valid_israeli_id(id_str):
    if not id_str or not isinstance(id_str, str) or not id_str.isdigit() or len(id_str) != 9:
        return False
    total = 0
    for i in range(9):
        val = int(id_str[i]) * (1 if i % 2 == 0 else 2)
        total += val if val < 10 else (val % 10 + 1)
    return total % 10 == 0

def add_client(tz, name, phone, btype, stage):
    if is_mock():
        return True
        
    try:
        service = _get_sheets_service()
        sheet_id = st.secrets.get("drive", {}).get("spreadsheet_id", "")
        
        # בניית השורה שתיכתב לגיליון
        values = [[str(tz), str(name), str(phone), str(btype), str(stage)]]
        body = {'values': values}
        
        # כתיבה לגיליון
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="A:E",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        return True
    except Exception as e:
        raise DatabaseError(f"Error saving to Google Sheets: {e}")
