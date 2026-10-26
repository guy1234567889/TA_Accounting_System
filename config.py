"""Shared constants: sheet columns, statuses, stages and the documents each stage needs."""

# ---- Google Sheet columns (row 1). The first 7 are yours; the last 2 are added automatically.
COL_ID = "ת״ז"
COL_NAME = "שם מלא"
COL_PHONE = "טלפון"
COL_BTYPE = "סוג עסק"
COL_STAGE = "שלב נוכחי"
COL_STATUS = "סטטוס כללי"
COL_MISSING = "מסמכים חסרים"      # comma-separated list
COL_RECEIVED = "מסמכים שהתקבלו"    # JSON list (file paths + approval flag)
COL_UPDATED = "עדכון אחרון"
COL_FINALIZED = "אישור סופי"          # timestamp of the office's final sign-off
COLUMNS = [COL_ID, COL_NAME, COL_PHONE, COL_BTYPE, COL_STAGE, COL_STATUS,
           COL_MISSING, COL_RECEIVED, COL_UPDATED, COL_FINALIZED]

# ---- Global status (traffic light)
WAITING, REVIEW, DONE = "ממתין למסמכים", "בבדיקה", "הושלם"
STATUSES = [WAITING, REVIEW, DONE]
STATUS_STYLE = {   # (background, text, emoji, streamlit colour name)
    WAITING: ("#fde4e1", "#7a1f16", "🔴", "red"),
    REVIEW:  ("#fff3c4", "#6b5200", "🟡", "orange"),
    DONE:    ("#dcf3e1", "#14532d", "🟢", "green"),
}

BUSINESS_TYPES = ["עוסק פטור", "עוסק מורשה"]

# ---- Stages and the documents each one requires
STAGES = ["לקוח חדש", "דוח שנתי", "הצהרת הון"]
STAGE_DOCUMENTS = {
    "לקוח חדש":   ["צילום תעודת זהות", "צילום שיק מבוטל"],
    "דוח שנתי":   ["טופס 106", "טופס 867", "קבלות"],
    "הצהרת הון":  ["צילום תעודת זהות", "טופס 867", "דפי חשבון בנק", "קבלות"],
}

# English values from older sheets -> Hebrew (applied on read, so existing data keeps working)
ALIASES = {
    "Waiting for docs": WAITING, "In Review": REVIEW, "Done": DONE,
    "Exempt": BUSINESS_TYPES[0], "Authorized": BUSINESS_TYPES[1],
    "New Client": STAGES[0], "Annual Report": STAGES[1], "Capital Statement": STAGES[2],
    "ID copy": "צילום תעודת זהות", "Bank check copy": "צילום שיק מבוטל",
    "Form 106": "טופס 106", "Form 867": "טופס 867", "Receipts": "קבלות",
    "Bank statements": "דפי חשבון בנק",
}

# Legacy English sheet headers -> Hebrew. Applied once on connect (the header row is renamed in place,
# so existing data stays attached to its columns).
HEADER_ALIASES = {
    "ID (T.Z)": COL_ID, "Full Name": COL_NAME, "Phone": COL_PHONE, "Business Type": COL_BTYPE,
    "Current Stage": COL_STAGE, "Global Status": COL_STATUS, "Missing Documents": COL_MISSING,
    "Received Documents": COL_RECEIVED, "Last Update": COL_UPDATED,
}

# Israeli mobile prefixes accepted by phone validation (edit if a new carrier prefix appears)
MOBILE_PREFIXES = ("050", "051", "052", "053", "054", "055", "056", "058", "059")

# ---- Branding (shown in the banner of both apps)
FIRM_NAME = "אריק טרבלסי - רואה חשבון"      # replace with your firm's name
FIRM_PHONE = "0528858530"                     # optional, e.g. "09-1234567" – shown to clients for questions
