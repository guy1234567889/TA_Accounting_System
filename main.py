"""שער כניסה ראשי למערכת – בחר בין כניסת משרד לפורטל לקוחות"""
import streamlit as st
import ui
import config as C

st.set_page_config(page_title=f"{C.FIRM_NAME} – מערכת ניהול", page_icon="🗂️", layout="centered")
ui.apply_rtl()

ui.header(C.FIRM_NAME, "מערכת ניהול משרד ופורטל לקוחות מאובטח")

st.markdown("### אנא בחר את סוג הכניסה הרצוי:")

col1, col2 = st.columns(2, gap="medium")

with col1:
    with st.container(border=True):
        st.subheader("👨‍💼 כניסת משרד")
        st.write("לשימוש רואה החשבון והצוות בלבד. דורש סיסמת ניהול.")
        if st.button("כניסת מנהל / רו\"ח", type="primary", use_container_width=True):
            st.switch_page("admin_app.py")

with col2:
    with st.container(border=True):
        st.subheader("📄 פורטל לקוחות")
        st.write("ללקוחות המשרד – צפייה בסטטוס התיק והעלאת מסמכים בקלות.")
        if st.button("כניסת לקוחות", use_container_width=True):
            st.switch_page("client_portal.py")
