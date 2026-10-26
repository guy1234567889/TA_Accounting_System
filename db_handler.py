"""Google Sheets data layer shared by the admin app and the client portal."""
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
import streamlit as st
from google.oauth2.credentials import Credentials

import config as C
import storage
from mock_sheet import MockWorksheet

SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]


class DatabaseError(Exception):
    """Raised with a message that is safe to show to the user."""


class ValidationError(DatabaseError):
    """Invalid user input (ID, phone, name…). Caught wherever DatabaseError is caught."""


# ───────────────────────────── validation ─────────────────────────────
def is_valid_israeli_id(tz: str) -> bool:
    """Standard Israeli ID check-digit algorithm (exactly 9 digits)."""
    if not re.fullmatch(r"[0-9]{9}", tz or ""):
        return False
    total = 0
    for i, ch in enumerate(tz):
        n = int(ch) * (1 + i % 2)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def validate_id(raw: str) -> str:
    """Return a clean 9-digit ID or raise ValidationError. Leading zeros must be typed."""
    digits = re.sub(r"[\s\-]", "", raw or "")
    if not re.fullmatch(r"[0-9]{9}", digits):
        raise ValidationError("תעודת הזהות חייבת להכיל בדיוק 9 ספרות (כולל אפסים מובילים).")
    if not is_valid_israeli_id(digits):
        raise ValidationError("תעודת הזהות אינה תקינה (ספרת הביקורת שגויה). בדוק את המספר.")
    return digits


def validate_phone(raw: str) -> str:
    """Israeli mobile: 10 digits, valid 05X prefix. Accepts spaces, dashes and +972."""
    digits = re.sub(r"[\s\-().]", "", raw or "")
    if digits.startswith("+972"):
        digits = "0" + digits[4:]
    elif digits.startswith("972") and len(digits) == 12:
        digits = "0" + digits[3:]
    if not re.fullmatch(r"[0-9]{10}", digits):
        raise ValidationError("מספר הטלפון חייב להכיל 10 ספרות, למשל 0501234567.")
    if digits[:3] not in C.MOBILE_PREFIXES:
        raise ValidationError("קידומת הטלפון אינה חוקית. קידומות נתמכות: "
                              + ", ".join(C.MOBILE_PREFIXES) + ".")
    return digits


_NAME_WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['’׳״\"\-])+")


def validate_full_name(raw: str) -> str:
    """At least two words (first + last name), letters only (hyphen/geresh allowed)."""
    words = (raw or "").split()
    if len(words) < 2:
        raise ValidationError("יש להזין שם פרטי ושם משפחה (לפחות שתי מילים).")
    if not all(_NAME_WORD.fullmatch(w) for w in words):
        raise ValidationError("השם יכול להכיל אותיות בלבד (כל מילה לפחות שתי אותיות).")
    return " ".join(words)


def format_phone(digits: str) -> str:
    return f"{digits[:3]}-{digits[3:]}" if re.fullmatch(r"[0-9]{10}", digits or "") else digits


# ───────────────────────────── helpers ─────────────────────────────
def normalize_id(raw: str) -> str | None:
    """Lenient lookup form: digits only, left-padded to 9 (Sheets drops leading zeros)."""
    digits = re.sub(r"\D", "", raw or "")
    return digits.zfill(9) if 5 <= len(digits) <= 9 else None


def _split(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"[,;\n]", text or "") if p.strip()]


def _now() -> str:
    return datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d %H:%M")


def _canon(value: str) -> str:
    """Map legacy English values to the Hebrew ones."""
    return C.ALIASES.get(value, value)


def _parse_received(text: str) -> list[dict]:
    try:
        data = json.loads(text) if text else []
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


