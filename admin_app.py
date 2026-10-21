"""Accountant dashboard – run with:  streamlit run admin_app.py"""
import hmac
import os
from pathlib import Path

import pandas as pd
import streamlit as st

import config as C
import db_handler as db
import storage
import ui

st.set_page_config(page_title="ניהול לקוחות", page_icon="🗂️", layout="wide")
ui.apply_rtl()


# ───────────────────────────── auth ─────────────────────────────
def require_login() -> None:
    """Password gate. Fails closed: with no password configured the app stays locked."""
    if st.session_state.get("admin_ok"):
        return
    try:
        expected = st.secrets["admin"]["password"]
    except Exception:
        expected = os.getenv("ADMIN_PASSWORD", "")
    if not expected:
        st.error("לא הוגדרה סיסמת מנהל. הוסף password תחת [admin] ב-secrets.toml "
                 "(או הגדר משתנה סביבה ADMIN_PASSWORD).")
        st.stop()
    st.title("כניסת רואה החשבון")
    with st.form("login"):
        pwd = st.text_input("סיסמה", type="password")
        if st.form_submit_button("כניסה", type="primary"):
            if hmac.compare_digest(pwd.encode(), expected.encode()):
                st.session_state["admin_ok"] = True
                st.rerun()
            st.error("סיסמה שגויה.")
    st.stop()


def flash(msg: str) -> None:
    st.session_state["flash"] = msg


def run(fn, *args, ok: str = "נשמר") -> None:
    """Call a db function, show errors inline, otherwise confirm and refresh."""
    try:
        fn(*args)
    except (db.DatabaseError, ValueError) as e:
        st.error(str(e))
        return
    flash(ok)
    st.rerun()


# ───────────────────────────── list view ─────────────────────────────
def row_colour(row: pd.Series) -> list[str]:
    """Traffic light: tint the whole row by Global Status."""
    status = row["_status"]
    bg, fg, *_ = C.STATUS_STYLE.get(status, ("", "", "", ""))
    css = f"background-color: {bg}; color: {fg};" if bg else ""
    return [css] * len(row)


def list_view(clients: list[dict]) -> None:
    st.title("לקוחות")

    counts = {s: sum(c["status"] == s for c in clients) for s in C.STATUSES}
    cols = st.columns(len(C.STATUSES) + 1)
    cols[0].metric("כל הלקוחות", len(clients))
    for col, s in zip(cols[1:], C.STATUSES):
        col.metric(f"{C.STATUS_STYLE[s][2]} {s}", counts[s])

    f1, f2, f3 = st.columns([2, 1, 1])
    query = f1.text_input("חיפוש לפי שם, ת״ז או טלפון", placeholder="הקלד לחיפוש…")
    status_f = f2.multiselect("סטטוס", C.STATUSES)
    stage_f = f3.multiselect("שלב", C.STAGES)

    rows = []
    for c in clients:
        hay = f"{c['name']} {c['id']} {c['phone']}".lower()
        if query and query.lower().strip() not in hay:
            continue
        if status_f and c["status"] not in status_f:
            continue
        if stage_f and c["stage"] not in stage_f:
            continue
        rows.append({"ת״ז": c["id"], "שם מלא": c["name"], "טלפון": c["phone"],
                     "סוג עסק": c["business_type"], "שלב": c["stage"],
                     "סטטוס": f"{C.STATUS_STYLE.get(c['status'], ('', '', '⚪'))[2]} {c['status']}",
                     "חסרים": ", ".join(c["missing"]) or "—",
                     "עודכן": c["updated"], "_status": c["status"]})

    if not rows:
        st.info("לא נמצאו לקוחות. שנה את הסינון או הוסף לקוח מהתפריט הצדדי.")
        return

    view = pd.DataFrame(rows).reset_index(drop=True)
    styled = view.style.apply(row_colour, axis=1)
    st.caption("בחר שורה כדי לפתוח את כרטיס הלקוח.")
    event = st.dataframe(
        styled, hide_index=True, use_container_width=True,
        on_select="rerun", selection_mode="single-row",
        column_order=["ת״ז", "שם מלא", "טלפון", "סוג עסק", "שלב", "סטטוס",
                      "חסרים", "עודכן"],
        key=f"table_{st.session_state.get('table_nonce', 0)}")
    if event.selection.rows:
        st.session_state["selected"] = view.iloc[event.selection.rows[0]]["ת״ז"]
        st.rerun()


# ───────────────────────────── drill-down ─────────────────────────────
def show_file(path: str, label: str, key: str) -> None:
    data = storage.read_file(path)
    if data is None:
        st.warning(f"הקובץ לא נמצא בדיסק: {path}")
        return
    if Path(path).suffix.lower() in storage.IMAGE_EXT:
        st.image(data, caption=label, use_container_width=True)
    st.download_button(f"הורד {label}", data, file_name=Path(path).name, key=key)


