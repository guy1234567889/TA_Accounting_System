"""Accountant dashboard – run with:  streamlit run admin_app.py"""
import hmac
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
STATUS_HEX = {C.WAITING: "#d64545", C.REVIEW: "#e0b01b", C.DONE: "#3d9a5b"}   # traffic light
STAGE_HEX = ["#2f7d6d", "#5b7bd5", "#a0527c", "#8a8f98"]


def row_colour(row: pd.Series) -> list[str]:
    """Traffic light: tint the whole row by Global Status."""
    bg, fg, *_ = C.STATUS_STYLE.get(row["_status"], ("", "", "", ""))
    return [f"background-color: {bg}; color: {fg};" if bg else ""] * len(row)


def quarter_of(ts: str) -> str | None:
    """'2026-10-21 19:48' -> '2026-Q4'."""
    try:
        d = datetime.strptime((ts or "")[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def quarter_label(q: str) -> str:
    year, n = q.split("-Q")
    return f"רבעון {n} · {year}"


def pie(counts: dict[str, int], colours: list[str]) -> None:
    data = pd.DataFrame({"label": list(counts), "count": list(counts.values())})
    if data["count"].sum() == 0:
        st.info("אין עדיין נתונים להצגה.")
        return
    st.vega_lite_chart(data[data["count"] > 0], {
        "mark": {"type": "arc", "innerRadius": 55},
        "encoding": {
            "theta": {"field": "count", "type": "quantitative"},
            "color": {"field": "label", "type": "nominal",
                      "scale": {"domain": list(counts), "range": colours},
                      "legend": {"orient": "bottom", "title": None}},
            "tooltip": [{"field": "label", "title": "קטגוריה"},
                        {"field": "count", "title": "לקוחות"}]}},
        use_container_width=True)


def dashboard(clients: list[dict]) -> None:
    st.subheader("דשבורד")
    total = len(clients)
    by_status = {s: sum(c["status"] == s for c in clients) for s in C.STATUSES}

    this_q = quarter_of(datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%Y-%m-%d"))
    quarters = sorted({quarter_of(c["updated"]) for c in clients} - {None} | {this_q}, reverse=True)
    q = st.selectbox("רבעון לדיווח", quarters, format_func=quarter_label)
    finished_q = sum(1 for c in clients if c["status"] in (C.REVIEW, C.DONE)
                     and not c["missing"] and quarter_of(c["updated"]) == q)

    top = st.columns(2)
    top[0].metric("סה״כ לקוחות", total)
    top[1].metric("סיימו להעלות הכול ברבעון", finished_q,
                  help="לקוחות ללא מסמכים חסרים שעודכנו לאחרונה ברבעון שנבחר")
    for col, s in zip(st.columns(len(C.STATUSES)), C.STATUSES):
        pct = f"{by_status[s] / total:.0%}" if total else "0%"
        col.metric(f"{C.STATUS_STYLE[s][2]} {s}", by_status[s], pct, delta_color="off")

    by = st.radio("פילוח לפי", ["סטטוס", "שלב"], horizontal=True)
    if by == "סטטוס":
        pie(by_status, [STATUS_HEX[s] for s in C.STATUSES])
    else:
        stages = {s: sum(c["stage"] == s for c in clients) for s in C.STAGES}
        if total - sum(stages.values()):
            stages["אחר"] = total - sum(stages.values())
        pie(stages, STAGE_HEX[:len(stages)])


def cards(rows: list[dict]) -> None:
    """Mobile-friendly list: one tappable card per client."""
    limit = st.session_state.get("card_limit", 30)
    for c in rows[:limit]:
        _, _, emoji, colour = C.STATUS_STYLE.get(c["status"], ("", "", "⚪", "gray"))
        with st.container(border=True):
            st.markdown(f"**{c['name']}** · ת״ז {c['id']}\n\n"
                        f"{emoji} :{colour}[**{c['status']}**] · {c['stage'] or '—'}\n\n"
                        f"📞 {db.format_phone(c['phone']) or '—'} · "
                        f"חסרים: {', '.join(c['missing']) or '—'}")
            if st.button("פתח כרטיס", key=f"open_{c['id']}", use_container_width=True):
                st.session_state["selected"] = c["id"]
                st.rerun()
    if len(rows) > limit and st.button(f"הצג עוד ({len(rows) - limit})"):
        st.session_state["card_limit"] = limit + 30
        st.rerun()


def table(rows: list[dict]) -> None:
    view = pd.DataFrame([
        {"ת״ז": c["id"], "שם מלא": c["name"], "טלפון": c["phone"], "סוג עסק": c["business_type"],
         "שלב": c["stage"],
         "סטטוס": f"{C.STATUS_STYLE.get(c['status'], ('', '', '⚪'))[2]} {c['status']}",
         "חסרים": ", ".join(c["missing"]) or "—", "עודכן": c["updated"], "_status": c["status"]}
        for c in rows]).reset_index(drop=True)
    st.caption("בחר שורה כדי לפתוח את כרטיס הלקוח.")
    event = st.dataframe(
        view.style.apply(row_colour, axis=1), hide_index=True, use_container_width=True,
        on_select="rerun", selection_mode="single-row",
        column_order=["ת״ז", "שם מלא", "טלפון", "סוג עסק", "שלב", "סטטוס", "חסרים", "עודכן"],
        key=f"table_{st.session_state.get('table_nonce', 0)}")
    if event.selection.rows:
        st.session_state["selected"] = view.iloc[event.selection.rows[0]]["ת״ז"]
        st.rerun()


def list_view(clients: list[dict]) -> None:
    st.title("לקוחות")
    dashboard(clients)
    st.divider()

    query = st.text_input("חיפוש לפי שם, ת״ז או טלפון", placeholder="הקלד לחיפוש…")
    with st.expander("סינון נוסף"):
        status_f = st.multiselect("סטטוס", C.STATUSES)
        stage_f = st.multiselect("שלב", C.STAGES)
    rows = [c for c in clients
            if (not query or query.lower().strip() in f"{c['name']} {c['id']} {c['phone']}".lower())
            and (not status_f or c["status"] in status_f)
            and (not stage_f or c["stage"] in stage_f)]
    if not rows:
        st.info("לא נמצאו לקוחות. שנה את הסינון או הוסף לקוח מהתפריט הצדדי.")
        return
    mode = st.radio("תצוגה", ["כרטיסים", "טבלה"], horizontal=True)
    st.caption(f"{len(rows)} לקוחות")
    (cards if mode == "כרטיסים" else table)(rows)


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

    # ---- verification against the client
    st.divider()
    st.subheader("אימות מול הלקוח")
    v1, v2 = st.columns(2)
    v1.write("✅ ת״ז תקינה" if db.is_valid_israeli_id(client["id"])
             else "⚠️ ת״ז לא עוברת בדיקת ספרת ביקורת")
    try:
        db.validate_phone(client["phone"])
        v2.write("✅ טלפון תקין")
    except db.ValidationError:
        v2.write("⚠️ הטלפון אינו תקין – מומלץ לעדכן")
    got = {}
    for rec in client["received"]:
        got[rec["doc"]] = got.get(rec["doc"], False) or bool(rec.get("approved"))
    required = list(dict.fromkeys(C.STAGE_DOCUMENTS.get(client["stage"], [])
                                  + list(got) + client["missing"]))
    for doc in required:
        st.write(f"{'🔴 חסר' if doc not in got else '✅ אושר' if got[doc] else '⏳ התקבל – ממתין לאישור'}"
                 f" — {doc}")
    if required:
        approved_n = sum(got.get(d, False) for d in required)
        st.progress(approved_n / len(required), text=f"אושרו {approved_n} מתוך {len(required)} מסמכים")

    # ---- uploaded documents
    st.divider()
    st.subheader("מסמכים שהועלו")
    if not client["received"]:
        st.info("הלקוח עדיין לא העלה מסמכים.")
    for i, rec in enumerate(client["received"]):
        mark = "✅ אושר" if rec.get("approved") else "⏳ ממתין לבדיקה"
        with st.expander(f"{rec['doc']} — {mark} — התקבל {rec.get('time', '')}{' · 🏢 צורף ע״י המשרד' if rec.get('source') == 'office' else ''}",
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


    # ---- attach files from the office
    st.divider()
    st.subheader("צירוף קבצים מטעם המשרד")
    options = client["missing"] + ["➕ מסמך אחר…"]
    with st.form("office_upload", clear_on_submit=True):
        choice = st.selectbox("עבור איזה מסמך?", options)
        custom = st.text_input("שם המסמך (כשבוחרים ״מסמך אחר״)")
        files = st.file_uploader("בחר קבצים", accept_multiple_files=True,
                                 type=[e[1:] for e in sorted(storage.ALLOWED_EXT)])
        approve = st.checkbox("סמן כמאושר מיד", value=True)
        if st.form_submit_button("צרף קבצים", type="primary"):
            run(db.attach_office_files, client["id"], custom if choice == options[-1] else choice,
                [(f.name, f.getvalue()) for f in files or []], approve, ok="הקבצים צורפו")


# ───────────────────────────── sidebar ─────────────────────────────
def sidebar() -> None:
    with st.sidebar:
        if db.is_mock():
            st.warning("מצב הדגמה: הנתונים נשמרים בקובץ CSV מקומי ולא ב-Google Sheets.")
        st.header("פעולות")
        if st.button("רענן נתונים"):
            db.get_all_clients(fresh=True)
            st.rerun()
        if storage.drive_enabled() and st.button("בדיקת חיבור ל-Google Drive"):
            ok, msg = storage.check_backend()
            (st.success if ok else st.error)(msg)
        with st.expander("הוספת לקוח"):
            with st.form(f"add_client_{st.session_state.get('add_n', 0)}"):
                tz = st.text_input("ת״ז", max_chars=9, placeholder="9 ספרות", help="תעודת זהות ישראלית תקינה, 9 ספרות כולל אפסים מובילים")
                name = st.text_input("שם מלא", placeholder="שם פרטי ושם משפחה")
                phone = st.text_input("טלפון", max_chars=15, placeholder="0501234567")
                btype = st.selectbox("סוג עסק", C.BUSINESS_TYPES)
                stage = st.selectbox("שלב התחלתי", C.STAGES)
                if st.form_submit_button("הוסף לקוח", type="primary"):
                    try:
                        db.add_client(tz, name, phone, btype, stage)
                    except db.DatabaseError as e:
                        st.error(str(e))
                    else:
                        st.session_state["add_n"] = st.session_state.get("add_n", 0) + 1
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
