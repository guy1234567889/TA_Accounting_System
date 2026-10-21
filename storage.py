"""File storage for client documents.

Backends (chosen automatically):
  • Google Drive – when secrets contain a [drive] section with folder_id. Files go to
    <root folder>/<client ID>/<file>. Used on Streamlit Community Cloud, where the local disk
    is temporary and not shared between the admin and client apps.
  • Local folder – otherwise (development / demo).
Stored references: "gdrive:<fileId>/<name>" for Drive, "<clientId>/<name>" for local files."""
import io
import logging
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

log = logging.getLogger(__name__)

BASE_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
MAX_BYTES = 15 * 1024 * 1024
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXT = IMAGE_EXT | {".pdf", ".heic"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".pdf": "application/pdf", ".heic": "image/heic"}

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER_MIME = "application/vnd.google-apps.folder"


# ───────────────────────────── validation ─────────────────────────────
def _looks_valid(ext: str, data: bytes) -> bool:
    """Cheap magic-byte check so a renamed .exe can't be stored as a 'photo'."""
    if ext in (".jpg", ".jpeg"):
        return data.startswith(b"\xff\xd8")
    if ext == ".png":
        return data.startswith(b"\x89PNG")
    if ext == ".pdf":
        return data.startswith(b"%PDF")
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext == ".heic":
        return data[4:8] == b"ftyp"
    return False


def _slug(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text).strip("_").lower() or "doc"


# ───────────────────────────── Google Drive ─────────────────────────────
def _drive_cfg() -> dict | None:
    try:
        cfg = dict(st.secrets["drive"])
        return cfg if cfg.get("folder_id") else None
    except Exception:                        # no secrets / no [drive] section → local disk
        return None


def drive_enabled() -> bool:
    return _drive_cfg() is not None


@st.cache_resource(show_spinner=False)
def _creds():
    """Personal-Drive mode (OAuth refresh token) if configured, else the service account."""
    cfg = _drive_cfg()
    if cfg.get("refresh_token"):
        from google.oauth2.credentials import Credentials
        return Credentials(None, refresh_token=cfg["refresh_token"], client_id=cfg["client_id"],
                           client_secret=cfg["client_secret"], scopes=[DRIVE_SCOPE],
                           token_uri="https://oauth2.googleapis.com/token")
    from google.oauth2.service_account import Credentials
    return Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),
                                                 scopes=[DRIVE_SCOPE])


def _service():
    """A fresh API client per call (googleapiclient objects are not thread-safe)."""
    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=_creds(), cache_discovery=False)


_folder_ids: dict[str, str] = {}
_folder_lock = threading.Lock()


def _client_folder(svc, root: str, cid: str) -> str:
    """Find or create the per-client subfolder (cid is digits only, so the query is safe)."""
    with _folder_lock:
        if cid in _folder_ids:
            return _folder_ids[cid]
        q = (f"name='{cid}' and '{root}' in parents and mimeType='{FOLDER_MIME}' "
             "and trashed=false")
        found = svc.files().list(q=q, fields="files(id)", pageSize=1, supportsAllDrives=True,
                                 includeItemsFromAllDrives=True).execute().get("files", [])
        fid = found[0]["id"] if found else svc.files().create(
            body={"name": cid, "mimeType": FOLDER_MIME, "parents": [root]},
            fields="id", supportsAllDrives=True).execute()["id"]
        _folder_ids[cid] = fid
        return fid


def _drive_upload(cfg: dict, cid: str, name: str, ext: str, data: bytes) -> str:
    from googleapiclient.http import MediaIoBaseUpload
    svc = _service()
    folder = _client_folder(svc, cfg["folder_id"], cid)
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=MIME[ext], resumable=False)
    f = svc.files().create(body={"name": name, "parents": [folder]}, media_body=media,
                           fields="id", supportsAllDrives=True).execute()
    return f"gdrive:{f['id']}/{name}"


def _drive_download(rel_path: str) -> bytes | None:
    from googleapiclient.http import MediaIoBaseDownload
    file_id = rel_path.split(":", 1)[1].split("/", 1)[0]
    if not re.fullmatch(r"[\w-]{10,}", file_id):
        return None
    try:
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, _service().files().get_media(fileId=file_id,
                                                                    supportsAllDrives=True))
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()
    except Exception:
        log.exception("Drive download failed for %s", file_id)
        return None


def check_backend() -> tuple[bool, str]:
    """Health check for the admin sidebar: create and delete a tiny file in the root folder."""
    cfg = _drive_cfg()
    if not cfg:
        return False, "Google Drive לא הוגדר (חסר [drive] ב-secrets) – הקבצים נשמרים בדיסק מקומי."
    try:
        from googleapiclient.http import MediaIoBaseUpload
        svc = _service()
        f = svc.files().create(
            body={"name": "_healthcheck.txt", "parents": [cfg["folder_id"]]},
            media_body=MediaIoBaseUpload(io.BytesIO(b"ok"), mimetype="text/plain"),
            fields="id", supportsAllDrives=True).execute()
        svc.files().delete(fileId=f["id"], supportsAllDrives=True).execute()
        return True, "החיבור ל-Google Drive תקין – נוצר ונמחק קובץ בדיקה."
    except Exception as e:
        text = str(e)
        if "quota" in text.lower():
            return False, ("לחשבון השירות אין מכסת אחסון ב-Drive אישי. יש להשתמש בכונן משותף "
                           "(Google Workspace) או במצב OAuth עם refresh_token. פרטים: " + text[:200])
        return False, f"שגיאה בחיבור ל-Drive: {text[:300]}"


# ───────────────────────────── public API ─────────────────────────────
def save_file(client_id: str, doc_name: str, filename: str, data: bytes) -> str:
    """Validate and store a file. Returns a reference string. Raises ValueError."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"'{filename}': סוג קובץ לא נתמך. יש להעלות JPG, PNG, PDF, HEIC או WEBP.")
    if not data:
        raise ValueError(f"הקובץ '{filename}' ריק.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"הקובץ '{filename}' גדול מ-{MAX_BYTES // 1024 // 1024} MB.")
    if not _looks_valid(ext, data):
        raise ValueError(f"הקובץ '{filename}' אינו קובץ {ext[1:].upper()} תקין.")

    cid = re.sub(r"\D", "", client_id)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{_slug(doc_name)}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"

    cfg = _drive_cfg()
    if cfg:
        try:
            return _drive_upload(cfg, cid, name, ext, data)
        except Exception as e:               # details go to the server log, not to the client
            log.exception("Drive upload failed")
            raise ValueError("לא ניתן לשמור את הקובץ כרגע. נסה שוב בעוד רגע.") from e

    folder = BASE_DIR / cid                  # local disk (development / demo)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)
    return f"{cid}/{name}"


def read_file(rel_path: str) -> bytes | None:
    """Read a stored file by its reference; None if missing or invalid."""
    if rel_path.startswith("gdrive:"):
        return _drive_download(rel_path) if _drive_cfg() else None
    target = (BASE_DIR / rel_path).resolve()  # local: path-traversal guard
    if not target.is_relative_to(BASE_DIR) or not target.is_file():
        return None
    return target.read_bytes()