def detail_view(client_id: str) -> None:
    client = db.get_client(client_id, fresh=True)
    if client is None:
        st.session_state.pop("selected", None)
        st.warning("הלקוח כבר לא קיים.")
        st.rerun()

    if st.button("→ חזרה לכל הלקוחות"):
        st.session_state.pop("selected")
        st.session_state["table_nonce"] = st.session_state.get("table_nonce", 0) + 1
        st.rerun()

    _, _, emoji, colour = C.STATUS_STYLE.get(client["status"], ("", "", "⚪", "gray"))
    st.title(client["name"])
    st.markdown(f"{emoji} :{colour}[**{client['status']}**] · {client['stage']}")

    left, right = st.columns([1, 1], gap="large")

    # ---- details + status controls
    with left:
        st.subheader("פרטים")
        st.write(f"**ת״ז:** {client['id']}")
        st.write(f"**טלפון:** {client['phone'] or '—'}")
        st.write(f"**סוג עסק:** {client['business_type'] or '—'}")
        st.write(f"**עדכון אחרון:** {client['updated'] or '—'}")

        with st.expander("עריכת פרטים"):
            with st.form("edit_details"):
                name = st.text_input("שם מלא", client["name"])
                phone = st.text_input("טלפון", client["phone"])
                bt_opts = C.BUSINESS_TYPES + ([client["business_type"]]
                          if client["business_type"] not in C.BUSINESS_TYPES else [])
                btype = st.selectbox("סוג עסק", bt_opts,
                                     index=bt_opts.index(client["business_type"])
                                     if client["business_type"] in bt_opts else 0)
                if st.form_submit_button("שמור פרטים"):
                    run(db.update_details, client["id"], name, phone, btype)

        st.subheader("סטטוס")
        idx = C.STATUSES.index(client["status"]) if client["status"] in C.STATUSES else 0
        new_status = st.radio("סטטוס כללי", C.STATUSES, index=idx, horizontal=True,
                              label_visibility="collapsed")
        if new_status != client["status"]:
            if new_status == C.DONE and client["missing"]:
                st.warning(f"עדיין חסרים {len(client['missing'])} מסמכים.")
            if st.button(f"עדכן ל“{new_status}”", type="primary"):
                run(db.set_status, client["id"], new_status, ok="הסטטוס עודכן")

        st.subheader("שלב")
        stage_opts = C.STAGES + ([client["stage"]] if client["stage"] not in C.STAGES else [])
        new_stage = st.selectbox("שלב נוכחי", stage_opts,
                                 index=stage_opts.index(client["stage"])
                                 if client["stage"] in stage_opts else 0)
        reset = st.checkbox("בקש את המסמכים הסטנדרטיים של השלב", value=True)
        if st.button("החלף שלב", disabled=new_stage == client["stage"]):
            run(db.set_stage, client["id"], new_stage, reset, ok="השלב עודכן")

    # ---- missing documents
    with right:
        st.subheader("מסמכים חסרים")
        if client["missing"]:
            for doc in client["missing"]:
                st.markdown(f"- 🔴 {doc}")
        else:
            st.success("לא חסר דבר.")
        with st.form("request_doc", clear_on_submit=True):
            extra = st.text_input("בקשת מסמך נוסף", placeholder="לדוגמה: חוזה שכירות")
            if st.form_submit_button("שלח בקשה"):
                run(db.request_document, client["id"], extra, ok="המסמך התבקש")

    # ---- uploaded documents
    st.divider()
    st.subheader("מסמכים שהועלו")
    if not client["received"]:
        st.info("הלקוח עדיין לא העלה מסמכים.")
    for i, rec in enumerate(client["received"]):
        mark = "✅ אושר" if rec.get("approved") else "⏳ ממתין לבדיקה"
        with st.expander(f"{rec['doc']} — {mark} — התקבל {rec.get('time', '')}",
                         expanded=not rec.get("approved")):
            for j, path in enumerate(rec.get("files", [])):
                show_file(path, f"{rec['doc']} (עמוד {j + 1})", f"dl_{i}_{j}")
            a, b, _ = st.columns([1, 1, 2])
            if rec.get("approved"):
                if a.button("בטל אישור", key=f"unapprove_{i}"):
                    run(db.set_document_approval, client["id"], rec["doc"], False)
            elif a.button("אשר", key=f"approve_{i}", type="primary"):
                run(db.set_document_approval, client["id"], rec["doc"], True,
                    ok=f"{rec['doc']} אושר")
            if b.button("דחה ובקש שוב", key=f"reject_{i}"):
                run(db.reject_document, client["id"], rec["doc"],
                    ok=f"{rec['doc']} הוחזר ללקוח")


# ───────────────────────────── sidebar ─────────────────────────────
def sidebar() -> None:
    with st.sidebar:
        if db.is_mock():
            st.warning("מצב הדגמה: הנתונים נשמרים בקובץ CSV מקומי ולא ב-Google Sheets.")
        st.header("פעולות")
        if st.button("רענן נתונים"):
            db.get_all_clients(fresh=True)
            st.rerun()
        with st.expander("הוספת לקוח"):
            with st.form("add_client", clear_on_submit=True):
                tz = st.text_input("ת״ז")
                name = st.text_input("שם מלא")
                phone = st.text_input("טלפון")
                btype = st.selectbox("סוג עסק", C.BUSINESS_TYPES)
                stage = st.selectbox("שלב התחלתי", C.STAGES)
                if st.form_submit_button("הוסף לקוח", type="primary"):
                    norm = db.normalize_id(tz)
                    if norm and not db.is_valid_israeli_id(norm):
                        st.warning("ספרת הביקורת של הת״ז נראית שגויה – הלקוח יישמר, אנא ודא את המספר.")
                    try:
                        db.add_client(tz, name, phone, btype, stage)
                    except db.DatabaseError as e:
                        st.error(str(e))
                    else:
                        flash("הלקוח נוסף")
                        st.rerun()
        if st.button("יציאה"):
            st.session_state.clear()
            st.rerun()


# ───────────────────────────── main ─────────────────────────────
require_login()
if msg := st.session_state.pop("flash", None):
    st.toast(msg, icon="✅")
sidebar()
try:
    all_clients = db.get_all_clients()
except db.DatabaseError as e:
    st.error(str(e))
    st.stop()

if "selected" in st.session_state:
    detail_view(st.session_state["selected"])
else:
    list_view(all_clients)
