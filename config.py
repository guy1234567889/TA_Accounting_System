"""Shared constants: sheet columns, statuses, stages and the documents each stage needs."""

# ---- Google Sheet columns (row 1). The first 7 are yours; the last 2 are added automatically.
COL_ID = "ID (T.Z)"
COL_NAME = "Full Name"
COL_PHONE = "Phone"
COL_BTYPE = "Business Type"
COL_STAGE = "Current Stage"
COL_STATUS = "Global Status"
COL_MISSING = "Missing Documents"      # comma-separated list
COL_RECEIVED = "Received Documents"    # JSON list (file paths + approval flag)
COL_UPDATED = "Last Update"
COLUMNS = [COL_ID, COL_NAME, COL_PHONE, COL_BTYPE, COL_STAGE, COL_STATUS,
           COL_MISSING, COL_RECEIVED, COL_UPDATED]

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
