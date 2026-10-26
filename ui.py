"""Shared Hebrew / RTL / mobile-first look & feel for both apps."""
import html

import streamlit as st

import config as C

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&display=swap');
:root {--navy:#12355b; --navy2:#1d4f82; --gold:#b8924a; --ink:#1b2a41; --line:#dbe3ef;}

html, body, .stApp, [data-testid="stSidebar"] {direction: rtl;}
.stApp {font-family: 'Heebo', 'Assistant', Arial, sans-serif; color: var(--ink);
        background: linear-gradient(180deg, #e6edf7 0, #f6f8fc 340px, #f6f8fc 100%);}
.stMarkdown, .stAlert, label, p, h1, h2, h3, h4, li,
[data-testid="stMetric"], [data-testid="stCaptionContainer"] {text-align: right;}
h1, h2, h3, h4 {color: var(--navy); letter-spacing: -0.01em;}
input, textarea, [data-baseweb="select"] {direction: rtl; text-align: right;}
[role="radiogroup"], [role="tablist"] {direction: rtl;}

/* chrome */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding: 1.2rem 1.2rem 5rem; max-width: 1100px;}
[data-testid="stSidebar"] {background: #fff; border-left: 1px solid var(--line);}

/* banner */
.crm-banner {background: linear-gradient(135deg, var(--navy) 0%, var(--navy2) 100%); color: #fff;
             border-radius: 16px; padding: 1.1rem 1.3rem; margin-bottom: 1.1rem;
             border-bottom: 4px solid var(--gold); box-shadow: 0 6px 18px rgba(18,53,91,.18);}
.crm-firm {font-size: .8rem; letter-spacing: .08em; opacity: .8;}
.crm-title {font-size: 1.6rem; font-weight: 700; line-height: 1.25;}
.crm-sub {font-size: .95rem; opacity: .85; margin-top: .15rem;}

/* cards, metrics, buttons */
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px; background: #fff;
    border-color: var(--line); box-shadow: 0 2px 10px rgba(18,53,91,.07);}
[data-testid="stMetric"] {background: #fff; border: 1px solid var(--line); border-radius: 12px;
                          padding: .6rem .8rem;}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button
    {min-height: 2.9rem; border-radius: 12px; font-weight: 500;}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"]
    {background: var(--navy); border-color: var(--navy);}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover
    {background: var(--navy2); border-color: var(--gold);}
input, textarea {font-size: 16px !important;}   /* stops iOS zoom-on-focus */

/* Hebrew text for the built-in upload widget (best effort: relies on Streamlit's markup) */
[data-testid="stFileUploaderDropzoneInstructions"] span, 
[data-testid="stFileUploaderDropzoneInstructions"] small {display: none;}
[data-testid="stFileUploaderDropzoneInstructions"]::before
    {content: "גררו קבצים לכאן או לחצו על ״בחירת קבצים״"; font-size: .95rem;}
[data-testid="stFileUploaderDropzone"] button {font-size: 0 !important;}
[data-testid="stFileUploaderDropzone"] button::after {content: "בחירת קבצים"; font-size: 1rem;}
[data-testid="stCameraInputButton"] {font-size: 0 !important;}
[data-testid="stCameraInputButton"]::after {content: "צילום"; font-size: 1rem;}

@media (max-width: 640px) {
  .block-container {padding: .8rem .65rem 5rem;}
  .crm-title {font-size: 1.3rem;}
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


def header(title: str, subtitle: str = "") -> None:
    """Branded banner at the top of a page."""
    sub = f'<div class="crm-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="crm-banner"><div class="crm-firm">{html.escape(C.FIRM_NAME)}</div>'
                f'<div class="crm-title">{html.escape(title)}</div>{sub}</div>',
                unsafe_allow_html=True)
