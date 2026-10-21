"""File storage. Local folder for now – swap the bodies of save_file/read_file for S3, GCS or
Drive later without touching the apps."""
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
MAX_BYTES = 15 * 1024 * 1024
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_EXT = IMAGE_EXT | {".pdf", ".heic"}


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
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower() or "doc"


def save_file(client_id: str, doc_name: str, filename: str, data: bytes) -> str:
    """Validate and store a file. Returns a path relative to BASE_DIR. Raises ValueError."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"'{filename}': סוג קובץ לא נתמך. יש להעלות JPG, PNG, PDF, HEIC או WEBP.")
    if not data:
        raise ValueError(f"הקובץ '{filename}' ריק.")
    if len(data) > MAX_BYTES:
        raise ValueError(f"הקובץ '{filename}' גדול מ-{MAX_BYTES // 1024 // 1024} MB.")
    if not _looks_valid(ext, data):
        raise ValueError(f"הקובץ '{filename}' אינו קובץ {ext[1:].upper()} תקין.")

    folder = BASE_DIR / re.sub(r"\D", "", client_id)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = folder / f"{_slug(doc_name)}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
    target.write_bytes(data)
    return str(target.relative_to(BASE_DIR))


def read_file(rel_path: str) -> bytes | None:
    """Read a stored file; refuses anything outside BASE_DIR (path-traversal guard)."""
    target = (BASE_DIR / rel_path).resolve()
    if not target.is_relative_to(BASE_DIR) or not target.is_file():
        return None
    return target.read_bytes()
