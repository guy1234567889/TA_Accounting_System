"""פורטל לקוחות (Mobile-first) – הרצה:  streamlit run client_portal.py --server.port 8502"""
import time

import streamlit as st

import config as C
import db_handler as db
import storage
import ui

st.set_page_config(page_title=f"{C.FIRM_NAME} – פורטל לקוחות", page_icon="📄",
                   layout="centered", initial_sidebar_state="collapsed")
ui.apply_rtl()

MAX_ATTEMPTS, LOCK_SECONDS, IDLE_SECONDS = 5, 60, 30 * 60
FRIENDLY = {
    C.WAITING: "אנחנו ממתינים למסמכים שלכם. אפשר להעלות אותם ישר מהטלפון.",
    C.REVIEW: "תודה! קיבלנו את המסמכים, והמשרד בודק אותם.",
    C.DONE: "התיק הושלם ואושר. אין צורך בשום דבר נוסף.",
}


# ───────────────────────────── login ─────────────────────────────
def login_screen() -> None:
    ui.header("ברוכים הבאים", "הפורטל האישי שלכם – סטטוס התיק והעלאת מסמכים")
    if msg := st.session_state.pop("flash_info", None):
        st.info(msg)
    if db.is_mock():
        with st.expander("מצב הדגמה – פרטי כניסה לדוגמה"):
            try:
                for c in db.get_all_clients():
                    st.code(f"ת״ז {c['id']}   טלפון {c['phone']}   {c['name']}", language=None)
            except db.DatabaseError as e:
                st.error(str(e))

    locked_for = int(st.session_state.get("locked_until", 0) - time.time())
    if locked_for > 0:
        st.error(f"בוצעו יותר מדי ניסיונות. נסו שוב בעוד {locked_for} שניות.")
        return

    with st.form("login"):
        raw_id = st.text_input("תעודת זהות", max_chars=9, placeholder="9 ספרות",
                               help="מספר תעודת הזהות שלכם, כולל אפסים מובילים")
        raw_phone = st.text_input("טלפון נייד", max_chars=15, placeholder="0501234567",
                                  help="המספר הרשום אצלנו בתיק")
        go = st.form_submit_button("כניסה", type="primary", use_container_width=True)
    st.caption("הכניסה מאובטחת. תוצגו רק הנתונים האישיים שלכם.")
    if not go:
        return
    try:
        client = db.authenticate(raw_id, raw_phone)
    except db.LoginError as e:
        fails = st.session_state.get("fails", 0) + 1
        st.session_state["fails"] = fails
        if fails >= MAX_ATTEMPTS:
            st.session_state.update(locked_until=time.time() + LOCK_SECONDS, fails=0)
            st.rerun()
        st.error(str(e))
        return
    except db.ValidationError as e:
        st.error(str(e))
        return
    except db.DatabaseError:
        st.error("השירות אינו זמין כרגע. נסו שוב בעוד כמה דקות.")
        return
    st.session_state.update(client_id=client["id"], fails=0, last_seen=time.time())
    st.rerun()


