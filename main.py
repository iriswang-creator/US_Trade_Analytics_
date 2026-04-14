import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

# ─── 頁面基本設定（一定要放在最前面）───
st.set_page_config(
    page_title="US Trade Intelligence Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 引入其他模組 ───
from sidebar import render_sidebar
from view import render_view
from view_agent import render_tab6_ai_analyst
from view_multi_agent import render_tab7_multi_agent

# ─── 先取得 sidebar 設定（含 theme）───
filters = render_sidebar()
_light = filters["theme"] == "Light"

# ─── 全域 CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ══ BASE ══ */
html, body, [class*="css"], .stApp {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #0a0a0b !important;
}
.block-container {
    padding: 2rem 3rem 3rem !important;
    max-width: 1400px !important;
}
#MainMenu, footer, header { visibility: hidden; }

/* ══ KPI CARDS ══ */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 2rem;
}
.kpi-card {
    background: #111113;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 1.2rem 1.4rem 1.2rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.15s ease;
}
.kpi-card:hover { border-color: rgba(255,255,255,0.14); }
.kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; bottom: 0;
    width: 2px;
    border-radius: 10px 0 0 10px;
}
.kpi-card.red::before   { background: #ef4444; }
.kpi-card.green::before { background: #22c55e; }
.kpi-card.blue::before  { background: #5b8dee; }
.kpi-label {
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #52525e;
    margin-bottom: 0.5rem;
}
.kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 0.5rem;
}
.kpi-delta {
    font-size: 0.74rem;
    font-weight: 500;
    padding: 2px 7px;
    border-radius: 4px;
    display: inline-block;
    letter-spacing: 0.01em;
}
.kpi-delta.neg { background: rgba(239,68,68,0.1);  color: #f87171; }
.kpi-delta.pos { background: rgba(34,197,94,0.1);  color: #4ade80; }
.kpi-delta.neu { background: rgba(91,141,238,0.1); color: #5b8dee; }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    margin-bottom: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important;
    padding: 11px 22px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
    transition: color 0.15s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { background: transparent !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: transparent !important;
    border-bottom: 2px solid #5b8dee !important;
    box-shadow: none !important;
}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 1.5rem !important;
    background: transparent !important;
}

/* ══ SIDEBAR ══ */
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(255,255,255,0.07) !important;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.66rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.06) !important;
}

/* ══ INPUTS ══ */
[data-baseweb="select"] > div {
    border-radius: 8px !important;
}
[data-baseweb="popover"] > div, [data-baseweb="menu"] {
    border-radius: 8px !important;
}
[data-baseweb="input"] { border-radius: 8px !important; }

/* ══ RADIO ══ */
.stRadio > div { gap: 4px !important; }

/* ══ SLIDER ══ */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: #5b8dee !important;
    border-color: #5b8dee !important;
}

/* ══ METRIC ══ */
[data-testid="stMetricLabel"] { font-size: 0.78rem !important; font-weight: 500 !important; }
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.4rem !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

/* ══ ALERTS ══ */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 0.88rem !important;
}

/* ══ DATAFRAME ══ */
[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    overflow: hidden !important;
}

/* ══ CHARTS ══ */
[data-testid="stPlotlyChart"] {
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ══ BUTTONS ══ */
.stButton > button, .stDownloadButton > button {
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: border-color 0.15s ease, background 0.15s ease !important;
    box-shadow: none !important;
}

/* ══ DIVIDER ══ */
hr { margin: 1rem 0 !important; }

/* ══ CAPTION ══ */
[data-testid="stCaptionContainer"] p {
    font-size: 0.78rem !important;
}

/* ══ SUBHEADER ══ */
h2[data-testid="stHeading"], h3[data-testid="stHeading"] {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.15rem !important;
    letter-spacing: -0.02em !important;
    text-transform: none !important;
}

/* ══ BOLD SECTION LABELS ══ */
[data-testid="stMarkdownContainer"] strong {
    font-weight: 800 !important;
    font-size: 1rem !important;
}
[data-testid="stMarkdownContainer"] p strong {
    display: block !important;
    text-align: center !important;
    font-weight: 800 !important;
    font-size: 1rem !important;
}

/* ══ H4 HEADINGS inside tabs ══ */
[data-testid="stMarkdownContainer"] h4 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 800 !important;
    font-size: 1.05rem !important;
    letter-spacing: -0.02em !important;
    text-align: center !important;
    margin: 1rem 0 0.5rem !important;
}

/* ══ METRIC CARDS ══ */
[data-testid="stMetric"] { text-align: center !important; }
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3f3f46; }

/* ══ AI ANALYST LEFT PANEL BUTTONS ══ */
/* Make suggestion buttons left-aligned and compact */
[data-testid="stVerticalBlock"] .stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 8px 12px !important;
    line-height: 1.35 !important;
    height: auto !important;
    white-space: normal !important;
}

