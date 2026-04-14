import streamlit as st
import pandas as pd

def render_sidebar():
    st.sidebar.markdown("""
<style>
.sb-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #52525e !important;
    margin-bottom: 8px;
    margin-top: 4px;
    display: block;
}
</style>
""", unsafe_allow_html=True)

    # ── Data Source ──
    st.sidebar.markdown('<span class="sb-label">Data Source</span>', unsafe_allow_html=True)
    data_source = st.sidebar.radio(
        "Data source",
        options=["Local Data (1985–2026)", "Live API (2013–present)"],
        index=0,
        key="data_source",
        label_visibility="collapsed",
    )
    if data_source == "Live API (2013–present)":
        st.sidebar.success("Live mode — pulling from\nU.S. Census Bureau API")
        st.sidebar.caption("Data updates automatically.\nCovers 2013 to present.")
    else:
        st.sidebar.caption("Using downloaded dataset.\nCovers 1985 to 2026.")

    st.sidebar.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # ── Brand ──
    st.sidebar.markdown("""
<div style='padding: 1.2rem 0 1rem;'>
    <div style='font-family: Syne, sans-serif; font-size: 1rem; font-weight: 800;
                letter-spacing: -0.01em; margin-bottom: 2px;'>
        US Trade Intel
    </div>
    <div style='font-size: 0.72rem; color: #52525e;'>1985 – 2026</div>
</div>
<hr style='border-color: rgba(255,255,255,0.07); margin: 0 0 1rem;'>
""", unsafe_allow_html=True)

    # ── Theme ──
    st.sidebar.markdown('<span class="sb-label">Appearance</span>', unsafe_allow_html=True)
    theme = st.sidebar.radio(
        "Theme",
        options=["Dark", "Light"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.sidebar.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # ── Quick Compare ──
    st.sidebar.markdown('<span class="sb-label">Quick Compare</span>', unsafe_allow_html=True)
    preset = st.sidebar.radio(
        "Load preset pair",
        options=[
            "Custom",
            "China vs Japan",
            "Mexico vs Canada",
            "Germany vs France",
        ],
        index=0,
        label_visibility="collapsed",
    )

    preset_map = {
        "China vs Japan":    ("China", "Japan"),
        "Mexico vs Canada":  ("Mexico", "Canada"),
        "Germany vs France": ("Germany", "France"),
    }

    if preset == "Custom":
        st.sidebar.caption("Select countries in the Bilateral Flow tab")
        preset_country_a, preset_country_b = None, None
    else:
        preset_country_a, preset_country_b = preset_map[preset]
        st.sidebar.caption(f"A: {preset_country_a}  ·  B: {preset_country_b}")

    st.sidebar.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # ── Year Range ──
    st.sidebar.markdown('<span class="sb-label">Year Range</span>', unsafe_allow_html=True)
    year_min = 2013 if data_source == "Live API (2013–present)" else 1985
    year_start = st.session_state.get("year_range", (year_min, 2024))[0]
    year_end = st.session_state.get("year_range", (year_min, 2024))[1]
    if year_start < year_min:
        year_start = year_min
    if year_end < year_min:
        year_end = year_min
    year_range = st.sidebar.slider(
        "Select years",
        min_value=year_min,
        max_value=2025,
        value=(year_start, year_end),
        label_visibility="collapsed",
    )
    if data_source == "Live API (2013–present)":
        st.sidebar.info("Live data only available from 2013 onward. Earlier years are not available in live mode.")
    st.sidebar.caption(f"{year_range[0]} – {year_range[1]}  ·  Tabs 2, 3, 4")

    st.sidebar.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

    # ── Display Unit ──
    st.sidebar.markdown('<span class="sb-label">Display Unit</span>', unsafe_allow_html=True)
    unit = st.sidebar.radio(
        "Value unit",
        options=["Million USD", "Billion USD"],
        horizontal=True,
        label_visibility="collapsed",
    )
    unit_divisor = 1 if unit == "Million USD" else 1000
    unit_label   = "M USD" if unit == "Million USD" else "B USD"

    # ── Footer ──
    st.sidebar.markdown("""
<hr style='border-color: rgba(255,255,255,0.07); margin: 1.4rem 0 0.8rem;'>
<div style='font-size: 0.7rem; color: #3f3f46;'>
    U.S. Census Bureau Foreign Trade Division
</div>
""", unsafe_allow_html=True)

    return {
        "year_range":       year_range,
        "unit_divisor":     unit_divisor,
        "unit_label":       unit_label,
        "preset_country_a": preset_country_a,
        "preset_country_b": preset_country_b,
        "theme":            theme,
        "data_source":      data_source,
    }