# ───────────────────────────── uploads ─────────────────────────────
def document_card(client: dict, doc: str) -> None:
    """One card per missing document: pick/take a photo, then send."""
    nonce = st.session_state.get("nonce", 0)       # bumped after each send to reset the widgets
    key = f"{doc}_{nonce}"
    with st.container(border=True):
        st.subheader(doc)
        mode = st.radio("איך תרצו להוסיף?", ["צילום או בחירת קובץ", "מצלמה בדפדפן"],
                        key=f"mode_{key}", label_visibility="collapsed")
        files: list[tuple[str, bytes]] = []
        if mode == "מצלמה בדפדפן":
            st.caption("הניחו את המסמך על משטח ישר, באור טוב, כך שימלא את המסגרת.")
            shot = st.camera_input("צילום המסמך", key=f"cam_{key}", label_visibility="collapsed")
            if shot:
                files.append((shot.name if "." in shot.name else "scan.jpg", shot.getvalue()))
        else:
            st.caption("בטלפון תוכלו לבחור ״צילום״ או תמונה מהגלריה. אפשר להוסיף כמה עמודים.")
            picked = st.file_uploader("בחירת קבצים", key=f"up_{key}", accept_multiple_files=True,
                                      type=[e[1:] for e in sorted(storage.ALLOWED_EXT)],
                                      help=f"תמונות או PDF, עד {storage.MAX_BYTES // 1024 // 1024} MB לכל קובץ",
                                      label_visibility="collapsed")
            files += [(f.name, f.getvalue()) for f in picked or []]

        if st.button(f"שליחת ״{doc}״", key=f"send_{key}", type="primary",
                     use_container_width=True, disabled=not files):
            with st.spinner("מעלים את הקבצים…"):
                try:
                    db.register_upload(client["id"], doc, files)
                except (db.DatabaseError, ValueError) as e:
                    st.error(str(e))
                    return
            st.session_state["nonce"] = nonce + 1
            st.session_state["flash"] = f"״{doc}״ התקבל. תודה!"
            st.rerun()


# ───────────────────────────── portal ─────────────────────────────
def portal(client_id: str) -> None:
    try:
        client = db.get_client(client_id, fresh=True)   # only ever the logged-in client's own file
    except db.DatabaseError:
        st.error("השירות אינו זמין כרגע. נסו לרענן בעוד דקה.")
        return
    if client is None:
        st.session_state.clear()
        st.rerun()

    first = client["name"].split()[0] if client["name"] else ""
    ui.header(f"שלום {first}", "התיק האישי שלכם")
    if msg := st.session_state.pop("flash", None):
        st.success(msg, icon="✅")

    _, _, emoji, colour = C.STATUS_STYLE.get(client["status"], ("", "", "⚪", "gray"))
    with st.container(border=True):
        st.markdown(f"### {emoji} :{colour}[{client['status']}]")
        st.write(FRIENDLY.get(client["status"], ""))
        total = len(client["missing"]) + len(client["received"])
        if total:
            st.progress(len(client["received"]) / total,
                        text=f"נשלחו {len(client['received'])} מתוך {total} מסמכים")
        if client["status"] == C.DONE and client["finalized"]:
            st.caption(f"התיק הושלם ואושר ב-{client['finalized']}")
        if C.FIRM_PHONE:
            st.caption(f"לשאלות ניתן לפנות למשרד: {C.FIRM_PHONE}")

    with st.expander("הפרטים שלי"):
        st.write(f"**שם:** {client['name']}")
        st.write(f"**תעודת זהות:** ••••• {client['id'][-4:]}")
        st.write(f"**טלפון:** {db.format_phone(client['phone']) or '—'}")
        st.write(f"**סוג עסק:** {client['business_type'] or '—'}")
        st.write(f"**שלב נוכחי:** {client['stage'] or '—'}")
        st.caption("לעדכון פרטים יש לפנות למשרד.")

    if client["status"] != C.DONE:
        if client["missing"]:
            st.subheader(f"מסמכים להעלאה ({len(client['missing'])})")
            for doc in client["missing"]:
                document_card(client, doc)
        else:
            st.info("שלחתם את כל המסמכים שביקשנו. נחזור אליכם אם יידרש משהו נוסף.")

    if client["received"]:
        with st.expander(f"מסמכים שכבר נשלחו ({len(client['received'])})"):
            for rec in client["received"]:
                state = "אושר ✅" if rec.get("approved") else "התקבל, בבדיקה ⏳"
                st.write(f"**{rec['doc']}** – {state}")

    st.divider()
    if st.button("התנתקות", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# auto-logout after 30 idle minutes (shared phones)
if "client_id" in st.session_state:
    if time.time() - st.session_state.get("last_seen", 0) > IDLE_SECONDS:
        st.session_state.clear()
        st.session_state["flash_info"] = "ההתחברות הסתיימה עקב חוסר פעילות. אנא היכנסו שוב."
        st.rerun()
    st.session_state["last_seen"] = time.time()
    portal(st.session_state["client_id"])
else:
    login_screen()
