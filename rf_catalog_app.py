"""
RF & Electronic Components Catalog
-----------------------------------
A Streamlit application styled EXACTLY after industrial RF/electronics catalog
sites (Kyocera AVX style): Black top bar full width, cinematic full-width 
centered hero banner with animated panning tech background.

Data is loaded from an external CSV file (default: components_data.csv).
Run:
    streamlit run app.py
"""

import io
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st

CSV_PATH = Path("components_data.csv")

# ==========================================
# 1. SEO & URL ROUTING (Runs before page config)
# ==========================================
query_params = st.query_params
url_part = query_params.get("part", None)
page_title = "RF & Electronic Components Catalog"

if url_part and CSV_PATH.exists():
    try:
        temp_df = pd.read_csv(CSV_PATH)
        match = temp_df[temp_df["Part_Number"].astype(str).str.casefold() == url_part.casefold()]
        if not match.empty:
            cat = match.iloc[0].get("Category", "Component")
            page_title = f"{url_part} | {cat} | RF Catalog"
    except Exception:
        pass

# --------------------------------------------------------------------------
# Page configuration
# --------------------------------------------------------------------------
st.set_page_config(
    page_title=page_title,
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

NUMERIC_RANGE_COLUMNS = {
    "Gain_dB": "Gain [dB]",
    "NF_dB": "Noise Figure [dB]",
    "P1dB_dBm": "P1dB [dBm]",
    "OIP3_dBm": "OIP3 [dBm]",
    "Supply_Voltage_V": "Supply Voltage [V]",
    "Price_USD": "Price [$]",
}

FREQ_MIN_COL = "Frequency_Min_GHz"
FREQ_MAX_COL = "Frequency_Max_GHz"

QUICK_CATEGORIES = [
    {"icon": "📶", "label": "Amplifiers", "match": "amplifier"},
    {"icon": "🔀", "label": "Mixers", "match": "mixer"},
    {"icon": "🔁", "label": "RF Switches", "match": "switch"},
    {"icon": "🔄", "label": "Converters", "match": "converter"},
    {"icon": "🎛", "label": "Filters", "match": "filter"},
    {"icon": "📉", "label": "Attenuators", "match": "attenuator"},
]

def html_block(s: str) -> str:
    """Dedent a triple-quoted HTML/CSS block to prevent Streamlit black-box rendering."""
    return textwrap.dedent(s).strip("\n")

# --------------------------------------------------------------------------
# Theme / styling
# --------------------------------------------------------------------------
BG_APP = "#0B4C8C"           
TOPBAR_BG = "#151515"        # Kyocera Black
PRIMARY_BLUE = "#00355F"     
ACCENT_BLUE = "#0072CE"      
ACCENT_BLUE_LIGHT = "#E6F2FC"  
BORDER = "#D6DEE6"
TEXT_DARK = "#1A2733"        
CARD_WHITE = "#FFFFFF"

st.markdown(
    html_block(
        f"""
        <style>
        html, body {{
            overflow-x: hidden !important;
            max-width: 100vw;
            color-scheme: light !important;
        }}
        button {{
            color-scheme: light !important;
        }}
        *, *::before, *::after {{
            box-sizing: border-box;
        }}
        .stApp {{
            background-color: {BG_APP};
            overflow-x: hidden !important;
        }}
        .stApp, .stApp p, .stApp span, .stApp label, .stApp div {{
            color: #FFFFFF;
        }}
        
        /* Remove Streamlit default top padding so header is flush with browser top */
        .main .block-container {{
            padding-top: 0rem !important; 
            padding-bottom: 3rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 1500px;
            overflow-x: hidden;
        }}

        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        div[data-testid="stAppViewContainer"] {{
            padding-top: 0 !important;
        }}
        div[data-testid="stDecoration"] {{
            display: none !important;
        }}

        /* ---- Breakout class for Full Width (100vw) elements ---- */
        .full-width-breakout {{
            width: 100vw;
            position: relative;
            left: 50%;
            right: 50%;
            margin-left: -50vw;
            margin-right: -50vw;
        }}

        /* ---- EXACT Kyocera Top bar (Black) ---- */
        .rf-topbar {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            background-color: {TOPBAR_BG};
            padding: 18px 40px;
            margin-top: -1rem; /* Adjusts for any lingering Streamlit margin */
            z-index: 999;
        }}
        .rf-logo {{
            color: #FFFFFF !important;
            font-size: 1.6rem;
            font-weight: 800;
            letter-spacing: 1.5px;
            white-space: nowrap;
        }}
        .rf-nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 32px;
        }}
        .rf-nav span {{
            color: #E0E0E0 !important;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            cursor: pointer;
            transition: color 0.2s;
        }}
        .rf-nav span:hover {{
            color: {ACCENT_BLUE} !important;
        }}

        /* ---- EXACT Kyocera Hero banner (Full width, centered, panning tech background) ---- */
        .rf-hero {{
            height: 480px;
            background: url('https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=2500&q=80') center center;
            background-size: cover;
            animation: pan-hero 35s linear infinite alternate;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 4px solid {ACCENT_BLUE};
        }}
        
        /* The "Moving video" effect using slow background panning */
        @keyframes pan-hero {{
            0% {{ background-position: 0% 50%; }}
            100% {{ background-position: 100% 50%; }}
        }}

        /* Deep blue overlay tint over the moving background for text readability */
        .rf-hero-overlay {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(4, 25, 55, 0.65);
            z-index: 1;
        }}

        .rf-hero-content {{
            position: relative;
            z-index: 2;
            text-align: center;
            padding: 0 20px;
        }}
        .rf-hero-content h1 {{
            color: #FFFFFF !important;
            font-size: 4.5rem !important;
            font-weight: 300 !important;
            letter-spacing: 2.5px;
            line-height: 1.1;
            margin-bottom: 15px;
            text-shadow: 0 4px 15px rgba(0,0,0,0.5);
            text-transform: uppercase;
        }}
        .rf-hero-content p {{
            color: #E6F2FC !important;
            font-size: 1.35rem !important;
            font-weight: 400 !important;
            max-width: 900px;
            margin: 0 auto;
            text-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }}

        /* Search input styling below the hero */
        div[data-testid="stTextInput"] input {{
            border: 2px solid {ACCENT_BLUE} !important;
            border-radius: 24px !important;
            padding: 10px 20px !important;
            font-size: 1.02rem !important;
            background-color: #FFFFFF !important;
            color: {TEXT_DARK} !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        div[data-testid="stTextInput"] input::placeholder {{
            color: #8A97A5 !important;
        }}
        div[data-testid="stTextInput"] input:focus {{
            box-shadow: 0 0 0 3px rgba(0, 114, 206, 0.3);
        }}

        .browse-label {{
            text-align: center;
            color: #FFFFFF !important;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            font-size: 0.8rem;
            margin-bottom: 10px;
        }}

        /* ---- Category tile buttons (white cards, navy text) ---- */
        div[data-testid="column"] .stButton > button {{
            width: 100%;
            border-radius: 12px !important;
            border: 1px solid {BORDER} !important;
            background-color: {CARD_WHITE} !important;
            font-weight: 700 !important;
            padding: 18px 4px !important;
        }}
        div[data-testid="column"] .stButton > button,
        div[data-testid="column"] .stButton > button * {{
            color: {PRIMARY_BLUE} !important;
            -webkit-text-fill-color: {PRIMARY_BLUE} !important;
        }}
        div[data-testid="column"] .stButton > button:hover,
        div[data-testid="column"] .stButton > button:focus,
        div[data-testid="column"] .stButton > button:active {{
            background-color: {ACCENT_BLUE_LIGHT} !important;
            border-color: {ACCENT_BLUE} !important;
        }}
        div[data-testid="column"] .stButton > button:hover,
        div[data-testid="column"] .stButton > button:hover *,
        div[data-testid="column"] .stButton > button:focus,
        div[data-testid="column"] .stButton > button:focus *,
        div[data-testid="column"] .stButton > button:active,
        div[data-testid="column"] .stButton > button:active * {{
            color: {ACCENT_BLUE} !important;
            -webkit-text-fill-color: {ACCENT_BLUE} !important;
        }}
        @media (max-width: 640px) {{
            div[data-testid="column"] .stButton > button,
            div[data-testid="column"] .stButton > button * {{
                color: {PRIMARY_BLUE} !important;
                -webkit-text-fill-color: {PRIMARY_BLUE} !important;
            }}
        }}

        /* ---- Generic action buttons ---- */
        .stButton > button {{
            border-radius: 24px;
            font-weight: 600;
        }}
        .stDownloadButton > button, .stLinkButton > a {{
            background-color: {ACCENT_BLUE} !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 24px !important;
            font-weight: 600 !important;
        }}
        .stDownloadButton > button:hover, .stLinkButton > a:hover {{
            background-color: {PRIMARY_BLUE} !important;
            color: #FFFFFF !important;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: {CARD_WHITE} !important;
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] * {{
            color: {TEXT_DARK} !important;
        }}
        .sidebar-section-title {{
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 1.1px;
            text-transform: uppercase;
            color: {ACCENT_BLUE} !important;
            margin: 1.1rem 0 0.4rem 0;
            border-bottom: 2px solid {ACCENT_BLUE_LIGHT};
            padding-bottom: 6px;
        }}
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label span {{
            color: {TEXT_DARK} !important;
            opacity: 1 !important;
        }}
        section[data-testid="stSidebar"] .stButton > button {{
            background-color: #FFFFFF !important;
            color: {ACCENT_BLUE} !important;
            border: 1px solid {ACCENT_BLUE} !important;
        }}

        /* ---- Metric tiles ---- */
        div[data-testid="stMetric"] {{
            background: {CARD_WHITE} !important;
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 12px 16px 10px 16px;
        }}
        div[data-testid="stMetric"] * {{
            color: {PRIMARY_BLUE} !important;
        }}
        div[data-testid="stMetricLabel"] {{
            font-size: 0.72rem !important;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            font-weight: 700 !important;
            opacity: 0.8;
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.5rem !important;
            font-weight: 800 !important;
        }}

        h2, h3 {{
            color: #FFFFFF !important;
        }}

        /* ---- Results table ---- */
        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {BORDER};
            max-width: 100%;
        }}

        .active-chip {{
            display: inline-block;
            background-color: {CARD_WHITE};
            border: 1px solid {ACCENT_BLUE};
            color: {ACCENT_BLUE} !important;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}

        /* ---- Product Details card ---- */
        .detail-card {{
            background: {CARD_WHITE};
            border-radius: 12px;
            padding: 22px 24px;
            box-shadow: 0 2px 14px rgba(0, 0, 0, 0.18);
            width: 100%;
            overflow-x: auto;
        }}
        .detail-card, .detail-card * {{
            color: {TEXT_DARK} !important;
        }}
        .detail-title {{
            font-size: 1.5rem;
            font-weight: 800;
            color: {PRIMARY_BLUE} !important;
            margin-bottom: 2px;
        }}
        .detail-sub {{
            opacity: 0.75;
            font-size: 0.95rem;
            margin-bottom: 14px;
        }}
        .spec-label {{
            font-size: 0.68rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            opacity: 0.65;
            margin-bottom: 2px;
        }}
        .spec-value {{
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 14px;
            word-break: break-word;
        }}
        .stock-pill-in {{
            background-color: #E6F7EE;
            border: 1px solid #2ec27e;
            color: #1a8a54 !important;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
        }}
        .stock-pill-out {{
            background-color: #FDECEC;
            border: 1px solid #e03c3c;
            color: #c0302f !important;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
        }}

        footer {{visibility: hidden;}}

        /* ---- Mobile responsiveness ---- */
        @media (max-width: 800px) {{
            .rf-nav {{ display: none; }}
            .rf-topbar {{ justify-content: center; }}
            .rf-hero {{ height: 350px; }}
            .rf-hero-content h1 {{ font-size: 2.5rem !important; }}
            .rf-hero-content p {{ font-size: 1.1rem !important; }}
            .main .block-container {{
                padding-left: 0.6rem;
                padding-right: 0.6rem;
            }}
        }}
        </style>
        """
    ),
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Data loading & Strict Brand Scrubber
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading component database...")
def load_data(path: Path, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # STRICT LEGAL RULE: Nuke the manufacturer column completely if it exists
    if "Manufacturer" in df.columns:
        df = df.drop(columns=["Manufacturer"], errors="ignore")

    for col in list(NUMERIC_RANGE_COLUMNS.keys()) + [FREQ_MIN_COL, FREQ_MAX_COL, "Stock_Qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Stock_Qty" in df.columns:
        df["In_Stock"] = df["Stock_Qty"].fillna(0) > 0
    else:
        df["In_Stock"] = True

    for col in ["Part_Number", "Category", "Description", "Package", "Applications", "Drop_in_Replacement"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("")

    return df


def safe_min_max(series: pd.Series, fallback=(0.0, 1.0)):
    s = series.dropna()
    if s.empty:
        return fallback
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        hi = lo + 1e-6
    return lo, hi


# --------------------------------------------------------------------------
# Load the dataset
# --------------------------------------------------------------------------
if not CSV_PATH.exists():
    st.error(
        f"Data file `{CSV_PATH.name}` was not found in the application folder.\n\n"
        "Create a CSV file with this name (see the recommended schema), "
        "or upload one below for a one-off preview."
    )
    uploaded = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded is None:
        st.stop()
    df_raw = pd.read_csv(uploaded)
    df_raw.columns = [c.strip() for c in df_raw.columns]
    if "Manufacturer" in df_raw.columns:
        df_raw = df_raw.drop(columns=["Manufacturer"], errors="ignore")
else:
    df_raw = load_data(CSV_PATH, CSV_PATH.stat().st_mtime)

df = df_raw.copy()

if "quick_category" not in st.session_state:
    st.session_state["quick_category"] = None

# --------------------------------------------------------------------------
# Top bar + Hero banner (Full width 100vw implementation)
# --------------------------------------------------------------------------
st.markdown(
    html_block(
        """
        <div class="rf-topbar full-width-breakout">
            <div class="rf-logo">[COMPANY NAME]</div>
            <div class="rf-nav">
                <span>FILTERS</span>
                <span>DATA SHEETS</span>
                <span>NEWS/PRESS</span>
                <span>ONLINE ORDERS</span>
            </div>
        </div>
        
        <div class="rf-hero full-width-breakout">
            <div class="rf-hero-overlay"></div>
            <div class="rf-hero-content">
                <h1>ACCELERATING INNOVATION</h1>
                <p>Advanced Electronic Components and Interconnect, Sensing, Control & Antenna Solutions</p>
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)

hero_search_col1, hero_search_col2, hero_search_col3 = st.columns([1, 3, 1])
with hero_search_col2:
    hero_search = st.text_input(
        "Search",
        key="filt_search",
        placeholder="🔍  Search by part number, keyword or description (e.g. \"LNA\", \"2.4 GHz\", \"low noise\")",
        label_visibility="collapsed",
    )

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
st.markdown("<div class='browse-label'>Browse by Category</div>", unsafe_allow_html=True)

cat_cols = st.columns(len(QUICK_CATEGORIES))
for col, cat in zip(cat_cols, QUICK_CATEGORIES):
    with col:
        if st.button(f"{cat['icon']}\n\n{cat['label']}", key=f"quickcat_{cat['label']}", use_container_width=True):
            st.session_state["quick_category"] = cat["match"]

if st.session_state["quick_category"]:
    chip_col1, chip_col2 = st.columns([5, 1])
    with chip_col1:
        st.markdown(
            f"<span class='active-chip'>Category filter: {st.session_state['quick_category'].title()} ✕</span>",
            unsafe_allow_html=True,
        )
    with chip_col2:
        if st.button("Clear category", key="clear_quickcat"):
            st.session_state["quick_category"] = None
            st.rerun()

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Sidebar — advanced filters
# --------------------------------------------------------------------------
st.sidebar.markdown(
    f"<div style='font-size:1.05rem; font-weight:800; letter-spacing:0.4px; color:{PRIMARY_BLUE} !important;'>⚙ ADVANCED FILTERS</div>",
    unsafe_allow_html=True,
)
st.sidebar.caption("Refine the catalog using the parameters below.")

if st.sidebar.button("↺ Reset all filters", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key.startswith("filt_"):
            del st.session_state[key]
    st.session_state["quick_category"] = None
    if "part" in st.query_params:
        del st.query_params["part"]
    st.rerun()

st.sidebar.markdown("<div class='sidebar-section-title'>Classification</div>", unsafe_allow_html=True)

if "Category" in df.columns:
    categories = sorted(df["Category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect("Category", options=categories, key="filt_category")
else:
    selected_categories = []

if "Package" in df.columns:
    packages = sorted(df["Package"].dropna().unique().tolist())
    selected_packages = st.sidebar.multiselect("Package", options=packages, key="filt_package")
else:
    selected_packages = []

st.sidebar.markdown("<div class='sidebar-section-title'>Availability</div>", unsafe_allow_html=True)
stock_filter = st.sidebar.radio(
    "Stock status",
    options=["All", "In Stock Only", "Out of Stock Only"],
    key="filt_stock",
    label_visibility="collapsed",
)

freq_selected_range = None
if FREQ_MIN_COL in df.columns and FREQ_MAX_COL in df.columns:
    st.sidebar.markdown("<div class='sidebar-section-title'>Frequency Range (GHz)</div>", unsafe_allow_html=True)
    combined_freq = pd.concat([df[FREQ_MIN_COL], df[FREQ_MAX_COL]])
    f_lo, f_hi = safe_min_max(combined_freq, fallback=(0.0, 40.0))
    freq_selected_range = st.sidebar.slider(
        "Include parts overlapping this range",
        min_value=round(f_lo, 3),
        max_value=round(f_hi, 3),
        value=(round(f_lo, 3), round(f_hi, 3)),
        key="filt_freq",
        label_visibility="collapsed",
    )

numeric_selected_ranges = {}
active_numeric_cols = [c for c in NUMERIC_RANGE_COLUMNS if c in df.columns and df[c].notna().any()]
if active_numeric_cols:
    st.sidebar.markdown("<div class='sidebar-section-title'>Performance Parameters</div>", unsafe_allow_html=True)
    for col in active_numeric_cols:
        label = NUMERIC_RANGE_COLUMNS[col]
        lo, hi = safe_min_max(df[col])
        with st.sidebar.expander(label, expanded=False):
            selected = st.slider(
                label,
                min_value=round(lo, 2),
                max_value=round(hi, 2),
                value=(round(lo, 2), round(hi, 2)),
                key=f"filt_{col}",
                label_visibility="collapsed",
            )
            numeric_selected_ranges[col] = selected

# --------------------------------------------------------------------------
# Apply filters
# --------------------------------------------------------------------------
filtered = df.copy()

if hero_search:
    text_cols = [c for c in ["Part_Number", "Description", "Drop_in_Replacement", "Applications"] if c in filtered.columns]
    if text_cols:
        mask = pd.Series(False, index=filtered.index)
        for c in text_cols:
            mask |= filtered[c].str.contains(hero_search, case=False, na=False)
        filtered = filtered[mask]

if st.session_state["quick_category"] and "Category" in filtered.columns:
    filtered = filtered[filtered["Category"].str.contains(st.session_state["quick_category"], case=False, na=False)]

if selected_categories:
    filtered = filtered[filtered["Category"].isin(selected_categories)]

if selected_packages:
    filtered = filtered[filtered["Package"].isin(selected_packages)]

if stock_filter == "In Stock Only":
    filtered = filtered[filtered["In_Stock"]]
elif stock_filter == "Out of Stock Only":
    filtered = filtered[~filtered["In_Stock"]]

if freq_selected_range is not None:
    f_min_sel, f_max_sel = freq_selected_range
    filtered = filtered[
        (filtered[FREQ_MIN_COL].fillna(-1e9) <= f_max_sel)
        & (filtered[FREQ_MAX_COL].fillna(1e9) >= f_min_sel)
    ]

for col, (lo_sel, hi_sel) in numeric_selected_ranges.items():
    filtered = filtered[filtered[col].isna() | filtered[col].between(lo_sel, hi_sel)]

# --------------------------------------------------------------------------
# Determine Product Details logic (SEO / URL integration)
# --------------------------------------------------------------------------
part_to_display = None

# --------------------------------------------------------------------------
# Summary metrics & Main Table
# --------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Parts", len(df))
m2.metric("Matching Results", len(filtered))
if "In_Stock" in filtered.columns:
    m3.metric("In Stock", int(filtered["In_Stock"].sum()))
if "Price_USD" in filtered.columns and not filtered.empty:
    avg_price = filtered["Price_USD"].mean()
    m4.metric("Avg. Price (USD)", f"${avg_price:,.2f}" if pd.notna(avg_price) else "—")

st.markdown("###  ")
st.subheader("Search Results")

if filtered.empty:
    st.warning("No components match the current filters. Try widening the ranges or clearing filters.")
    event = None
else:
    display_df = filtered.copy()
    if "In_Stock" in display_df.columns:
        display_df["Availability"] = display_df["In_Stock"].map({True: "✅ In Stock", False: "❌ Out of Stock"})

    column_order = [
        c for c in [
            "Part_Number", "Category", "Description", FREQ_MIN_COL, FREQ_MAX_COL,
            "Gain_dB", "NF_dB", "P1dB_dBm", "OIP3_dBm", "Package",
            "Price_USD", "Availability", "Stock_Qty"
        ] if c in display_df.columns
    ]
    remaining_cols = [c for c in display_df.columns if c not in column_order and c != "In_Stock"]
    column_order += remaining_cols

    event = st.dataframe(
        display_df[column_order],
        use_container_width=True,
        hide_index=True,
        height=430,
        on_select="rerun",
        selection_mode="single-row",
        key="results_table",
    )

    dl_col, hint_col = st.columns([1, 4])
    with dl_col:
        csv_buffer = io.StringIO()
        filtered.drop(columns=["In_Stock"], errors="ignore").to_csv(csv_buffer, index=False)
        st.download_button(
            label="⬇ Download Filtered Results (CSV)",
            data=csv_buffer.getvalue(),
            file_name="filtered_components.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with hint_col:
        st.caption("Click any row in the table above to open its full parametric datasheet below and generate its unique link.")

# Figure out which part to display based on table click OR URL
if event and event.selection.rows:
    sel_idx = filtered.index[event.selection.rows[0]]
    part_to_display = filtered.loc[sel_idx]
    st.query_params["part"] = part_to_display.get("Part_Number", "")
elif url_part:
    matching_parts = df[df["Part_Number"].astype(str).str.casefold() == url_part.casefold()]
    if not matching_parts.empty:
        part_to_display = matching_parts.iloc[0]

# ----------------------------------------------------------------
# Product Details Card
# ----------------------------------------------------------------
st.markdown("###  ")
st.subheader("Product Details")

if part_to_display is None:
    st.info("Select a component from the table above to view its full specifications.")
else:
    st.markdown("<div class='detail-card'>", unsafe_allow_html=True)

    header_col, badge_col = st.columns([4, 1])
    with header_col:
        title = part_to_display.get("Part_Number", "Component")
        desc = part_to_display.get("Description", "")
        cat = part_to_display.get("Category", "")
        
        sub_line = " · ".join([v for v in [cat, desc] if v])
        
        st.markdown(f"<div class='detail-title'>{title}</div>", unsafe_allow_html=True)
        if sub_line:
            st.markdown(f"<div class='detail-sub'>{sub_line}</div>", unsafe_allow_html=True)
            
    with badge_col:
        if part_to_display.get("In_Stock", True):
            st.markdown("<span class='stock-pill-in'>✅ IN STOCK</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='stock-pill-out'>❌ OUT OF STOCK</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    skip_cols = {"In_Stock", "Part_Number", "Description", "Datasheet_URL", "Category"}
    items = [(k, v) for k, v in part_to_display.items() if k not in skip_cols and str(v).strip() not in ["nan", ""]]

    n_cols = 4
    spec_cols = st.columns(n_cols)
    for i, (key, value) in enumerate(items):
        display_value = "—" if (pd.isna(value) or value == "") else str(value)
        col = spec_cols[i % n_cols]
        col.markdown(
            html_block(
                f"""
                <div class='spec-label'>{key.replace('_', ' ')}</div>
                <div class='spec-value'>{display_value}</div>
                """
            ),
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    action_col1, action_col2, _ = st.columns([1.4, 1.4, 3])

    with action_col1:
        datasheet_url = part_to_display.get("Datasheet_URL", "")
        if isinstance(datasheet_url, str) and datasheet_url.startswith("http"):
            st.link_button("📄 Open Datasheet", datasheet_url, use_container_width=True)
        else:
            st.button("📄 Datasheet Unavailable", disabled=True, use_container_width=True)

    with action_col2:
        single_buffer = io.StringIO()
        pd.DataFrame([part_to_display.drop(labels=["In_Stock"], errors="ignore")]).to_csv(single_buffer, index=False)
        st.download_button(
            label="⬇ Export This Part (CSV)",
            data=single_buffer.getvalue(),
            file_name=f"{part_to_display.get('Part_Number', 'component')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.markdown("---")
st.caption(
    f"Generic Industry Standard RF Components Catalog. Data source: `{CSV_PATH.name}`"
)