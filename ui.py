"""Shared Hebrew / RTL styling for both apps."""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&display=swap');
html, body, .stApp, [data-testid="stSidebar"] {direction: rtl;}
.stApp {font-family: 'Heebo', 'Assistant', Arial, sans-serif;}
.stMarkdown, .stAlert, label, p, h1, h2, h3, h4, li,
[data-testid="stMetric"], [data-testid="stCaptionContainer"] {text-align: right;}
input, textarea, [data-baseweb="select"] {direction: rtl; text-align: right;}
[role="radiogroup"], [role="tablist"] {direction: rtl;}
</style>
"""


def apply_rtl() -> None:
    """Call once, right after st.set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)
