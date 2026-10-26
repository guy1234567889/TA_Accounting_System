"""Client portal (mobile-first) – run with:  streamlit run client_app.py --server.port 8502"""
import time

import streamlit as st

import config as C
import db_handler as db
import ui

st.set_page_config(page_title="העלאת מסמכים", page_icon="📄", layout="centered")
ui.apply_rtl()

MAX_ATTEMPTS, LOCK_SECONDS = 5, 60

st.markdown("""
<style>
  header[data-testid="stHeader"], footer {visibility: hidden;}
  .block-container {padding: 1.2rem 1rem 4rem; max-width: 560px;}
  .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button
      {width: 100%; min-height: 3.1rem; font-size: 1.05rem; border-radius: 10px;}
  input {font-size: 1.1rem !important;}
</style>
""", unsafe_allow_html=True)

FRIENDLY = {
    C.WAITING: ("אנחנו ממתינים למסמכים שלך.", "red"),
    C.REVIEW: ("תודה! רואה החשבון שלך בודק את המסמכים.", "orange"),
    C.DONE: ("הכול הושלם – אין צורך בשום דבר נוסף.", "green"),
}


# ───────────────────────────── login ─────────────────────────────
def login_screen() -> None:
    st.title("ברוכים הבאים")
    st.write("הזן את מספר תעודת הזהות כדי לראות אילו מסמכים אנחנו צריכים ממך.")

    if db.is_mock():
        with st.expander("מצב הדגמה – מספרי ת״ז לדוגמה"):
            try:
                for c in db.get_all_clients():
                    st.code(f"{c['id']}   {c['name']}  ({c['status']})", language=None)
            except db.DatabaseError as e:
                st.error(str(e))

    locked_for = int(st.session_state.get("locked_until", 0) - time.time())
    if locked_for > 0:
        st.error(f"יותר מדי ניסיונות. נסה שוב בעוד {locked_for} שניות.")
        return

    with st.form("login"):
        raw = st.text_input("מספר תעודת זהות", max_chars=9, placeholder="9 ספרות")
        go = st.form_submit_button("המשך", type="primary")
    if not go:
        return

    try:
        tz = db.validate_id(raw)
    except db.ValidationError as e:
        st.error(str(e))
        return
    try:
        client = db.get_client(tz, fresh=True)
    except db.DatabaseError:
        st.error("השירות אינו זמין כרגע. נסה שוב בעוד כמה דקות.")
        return

    if client is None:
        fails = st.session_state.get("fails", 0) + 1
        st.session_state["fails"] = fails
        if fails >= MAX_ATTEMPTS:
            st.session_state.update(locked_until=time.time() + LOCK_SECONDS, fails=0)
            st.rerun()
        st.error("לא מצאנו תעודת זהות כזו. בדוק את המספר או פנה למשרד רואה החשבון.")
        return

    st.session_state.update(client_id=client["id"], fails=0)
    st.rerun()


# ───────────────────────────── upload widgets ─────────────────────────────
def document_card(client: dict, doc: str) -> None:
    """One card per missing document: camera scan or file upload, then 'Send'."""
    nonce = st.session_state.get("nonce", 0)       # bumped after each send to reset widgets
    key = f"{doc}_{nonce}"
    with st.container(border=True):
        st.subheader(doc)
        mode = st.radio("איך תרצה להוסיף?",
                        ["העלאת קובץ או צילום", "סריקה במצלמה"],
                        key=f"mode_{key}", label_visibility="collapsed")
        files: list[tuple[str, bytes]] = []
        if mode == "סריקה במצלמה":
            st.caption("הנח את המסמך על משטח ישר, באור טוב, כך שימלא את המסגרת.")
            shot = st.camera_input("צלם", key=f"cam_{key}", label_visibility="collapsed")
            if shot:
                files.append((shot.name if "." in shot.name else "scan.jpg", shot.getvalue()))
        else:
            st.caption("בטלפון אפשר לבחור ״צילום״ או לבחור מהגלריה. "
                       "אפשר להוסיף כמה עמודים.")
            picked = st.file_uploader("בחר קבצים", key=f"up_{key}", accept_multiple_files=True,
                                      type=["jpg", "jpeg", "png", "pdf", "heic", "webp"],
                                      label_visibility="collapsed")
            files += [(f.name, f.getvalue()) for f in picked or []]

        if st.button(f"שלח {doc}", key=f"send_{key}", type="primary", disabled=not files):
            with st.spinner("מעלה…"):
                try:
                    db.register_upload(client["id"], doc, files)
                except (db.DatabaseError, ValueError) as e:
                    st.error(str(e))
                    return
            st.session_state["nonce"] = nonce + 1
            st.session_state["flash"] = f"{doc} התקבל. תודה!"
            st.rerun()


# ───────────────────────────── portal ─────────────────────────────
def portal(client_id: str) -> None:
    try:
        client = db.get_client(client_id, fresh=True)
    except db.DatabaseError:
        st.error("השירות אינו זמין כרגע. נסה לרענן בעוד דקה.")
        return
    if client is None:                               # record deleted while logged in
        st.session_state.clear()
        st.rerun()

    if msg := st.session_state.pop("flash", None):
        st.success(msg, icon="✅")

    first = client["name"].split()[0] if client["name"] else ""
    st.title(f"שלום {first}")
    text, colour = FRIENDLY.get(client["status"], ("", "gray"))
    st.markdown(f":{colour}[**{text}**]")

    total = len(client["missing"]) + len(client["received"])
    if total:
        st.progress(len(client["received"]) / total,
                    text=f"נשלחו {len(client['received'])} מתוך {total} מסמכים")

    if client["status"] == C.DONE:
        pass                                          # nothing to upload
    elif not client["missing"]:
        st.info("שלחת את כל מה שביקשנו. ניצור קשר אם יידרש משהו נוסף.")
    else:
        st.subheader(f"המסמכים שאנחנו צריכים ({len(client['missing'])})")
        for doc in client["missing"]:
            document_card(client, doc)

    if client["received"]:
        with st.expander(f"נשלחו כבר ({len(client['received'])})"):
            for rec in client["received"]:
                state = "אושר ✅" if rec.get("approved") else "התקבל, בבדיקה ⏳"
                st.write(f"**{rec['doc']}** – {state}")

    st.divider()
    if st.button("התנתקות"):
        st.session_state.clear()
        st.rerun()


if "client_id" in st.session_state:
    portal(st.session_state["client_id"])
else:
    login_screen()
