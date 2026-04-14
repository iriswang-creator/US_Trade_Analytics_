"""
census_api.py — Live data fetcher from the U.S. Census Bureau International Trade API.
No API key required. Free tier: 500 calls/day.

Endpoints used:
  Exports: https://api.census.gov/data/timeseries/intltrade/exports/hs
  Imports: https://api.census.gov/data/timeseries/intltrade/imports/hs
"""

import requests
import pandas as pd
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


_EXPORT_URL = (
    "https://api.census.gov/data/timeseries/intltrade/exports/hs"
    "?get=CTY_CODE,CTY_NAME,ALL_VAL_YR&YEAR={year}&MONTH=12"
)
_IMPORT_URL = (
    "https://api.census.gov/data/timeseries/intltrade/imports/hs"
    "?get=CTY_CODE,CTY_NAME,CNT_VAL_YR&YEAR={year}&MONTH=12"
)

_TIMEOUT = 15  # seconds per request

_SESSION = requests.Session()
_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
)
_SESSION.mount("https://", HTTPAdapter(max_retries=_RETRY_STRATEGY))


def _fetch_json(url: str) -> list:
    """GET a Census API URL, return parsed JSON list."""
    headers = {
        "User-Agent": "US Trade Analytics Streamlit App/1.0",
        "Accept": "application/json",
    }
    resp = _SESSION.get(url, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    if "json" not in content_type.lower():
        raise RuntimeError(
            f"Census API returned unexpected content type {content_type} for {url}."
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Census API returned invalid JSON for {url}: {exc}. "
            f"Response preview: {resp.text[:200]!r}"
        ) from exc


def _json_to_df(data: list, value_col: str, raw_value_col: str) -> pd.DataFrame:
    """Convert Census API JSON (header row + data rows) to a tidy DataFrame."""
    if not isinstance(data, list) or len(data) < 2:
        raise RuntimeError("Census API returned unexpected JSON structure.")
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)
    df["CTY_CODE"] = pd.to_numeric(df["CTY_CODE"], errors="coerce")
    df[value_col] = pd.to_numeric(df[raw_value_col], errors="coerce").fillna(0) / 1e6  # → millions USD
    df = df.rename(columns={"CTY_NAME": "CTYNAME"})
    df["CTYNAME"] = df["CTYNAME"].astype(str)
    return df[["CTY_CODE", "CTYNAME", value_col]]


@st.cache_data(ttl=3600)
def fetch_country_trade(year: int) -> pd.DataFrame:
    """
    Fetch US export + import data for all countries for a given year.
    Returns a DataFrame with columns:
        CTYNAME, CTY_CODE, EYR, IYR, BALANCE, year
    Values are in million USD.
    Raises requests.RequestException on network failure.
    """
    exp_data = _fetch_json(_EXPORT_URL.format(year=year))
    imp_data = _fetch_json(_IMPORT_URL.format(year=year))

    exp_df = _json_to_df(exp_data, "EYR", "ALL_VAL_YR")
    imp_df = _json_to_df(imp_data, "IYR", "CNT_VAL_YR")

    # Merge on country code; outer join so no country is lost
    df = pd.merge(exp_df, imp_df[["CTY_CODE", "IYR"]], on="CTY_CODE", how="outer")
    df["EYR"] = df["EYR"].fillna(0)
    df["IYR"] = df["IYR"].fillna(0)

    # Keep only real countries (CTY_CODE 1000–8000)
    df = df[(df["CTY_CODE"] >= 1000) & (df["CTY_CODE"] <= 8000)].copy()

    df["BALANCE"] = df["EYR"] - df["IYR"]
    df["year"] = year
    df["CTY_CODE"] = df["CTY_CODE"].astype(int)

    return df.reset_index(drop=True)


def fetch_live_data(year_start: int, year_end: int) -> pd.DataFrame:
    """
    Fetch and concatenate country trade data for year_start..year_end (inclusive).
    Falls back gracefully if individual years fail.
    Returns a combined DataFrame with the same structure as country.xlsx.
    """
    frames = []
    errors = []
    for year in range(year_start, year_end + 1):
        try:
            frames.append(fetch_country_trade(year))
        except Exception as exc:
            errors.append((year, str(exc)))
            continue

    if not frames:
        error_summary = "; ".join(f"{year}: {msg}" for year, msg in errors[:3])
        raise RuntimeError(
            f"Census API returned no data for {year_start}–{year_end}. "
            f"First errors: {error_summary}. "
            "Check your internet connection or try again later."
        )

    if errors:
        st.warning(
            "Some years failed to load from Census API: "
            + "; ".join(f"{year}: {msg}" for year, msg in errors[:5])
        )

    return pd.concat(frames, ignore_index=True)