# ───────────────────────────── connection ─────────────────────────────
def is_mock() -> bool:
    """True when running in demo mode (local CSV instead of Google Sheets)."""
    if os.getenv("USE_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    try:
        sec = st.secrets
        return bool(sec.get("use_mock", False) or sec.get("drive", {}).get("use_mock", False))
    except Exception:                      # no secrets file at all
        return False


@st.cache_resource(show_spinner=False)
def _connect():
    """Open the worksheet once per server process, rename legacy English headers to Hebrew
    and add any missing columns. Returns (worksheet, headers)."""
    try:
        if is_mock():
            ws = MockWorksheet()
        else:
            d = st.secrets.get("drive", {})
            client_id = d.get("client_id") or os.getenv("CLIENT_ID")
            client_secret = d.get("client_secret") or os.getenv("CLIENT_SECRET")
            refresh_token = d.get("refresh_token") or os.getenv("REFRESH_TOKEN")
            sheet_id = d.get("spreadsheet_id") or os.getenv("SPREADSHEET_ID")
            if not (client_id and client_secret and refresh_token and sheet_id):
                raise DatabaseError("חסרים פרטי OAuth או spreadsheet_id ב-Secrets.")
            # No `scopes=` here on purpose: the refresh token already carries the scopes it was
            # granted, and asking for different ones makes Google answer "invalid_scope".
            creds = Credentials(token=None, refresh_token=refresh_token, client_id=client_id,
                                client_secret=client_secret,
                                token_uri="https://oauth2.googleapis.com/token")
            book = gspread.authorize(creds).open_by_key(sheet_id)
            tab = d.get("worksheet", "Clients")
            try:
                ws = book.worksheet(tab)
            except gspread.WorksheetNotFound:
                ws = book.add_worksheet(title=tab, rows=500, cols=len(C.COLUMNS))

        headers = ws.row_values(1)
        renamed = [C.HEADER_ALIASES.get(h, h) for h in headers]
        if renamed != headers:                 # one-time in-place migration to Hebrew headers
            ws.update(range_name="A1", values=[renamed], value_input_option="RAW")
            headers = renamed
        missing_cols = [c for c in C.COLUMNS if c not in headers]
        if missing_cols:                       # add any missing columns at the right edge
            ws.update(range_name=gspread.utils.rowcol_to_a1(1, len(headers) + 1),
                      values=[missing_cols], value_input_option="RAW")
            headers = headers + missing_cols
        return ws, headers
    except DatabaseError:
        raise
    except gspread.exceptions.SpreadsheetNotFound as e:
        raise DatabaseError("הגיליון לא נמצא – בדוק את המזהה ב-Secrets.") from e
    except Exception as e:
        raise DatabaseError(f"לא ניתן להתחבר למקור הנתונים: {e}") from e


@st.cache_data(ttl=15, show_spinner=False)
def _load_rows() -> list[dict]:
    ws, headers = _connect()
    try:
        values = ws.get_all_values()
    except (gspread.exceptions.APIError, OSError) as e:
        raise DatabaseError(f"שגיאת Google Sheets: {e}") from e
    rows = []
    for n, row in enumerate(values[1:], start=2):
        row = row + [""] * (len(headers) - len(row))
        rec = {h: row[i].strip() for i, h in enumerate(headers)}
        if rec.get(C.COL_ID):
            rec["_row"] = n
            rows.append(rec)
    return rows


def _to_client(rec: dict) -> dict:
    return {
        "id": normalize_id(rec[C.COL_ID]) or rec[C.COL_ID],
        "name": rec.get(C.COL_NAME, ""),
        "phone": rec.get(C.COL_PHONE, ""),
        "business_type": _canon(rec.get(C.COL_BTYPE, "")),
        "stage": _canon(rec.get(C.COL_STAGE, "")),
        "status": _canon(rec.get(C.COL_STATUS, "")) or C.WAITING,
        "missing": [_canon(d) for d in _split(rec.get(C.COL_MISSING, ""))],
        "received": [{**r, "doc": _canon(r.get("doc", ""))}
                     for r in _parse_received(rec.get(C.COL_RECEIVED, ""))],
        "updated": rec.get(C.COL_UPDATED, ""),
        "_row": rec["_row"],
    }


# ───────────────────────────── reads ─────────────────────────────
def get_all_clients(fresh: bool = False) -> list[dict]:
    if fresh:
        _load_rows.clear()
    return [_to_client(r) for r in _load_rows()]


def get_client(raw_id: str, fresh: bool = False) -> dict | None:
    """Return the client dict, or None if the ID is malformed or unknown."""
    wanted = normalize_id(raw_id)
    if not wanted:
        return None
    return next((c for c in get_all_clients(fresh) if c["id"] == wanted), None)


# ───────────────────────────── writes ─────────────────────────────
def _update(client: dict, fields: dict) -> None:
    """Write several cells of one row in a single API call."""
    ws, headers = _connect()
    fields = {**fields, C.COL_UPDATED: _now()}
    batch = [{"range": gspread.utils.rowcol_to_a1(client["_row"], headers.index(col) + 1),
              "values": [[val]]} for col, val in fields.items()]
    try:
        ws.batch_update(batch, value_input_option="RAW")
    except (gspread.exceptions.APIError, OSError) as e:
        raise DatabaseError(f"לא ניתן לשמור בגיליון: {e}") from e
    _load_rows.clear()


def _must_get(client_id: str) -> dict:
    c = get_client(client_id, fresh=True)       # always re-read before writing
    if not c:
        raise DatabaseError("הלקוח לא נמצא.")
    return c


def add_client(tz: str, name: str, phone: str, business_type: str, stage: str) -> dict:
    tz, name, phone = validate_id(tz), validate_full_name(name), validate_phone(phone)
    if business_type not in C.BUSINESS_TYPES or stage not in C.STAGES:
        raise ValidationError("יש לבחור סוג עסק ושלב מהרשימה.")
    if get_client(tz, fresh=True):
        raise DatabaseError("כבר קיים לקוח עם תעודת זהות זו.")
    ws, headers = _connect()
    values = {C.COL_ID: tz, C.COL_NAME: name, C.COL_PHONE: phone,
              C.COL_BTYPE: business_type, C.COL_STAGE: stage, C.COL_STATUS: C.WAITING,
              C.COL_MISSING: ", ".join(C.STAGE_DOCUMENTS.get(stage, [])),
              C.COL_RECEIVED: "[]", C.COL_UPDATED: _now()}
    try:
        ws.append_row([values.get(h, "") for h in headers], value_input_option="RAW")
    except (gspread.exceptions.APIError, OSError) as e:
        raise DatabaseError(f"לא ניתן לשמור בגיליון: {e}") from e
    _load_rows.clear()
    return _must_get(tz)


def update_details(client_id: str, name: str, phone: str, business_type: str) -> None:
    name, phone = validate_full_name(name), validate_phone(phone)
    _update(_must_get(client_id),
            {C.COL_NAME: name, C.COL_PHONE: phone, C.COL_BTYPE: business_type})


def set_status(client_id: str, status: str) -> None:
    if status not in C.STATUSES:
        raise DatabaseError("סטטוס לא מוכר.")
    _update(_must_get(client_id), {C.COL_STATUS: status})


def set_stage(client_id: str, stage: str, reset_documents: bool) -> None:
    """Move the client to another stage; optionally load that stage's standard documents."""
    c = _must_get(client_id)
    fields = {C.COL_STAGE: stage}
    if reset_documents:
        have = {r["doc"] for r in c["received"]}
        needed = [d for d in C.STAGE_DOCUMENTS.get(stage, []) if d not in have]
        fields[C.COL_MISSING] = ", ".join(needed)
        fields[C.COL_STATUS] = C.WAITING if needed else C.REVIEW
    _update(c, fields)


def request_document(client_id: str, doc: str) -> None:
    doc = re.sub(r"[,;\n]", " ", doc).strip()
    if not doc:
        raise DatabaseError("יש להזין שם מסמך.")
    c = _must_get(client_id)
    if doc.lower() in (m.lower() for m in c["missing"]):
        raise DatabaseError("המסמך הזה כבר התבקש.")
    _update(c, {C.COL_MISSING: ", ".join(c["missing"] + [doc]), C.COL_STATUS: C.WAITING})


def register_upload(client_id: str, doc: str, files: list[tuple[str, bytes]]) -> None:
    """Client side: store the files, move doc from Missing → Received, update the status."""
    c = _must_get(client_id)
    if doc not in c["missing"]:
        raise DatabaseError("המסמך הזה כבר אינו נדרש.")
    if not files:
        raise DatabaseError("יש להוסיף תמונה או קובץ קודם.")
    saved = [storage.save_file(c["id"], doc, name, data) for name, data in files]
    received = c["received"] + [{"doc": doc, "files": saved, "time": _now(), "approved": False}]
    missing = [m for m in c["missing"] if m != doc]
    fields = {C.COL_RECEIVED: json.dumps(received, ensure_ascii=False),
              C.COL_MISSING: ", ".join(missing)}
    if not missing and c["status"] != C.DONE:
        fields[C.COL_STATUS] = C.REVIEW          # everything arrived → accountant's turn
    _update(c, fields)


def attach_office_files(client_id: str, doc: str, files: list[tuple[str, bytes]],
                        approve: bool = True) -> None:
    """Accountant side: attach files to a client's record (marked source='office')."""
    doc = re.sub(r"[,;\n]", " ", doc or "").strip()
    if not doc:
        raise DatabaseError("יש לבחור מסמך או להזין את שמו.")
    if not files:
        raise DatabaseError("יש לבחור קובץ לצירוף.")
    c = _must_get(client_id)
    saved = [storage.save_file(c["id"], doc, name, data) for name, data in files]
    received = c["received"] + [{"doc": doc, "files": saved, "time": _now(),
                                 "approved": approve, "source": "office"}]
    missing = [m for m in c["missing"] if m != doc]
    fields = {C.COL_RECEIVED: json.dumps(received, ensure_ascii=False),
              C.COL_MISSING: ", ".join(missing)}
    if not missing and c["status"] == C.WAITING:
        fields[C.COL_STATUS] = C.REVIEW
    _update(c, fields)


def set_document_approval(client_id: str, doc: str, approved: bool) -> None:
    c = _must_get(client_id)
    received = c["received"]
    for rec in received:
        if rec["doc"] == doc:
            rec["approved"] = approved
    _update(c, {C.COL_RECEIVED: json.dumps(received, ensure_ascii=False)})


def reject_document(client_id: str, doc: str) -> None:
    """Send a document back: it returns to Missing and the status turns red.
    Files stay in storage for the audit trail."""
    c = _must_get(client_id)
    received = [r for r in c["received"] if r["doc"] != doc]
    missing = c["missing"] if doc in c["missing"] else c["missing"] + [doc]
    _update(c, {C.COL_RECEIVED: json.dumps(received, ensure_ascii=False),
                C.COL_MISSING: ", ".join(missing), C.COL_STATUS: C.WAITING})
