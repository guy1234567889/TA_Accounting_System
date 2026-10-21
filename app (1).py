"""
RF & Electronic Components Catalog
-----------------------------------
A Streamlit application for browsing, filtering and comparing RF and
electronic components, styled after industrial parametric catalogs
(e.g. Analog Devices / Mini-Circuits parametric search tools).

Data is loaded from an external CSV file (default: components_data.csv),
so the catalog (stock, pricing, specs) can be updated without touching
this code.

Run:
    streamlit run app.py
"""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------
# Page configuration
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="RF & Components Catalog",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_PATH = Path("components_data.csv")

# "Core" columns the app knows how to build dedicated filters for.
# Any extra columns present in the CSV are still shown automatically
# in the table and in the detail card.
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

# --------------------------------------------------------------------------
# Theme / styling — dark, industrial, ADI-inspired
# --------------------------------------------------------------------------
ACCENT = "#00A9E0"       # signal-blue accent
ACCENT_DIM = "#0B6E96"
BG_PANEL = "#12161C"
BG_CARD = "#171C24"
BORDER = "#262C36"
TEXT_MUTED = "#8B93A1"

st.markdown(
    f"""
    <style>
        html, body, [class*="css"] {{
            font-family: "Inter", "Segoe UI", -apple-system, sans-serif;
        }}

        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }}

        /* ---- Top banner ---- */
        .catalog-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 26px;
            background: linear-gradient(90deg, {BG_PANEL} 0%, #0D1117 100%);
            border: 1px solid {BORDER};
            border-left: 4px solid {ACCENT};
            border-radius: 10px;
            margin-bottom: 1.4rem;
        }}
        .catalog-header h1 {{
            font-size: 1.55rem;
            font-weight: 700;
            letter-spacing: 0.3px;
            margin: 0;
            color: #E8EBF0;
        }}
        .catalog-header p {{
            margin: 2px 0 0 0;
            color: {TEXT_MUTED};
            font-size: 0.88rem;
            letter-spacing: 0.4px;
            text-transform: uppercase;
        }}
        .catalog-badge {{
            background: rgba(0, 169, 224, 0.12);
            border: 1px solid {ACCENT_DIM};
            color: {ACCENT};
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] .block-container {{
            padding-top: 1.2rem;
        }}
        .sidebar-section-title {{
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: {ACCENT};
            margin: 1.1rem 0 0.3rem 0;
            border-bottom: 1px solid {BORDER};
            padding-bottom: 6px;
        }}

        /* ---- Metric tiles ---- */
        div[data-testid="stMetric"] {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 12px 16px 8px 16px;
        }}
        div[data-testid="stMetricLabel"] {{
            font-size: 0.72rem;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            color: {TEXT_MUTED};
        }}
        div[data-testid="stMetricValue"] {{
            font-size: 1.55rem;
            color: #E8EBF0;
        }}

        /* ---- Table ---- */
        .stDataFrame {{
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid {BORDER};
        }}

        /* ---- Detail card ---- */
        .detail-card {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-left: 4px solid {ACCENT};
            border-radius: 10px;
            padding: 22px 26px;
        }}
        .detail-title {{
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: 0.3px;
            color: #F1F3F6;
            margin-bottom: 2px;
        }}
        .detail-sub {{
            color: {TEXT_MUTED};
            font-size: 0.95rem;
            margin-bottom: 14px;
        }}
        .spec-label {{
            font-size: 0.68rem;
            letter-spacing: 0.6px;
            text-transform: uppercase;
            color: {TEXT_MUTED};
            margin-bottom: 2px;
        }}
        .spec-value {{
            font-size: 1.05rem;
            font-weight: 600;
            color: #E8EBF0;
            margin-bottom: 14px;
        }}
        .stock-pill-in {{
            background-color: rgba(46, 194, 126, 0.14);
            border: 1px solid #2ec27e;
            color: #6fe3ab;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .stock-pill-out {{
            background-color: rgba(224, 60, 60, 0.14);
            border: 1px solid #e03c3c;
            color: #ff8a8a;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading component database...")
def load_data(path: Path, mtime: float) -> pd.DataFrame:
    """Loads the CSV file. The `mtime` argument is only used to bust the
    Streamlit cache automatically whenever the underlying file changes."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    # Lenient numeric coercion so a slightly messy CSV doesn't crash the app
    for col in list(NUMERIC_RANGE_COLUMNS.keys()) + [FREQ_MIN_COL, FREQ_MAX_COL, "Stock_Qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Stock_Qty" in df.columns:
        df["In_Stock"] = df["Stock_Qty"].fillna(0) > 0
    else:
        df["In_Stock"] = True

    for col in ["Part_Number", "Category", "Manufacturer", "Description", "Package"]:
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
else:
    df_raw = load_data(CSV_PATH, CSV_PATH.stat().st_mtime)

df = df_raw.copy()

# --------------------------------------------------------------------------
# Sidebar — filters
# --------------------------------------------------------------------------
st.sidebar.markdown(
    "<div style='font-size:1.05rem; font-weight:800; letter-spacing:0.5px;'>⚙ PARAMETRIC SEARCH</div>",
    unsafe_allow_html=True,
)
st.sidebar.caption("Narrow down the catalog using the filters below.")

if st.sidebar.button("↺ Reset all filters", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key.startswith("filt_"):
            del st.session_state[key]
    st.rerun()

# --- Free-text search ---
st.sidebar.markdown("<div class='sidebar-section-title'>Quick Search</div>", unsafe_allow_html=True)
search_text = st.sidebar.text_input(
    "Part Number / Description",
    key="filt_search",
    placeholder="e.g. LNA-2440 or Low Noise Amplifier",
    label_visibility="collapsed",
)

# --- Category / Manufacturer / Package ---
st.sidebar.markdown("<div class='sidebar-section-title'>Classification</div>", unsafe_allow_html=True)

if "Category" in df.columns:
    categories = sorted(df["Category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect("Category", options=categories, key="filt_category")
else:
    selected_categories = []

if "Manufacturer" in df.columns:
    manufacturers = sorted(df["Manufacturer"].dropna().unique().tolist())
    selected_manufacturers = st.sidebar.multiselect("Manufacturer", options=manufacturers, key="filt_manufacturer")
else:
    selected_manufacturers = []

if "Package" in df.columns:
    packages = sorted(df["Package"].dropna().unique().tolist())
    selected_packages = st.sidebar.multiselect("Package", options=packages, key="filt_package")
else:
    selected_packages = []

# --- Stock availability ---
st.sidebar.markdown("<div class='sidebar-section-title'>Availability</div>", unsafe_allow_html=True)
stock_filter = st.sidebar.radio(
    "Stock status",
    options=["All", "In Stock Only", "Out of Stock Only"],
    key="filt_stock",
    label_visibility="collapsed",
)

# --- Frequency range ---
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

# --- Other numeric parameters ---
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

if search_text:
    text_cols = [c for c in ["Part_Number", "Description"] if c in filtered.columns]
    if text_cols:
        mask = pd.Series(False, index=filtered.index)
        for c in text_cols:
            mask |= filtered[c].str.contains(search_text, case=False, na=False)
        filtered = filtered[mask]

if selected_categories:
    filtered = filtered[filtered["Category"].isin(selected_categories)]

if selected_manufacturers:
    filtered = filtered[filtered["Manufacturer"].isin(selected_manufacturers)]

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
# Header banner
# --------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="catalog-header">
        <div>
            <h1>📡 RF & Electronic Components Catalog</h1>
            <p>Parametric Search · Stock Availability · Technical Datasheets</p>
        </div>
        <div class="catalog-badge">Live Inventory</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Summary metrics
# --------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Parts in Catalog", len(df))
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
else:
    display_df = filtered.copy()
    if "In_Stock" in display_df.columns:
        display_df["Availability"] = display_df["In_Stock"].map({True: "✅ In Stock", False: "❌ Out of Stock"})

    column_order = [
        c
        for c in [
            "Part_Number",
            "Category",
            "Manufacturer",
            "Description",
            FREQ_MIN_COL,
            FREQ_MAX_COL,
            "Gain_dB",
            "NF_dB",
            "P1dB_dBm",
            "OIP3_dBm",
            "Package",
            "Price_USD",
            "Availability",
            "Stock_Qty",
        ]
        if c in display_df.columns
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
        st.caption("Click any row in the table above to open its full parametric datasheet below.")

    # ----------------------------------------------------------------
    # Product Details Card
    # ----------------------------------------------------------------
    st.markdown("###  ")
    st.subheader("Product Details")

    selected_rows = event.selection.rows if event is not None else []

    if not selected_rows:
        st.info("Select a component from the table above to view its full specifications.")
    else:
        sel_idx = filtered.index[selected_rows[0]]
        part = filtered.loc[sel_idx]

        st.markdown("<div class='detail-card'>", unsafe_allow_html=True)

        header_col, badge_col = st.columns([4, 1])
        with header_col:
            title = part.get("Part_Number", "Component")
            desc = part.get("Description", "")
            manuf = part.get("Manufacturer", "")
            sub_line = " · ".join([v for v in [manuf, desc] if v])
            st.markdown(f"<div class='detail-title'>{title}</div>", unsafe_allow_html=True)
            if sub_line:
                st.markdown(f"<div class='detail-sub'>{sub_line}</div>", unsafe_allow_html=True)
        with badge_col:
            if part.get("In_Stock", True):
                st.markdown("<span class='stock-pill-in'>✅ IN STOCK</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='stock-pill-out'>❌ OUT OF STOCK</span>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        skip_cols = {"In_Stock", "Part_Number", "Description", "Manufacturer", "Datasheet_URL"}
        items = [(k, v) for k, v in part.items() if k not in skip_cols]

        n_cols = 4
        spec_cols = st.columns(n_cols)
        for i, (key, value) in enumerate(items):
            display_value = "—" if (pd.isna(value) or value == "") else str(value)
            col = spec_cols[i % n_cols]
            col.markdown(
                f"""
                <div class='spec-label'>{key.replace('_', ' ')}</div>
                <div class='spec-value'>{display_value}</div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # Action row: datasheet link + single-part CSV export
        st.markdown("<br>", unsafe_allow_html=True)
        action_col1, action_col2, _ = st.columns([1.4, 1.4, 3])

        with action_col1:
            datasheet_url = part.get("Datasheet_URL", "")
            if isinstance(datasheet_url, str) and datasheet_url.startswith("http"):
                st.link_button("📄 Open Datasheet", datasheet_url, use_container_width=True)
            else:
                st.button("📄 Datasheet Unavailable", disabled=True, use_container_width=True)

        with action_col2:
            single_buffer = io.StringIO()
            pd.DataFrame([part.drop(labels=["In_Stock"], errors="ignore")]).to_csv(single_buffer, index=False)
            st.download_button(
                label="⬇ Export This Part (CSV)",
                data=single_buffer.getvalue(),
                file_name=f"{part.get('Part_Number', 'component')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

st.markdown("---")
st.caption(
    f"Data source: `{CSV_PATH.name}` — update this file to change stock levels, pricing or specs. "
    "The app reloads automatically when the file changes."
)
