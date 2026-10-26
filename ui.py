"""Shared Hebrew / RTL / mobile-first styling for both apps."""
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

/* app-like chrome */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding: 1.2rem 1.2rem 5rem; max-width: 1100px;}

/* touch-friendly controls; 16px inputs stop iOS from zooming on focus */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button
    {min-height: 2.9rem; border-radius: 12px; font-weight: 500;}
input, textarea {font-size: 16px !important;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
[data-testid="stMetric"] {background: rgba(128,128,128,.08); border-radius: 12px; padding: .6rem .8rem;}

@media (max-width: 640px) {
  .block-container {padding: .8rem .65rem 5rem;}
  h1 {font-size: 1.55rem !important;}
  h2, h3 {font-size: 1.2rem !important;}
  [data-testid="stMetricValue"] {font-size: 1.5rem;}
  .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {width: 100%;}
}
</style>
"""


def apply_rtl() -> None:
    """Call once, right after st.set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)