/* ══ CHAT MESSAGE MARKDOWN ══ */
/* Keep paragraphs as blocks so text doesn't run together */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
    display: block !important;
    text-align: left !important;
    margin-bottom: 0.4rem !important;
}
/* Override the global centered-bold rule inside chat bubbles */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p strong,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {
    display: inline !important;
    text-align: left !important;
    font-size: inherit !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Theme override CSS ───
# ─── 依主題設定顏色變數 ───
if _light:
    _bg           = "#fafafa"
    _text         = "#18181b"
    _text_sec     = "#71717a"
    _text_muted   = "#a1a1aa"
    _accent       = "#2563eb"
    _sb_bg        = "#fafafa"
    _sb_border    = "rgba(0,0,0,0.07)"
    _sb_text      = "#71717a"
    _sb_heading   = "#a1a1aa"
    _tab_border   = "rgba(0,0,0,0.08)"
    _tab_color    = "#a1a1aa"
    _tab_act_clr  = "#18181b"
    _kpi_bg       = "#ffffff"
    _kpi_border   = "rgba(0,0,0,0.07)"
    _kpi_label    = "#a1a1aa"
    _kpi_val      = "#18181b"
    _input_bg     = "#ffffff"
    _input_border = "rgba(0,0,0,0.1)"
    _input_text   = "#18181b"
    _menu_bg      = "#ffffff"
    _menu_border  = "rgba(0,0,0,0.08)"
    _menu_text    = "#18181b"
    _menu_hover   = "rgba(0,0,0,0.04)"
    _alert_bg     = "#ffffff"
    _alert_border = "rgba(0,0,0,0.07)"
    _alert_text   = "#71717a"
    _chart_border = "rgba(0,0,0,0.06)"
    _hr_color     = "rgba(0,0,0,0.07)"
    _caption      = "#a1a1aa"
    _heading      = "#18181b"
    _metric_lbl   = "#71717a"
    _metric_val   = "#18181b"
    _btn_bg       = "#ffffff"
    _btn_border   = "rgba(0,0,0,0.1)"
    _btn_color    = "#18181b"
    _btn_hover_bg = "#f4f4f5"
else:
    _bg           = "#0a0a0b"
    _text         = "#ededef"
    _text_sec     = "#8b8b96"
    _text_muted   = "#52525e"
    _accent       = "#5b8dee"
    _sb_bg        = "#0a0a0b"
    _sb_border    = "rgba(255,255,255,0.07)"
    _sb_text      = "#8b8b96"
    _sb_heading   = "#52525e"
    _tab_border   = "rgba(255,255,255,0.07)"
    _tab_color    = "#52525e"
    _tab_act_clr  = "#ededef"
    _kpi_bg       = "#111113"
    _kpi_border   = "rgba(255,255,255,0.07)"
    _kpi_label    = "#52525e"
    _kpi_val      = "#ededef"
    _input_bg     = "#111113"
    _input_border = "rgba(255,255,255,0.08)"
    _input_text   = "#ededef"
    _menu_bg      = "#18181b"
    _menu_border  = "rgba(255,255,255,0.08)"
    _menu_text    = "#ededef"
    _menu_hover   = "rgba(255,255,255,0.05)"
    _alert_bg     = "#111113"
    _alert_border = "rgba(255,255,255,0.07)"
    _alert_text   = "#8b8b96"
    _chart_border = "rgba(255,255,255,0.06)"
    _hr_color     = "rgba(255,255,255,0.06)"
    _caption      = "#52525e"
    _heading      = "#ededef"
    _metric_lbl   = "#8b8b96"
    _metric_val   = "#ededef"
    _btn_bg       = "#111113"
    _btn_border   = "rgba(255,255,255,0.09)"
    _btn_color    = "#ededef"
    _btn_hover_bg = "#18181b"

st.markdown(f"""
<style>
html, body, [class*="css"], .stApp {{
    background-color: {_bg} !important;
    color: {_text} !important;
}}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6,
[data-testid="stHeading"],
[data-testid="stVerticalBlock"] label {{ color: {_text} !important; }}
[data-testid="stCaptionContainer"] p {{ color: {_caption} !important; }}
section[data-testid="stSidebar"] {{
    background: {_sb_bg} !important;
    border-right: 1px solid {_sb_border} !important;
}}
section[data-testid="stSidebar"] * {{ color: {_sb_text} !important; }}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{ color: {_sb_heading} !important; }}
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {_tab_border} !important;
}}
.stTabs [data-baseweb="tab"] {{ color: {_tab_color} !important; }}
.stTabs [data-baseweb="tab"]:hover {{ color: {_text_sec} !important; }}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: {_tab_act_clr} !important;
    border-bottom: 2px solid {_accent} !important;
}}
.kpi-card {{
    background: {_kpi_bg} !important;
    border: 1px solid {_kpi_border} !important;
}}
.kpi-label {{ color: {_kpi_label} !important; }}
.kpi-value {{ color: {_kpi_val} !important; }}
[data-baseweb="select"] > div {{
    background: {_input_bg} !important;
    border-color: {_input_border} !important;
    color: {_input_text} !important;
}}
[data-baseweb="popover"] > div, [data-baseweb="menu"] {{
    background: {_menu_bg} !important;
    border: 1px solid {_menu_border} !important;
}}
[data-baseweb="menu"] li {{ color: {_menu_text} !important; }}
[data-baseweb="menu"] li:hover {{ background: {_menu_hover} !important; }}
[data-baseweb="input"] input {{
    color: {_input_text} !important;
    -webkit-text-fill-color: {_input_text} !important;
}}
[data-testid="stAlert"] {{
    background: {_alert_bg} !important;
    border: 1px solid {_alert_border} !important;
}}
[data-testid="stAlert"] p {{ color: {_alert_text} !important; }}
[data-testid="stMetricLabel"] {{ color: {_metric_lbl} !important; }}
[data-testid="stMetricValue"] {{ color: {_metric_val} !important; }}
[data-testid="stPlotlyChart"] {{ border: 1px solid {_chart_border} !important; }}
[data-testid="stDataFrame"] {{ border: 1px solid {_chart_border} !important; }}
[data-testid="stAlert"] {{ background: {_alert_bg} !important; border-color: {_alert_border} !important; }}
hr {{ border-color: {_hr_color} !important; }}
.stButton > button, .stDownloadButton > button {{
    background: {_btn_bg} !important;
    border: 1px solid {_btn_border} !important;
    color: {_btn_color} !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    background: {_btn_hover_bg} !important;
    border-color: {_btn_border} !important;
}}
</style>
""", unsafe_allow_html=True)

# ─── App Header ───
_header_title = "#18181b" if _light else "#ededef"
_header_eye   = "#a1a1aa" if _light else "#52525e"
_header_sub   = "#71717a" if _light else "#3f3f46"
st.markdown(f"""
<div style='padding: 12px 0 24px 0;'>
    <div style='
        font-family: DM Sans, sans-serif;
        font-size: 0.66rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: {_header_eye};
        margin-bottom: 10px;
    '>US · Census Bureau · 1985–2026</div>
    <div style='
        font-family: Syne, sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        color: {_header_title};
        letter-spacing: -0.03em;
        line-height: 1;
        margin-bottom: 8px;
    '>Trade Analytics</div>
    <div style='
        font-family: DM Sans, sans-serif;
        font-size: 0.85rem;
        color: {_header_sub};
        letter-spacing: 0;
    '>240+ partner countries &nbsp;·&nbsp; Exports, Imports &amp; Balance</div>
</div>
""", unsafe_allow_html=True)

# ─── KPI 摘要列 ───
@st.cache_data
def get_kpi_data():
    df = pd.read_excel("data/country.xlsx")
    df = df[df["CTY_CODE"] > 1000].copy()
    df["BALANCE"] = df["EYR"] - df["IYR"]
    df_2024 = df[df["year"] == 2024].copy()
    df_2023 = df[df["year"] == 2023].copy()
    worst = df_2024.loc[df_2024["BALANCE"].idxmin()]
    best  = df_2024.loc[df_2024["BALANCE"].idxmax()]
    total_2024 = df_2024["EYR"].sum() + df_2024["IYR"].sum()
    total_2023 = df_2023["EYR"].sum() + df_2023["IYR"].sum()
    yoy = ((total_2024 - total_2023) / total_2023) * 100
    return worst, best, yoy, total_2024

worst, best, yoy, total_2024 = get_kpi_data()

yoy_cls   = "pos" if yoy >= 0 else "neg"
yoy_sign  = "↑" if yoy >= 0 else "↓"

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card red">
        <div class="kpi-label">Largest Deficit Partner · 2024</div>
        <div class="kpi-value">{worst['CTYNAME']}</div>
        <span class="kpi-delta neg">${worst['BALANCE']/1000:.1f}B deficit</span>
    </div>
    <div class="kpi-card green">
        <div class="kpi-label">Largest Surplus Partner · 2024</div>
        <div class="kpi-value">{best['CTYNAME']}</div>
        <span class="kpi-delta pos">${best['BALANCE']/1000:.1f}B surplus</span>
    </div>
    <div class="kpi-card blue">
        <div class="kpi-label">Total Trade Volume YoY</div>
        <div class="kpi-value">${total_2024/1e6:.1f}T</div>
        <span class="kpi-delta {yoy_cls}">{yoy_sign} {abs(yoy):.1f}% vs 2023</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Data source badge ───
if "Live" in filters.get("data_source", ""):
    st.markdown("""
        <div style='display:inline-block;background:#064e3b;color:#6ee7b7;
        font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
        padding:3px 10px;border-radius:4px;margin-bottom:8px;'>
        ● LIVE API
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style='display:inline-block;background:#1e3a5f;color:#93c5fd;
        font-size:0.72rem;font-weight:600;letter-spacing:0.08em;
        padding:3px 10px;border-radius:4px;margin-bottom:8px;'>
        ● LOCAL DATA
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ─── 六個主要 Tab ───
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "TRADE MAP",
    "BILATERAL FLOW",
    "PRODUCT TREND",
    "TRADE BALANCE",
    "HISTORICAL EVOLUTION",
    "AI ANALYST",
    "MULTI-AGENT",
])

# ─── 各 Tab 內容 ───
render_view(tab1, tab2, tab3, tab4, tab5, filters)

with tab6:
    render_tab6_ai_analyst(filters)

with tab7:
    render_tab7_multi_agent(filters)
