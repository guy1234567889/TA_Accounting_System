"""שער כניסה ראשי למערכת – בחר בין כניסת משרד לפורטל לקוחות"""
import streamlit as st
import ui
import config as C
import runpy
from pathlib import Path

st.set_page_config(page_title=f"{C.FIRM_NAME} – מערכת ניהול", page_icon="🗂️", layout="centered")
ui.apply_rtl()

# מנהל מצב ניווט אם נבחר
if "portal_mode" not in st.session_state:
    st.session_state["portal_mode"] = None

if st.session_state["portal_mode"] == "admin":
    runpy.run_path(str(Path(__file__).with_name("admin_app.py")), run_name="__main__")
elif st.session_state["portal_mode"] == "client":
    runpy.run_path(str(Path(__file__).with_name("client_portal.py")), run_name="__main__")
else:
    ui.header(C.FIRM_NAME, "מערכת ניהול משרד ופורטל לקוחות מאובטח")

    st.markdown("### אנא בחר את סוג הכניסה הרצוי:")

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        with st.container(border=True):
            st.subheader("👨‍💼 כניסת משרד")
            st.write("לשימוש רואה החשבון והצוות בלבד. דורש סיסמת ניהול.")
            if st.button("כניסת מנהל / רו\"ח", type="primary", use_container_width=True):
                st.session_state["portal_mode"] = "admin"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("📄 פורטל לקוחות")
            st.write("ללקוחות המשרד – צפייה בסטטוס התיק והעלאת מסמכים בקלות.")
            if st.button("כניסת לקוחות", use_container_width=True):
                st.session_state["portal_mode"] = "client"
                st.rerun()
