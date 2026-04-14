"""
agent.py — ReACT-style AI trade analyst using the Anthropic SDK tool-use API.
No LangChain agent framework needed. Call run_agent(question, api_key).
"""

import os
import json
import pandas as pd
from functools import lru_cache

import anthropic

# ── Data paths ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")


# ── Cached data loaders ───────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_country():
    df = pd.read_excel(os.path.join(_DATA, "country.xlsx"))
    df = df[df["CTY_CODE"] > 1000].copy()
    df["BALANCE"] = df["EYR"] - df["IYR"]
    df["CTYNAME"] = df["CTYNAME"].astype(str)
    return df


@lru_cache(maxsize=1)
def _load_enduse():
    exp = pd.read_excel(
        os.path.join(_DATA, "enduse_exports.xlsx"),
        sheet_name="Enduse Exports",
    )
    imp = pd.read_excel(
        os.path.join(_DATA, "enduse_imports.xlsx"),
        sheet_name="EnduseImp",
    )
    year_cols_exp = [c for c in exp.columns if c.startswith("value_")]
    year_cols_imp = [c for c in imp.columns if c.startswith("value_")]

    exp_long = exp.melt(
        id_vars=["CTY_CODE", "CTY_DESC", "END_USE", "COMM_DESC"],
        value_vars=year_cols_exp,
        var_name="year_code",
        value_name="export_value",
    )
    imp_long = imp.melt(
        id_vars=["CTY_CODE", "CTY_DESC", "END_USE", "COMM_DESC"],
        value_vars=year_cols_imp,
        var_name="year_code",
        value_name="import_value",
    )
    exp_long["year_code"] = exp_long["year_code"].astype(str)
    imp_long["year_code"] = imp_long["year_code"].astype(str)
    exp_long["year"] = exp_long["year_code"].str.replace("value_", "20").astype(int)
    imp_long["year"] = imp_long["year_code"].str.replace("value_", "20").astype(int)
    exp_long["COMM_DESC"] = exp_long["COMM_DESC"].astype(str)
    imp_long["COMM_DESC"] = imp_long["COMM_DESC"].astype(str)
    exp_long["END_USE"] = exp_long["END_USE"].astype(str)
    imp_long["END_USE"] = imp_long["END_USE"].astype(str)
    return exp_long, imp_long


# ── Tool implementations ──────────────────────────────────────────────────────

def _query_country_data(country: str, country2: str = None,
                        year_start: int = 1985, year_end: int = 2026) -> str:
    df = _load_country()

    def find_country(name: str):
        name_lower = name.strip().lower()
        # Convert to string first before using .str methods
        df["CTYNAME"] = df["CTYNAME"].astype(str)
        matches = df[df["CTYNAME"].str.lower().str.contains(name_lower, na=False)]
        if matches.empty:
            return None, name
        canonical = matches["CTYNAME"].iloc[0]
        subset = matches[matches["year"].between(year_start, year_end)].sort_values("year")
        return subset, canonical

    results = []
    for cname in ([country, country2] if country2 else [country]):
        if not cname:
            continue
        subset, canonical = find_country(cname)
        if subset is None or subset.empty:
            results.append(f"No data found for '{cname}'.")
            continue

        latest = subset.iloc[-1]
        latest_yr = int(latest["year"])

        prev = subset[subset["year"] == latest_yr - 1]
        if not prev.empty:
            p = prev.iloc[0]
            yoy_exp = ((latest["EYR"] - p["EYR"]) / p["EYR"] * 100) if p["EYR"] else 0
            yoy_imp = ((latest["IYR"] - p["IYR"]) / p["IYR"] * 100) if p["IYR"] else 0
            yoy_str = f"  YoY exports: {yoy_exp:+.1f}%  |  YoY imports: {yoy_imp:+.1f}%\n"
        else:
            yoy_str = ""

        first = subset.iloc[0]
        first_yr = int(first["year"])

        block = (
            f"=== {canonical} ({year_start}–{year_end}) ===\n"
            f"Latest year ({latest_yr}):\n"
            f"  US Exports to {canonical}:   ${latest['EYR']:,.0f}M\n"
            f"  US Imports from {canonical}: ${latest['IYR']:,.0f}M\n"
            f"  Trade Balance:              ${latest['BALANCE']:+,.0f}M "
            f"({'surplus' if latest['BALANCE'] >= 0 else 'deficit'})\n"
            f"{yoy_str}"
            f"Range start ({first_yr}):\n"
            f"  Exports: ${first['EYR']:,.0f}M  |  Imports: ${first['IYR']:,.0f}M  "
            f"|  Balance: ${first['BALANCE']:+,.0f}M\n"
            "Year-by-year data:\n"
        )
        for _, row in subset.iterrows():
            block += (
                f"  {int(row['year'])}: Exp=${row['EYR']:,.0f}M  "
                f"Imp=${row['IYR']:,.0f}M  Bal=${row['BALANCE']:+,.0f}M\n"
            )
        results.append(block)

    return "\n".join(results) if results else "No matching data found."


def _query_product_data(product: str = "", year_start: int = 2016,
                        year_end: int = 2025, top_n: int = 5) -> str:
    exp_long, imp_long = _load_enduse()
    world_exp = exp_long[exp_long["CTY_CODE"] == 0]
    world_imp = imp_long[imp_long["CTY_CODE"] == 0]

    if not product or product.lower() in ("top", "all", ""):
        latest_yr = min(year_end, 2025)
        agg_exp = world_exp[world_exp["year"] == latest_yr].groupby("COMM_DESC")["export_value"].sum()
        agg_imp = world_imp[world_imp["year"] == latest_yr].groupby("COMM_DESC")["import_value"].sum()
        combined = pd.DataFrame({"exports": agg_exp, "imports": agg_imp}).fillna(0)
        top = combined.nlargest(top_n, "imports")
        lines = [f"Top {top_n} import categories in {latest_yr}:"]
        for rank, (comm, row) in enumerate(top.iterrows(), 1):
            lines.append(
                f"  {rank}. {comm}: Imports=${row['imports']:,.0f}M  "
                f"Exports=${row['exports']:,.0f}M  "
                f"Balance=${row['exports']-row['imports']:+,.0f}M"
            )
        return "\n".join(lines)

    keyword = product.lower()
    matched_exp = world_exp[world_exp["COMM_DESC"].str.lower().str.contains(keyword, na=False)]
    matched_imp = world_imp[world_imp["COMM_DESC"].str.lower().str.contains(keyword, na=False)]
    if matched_exp.empty and matched_imp.empty:
        matched_exp = world_exp[world_exp["END_USE"].str.lower().str.contains(keyword, na=False)]
        matched_imp = world_imp[world_imp["END_USE"].str.lower().str.contains(keyword, na=False)]
    if matched_exp.empty:
        return f"No product data found matching '{product}'. Try: 'semiconductor', 'automotive', 'food', 'aircraft'."

    exp_yr = matched_exp[matched_exp["year"].between(year_start, year_end)].groupby("year")["export_value"].sum()
    imp_yr = matched_imp[matched_imp["year"].between(year_start, year_end)].groupby("year")["import_value"].sum()

    commodities = sorted(matched_exp["COMM_DESC"].unique())
    commodity_str = ", ".join(commodities[:5])
    if len(commodities) > 5:
        commodity_str += f" ... (+{len(commodities)-5} more)"

    lines = [
        f"=== Product: '{product}' ({year_start}–{year_end}) ===",
        f"Matched categories: {commodity_str}",
        "Year-by-year (exports / imports / balance):",
    ]
    all_years = sorted(set(exp_yr.index) | set(imp_yr.index))
    for yr in all_years:
        exp_val = exp_yr.get(yr, 0)
        imp_val = imp_yr.get(yr, 0)
        lines.append(f"  {yr}: Exp=${exp_val:,.0f}M  Imp=${imp_val:,.0f}M  Bal=${exp_val-imp_val:+,.0f}M")

    if len(all_years) >= 2:
        imp_first = imp_yr.get(all_years[0], 0)
        imp_last  = imp_yr.get(all_years[-1], 0)
        if imp_first > 0:
            pct = (imp_last - imp_first) / imp_first * 100
            lines.append(f"Import trend ({all_years[0]}→{all_years[-1]}): {'UP' if pct > 0 else 'DOWN'} {abs(pct):.1f}%")

    return "\n".join(lines)


def _get_rankings(type: str = "deficit", year: int = 2024, top_n: int = 10) -> str:
    df = _load_country()
    df_yr = df[df["year"] == year].copy()
    if df_yr.empty:
        year = min(df["year"].unique(), key=lambda y: abs(y - year))
        df_yr = df[df["year"] == year].copy()

    skip = ["World", "Total", "NAFTA", "OPEC", "Pacific",
            "Europe", "Africa", "America", "Asia", "Union", "Advanced", "Developing"]
    # Convert to string first before using .str methods
    df_yr["CTYNAME"] = df_yr["CTYNAME"].astype(str)
    df_yr = df_yr[~df_yr["CTYNAME"].str.contains("|".join(skip), case=False, na=False)]
    df_yr = df_yr.dropna(subset=["BALANCE"])

    rank_type = type.lower()
    if rank_type == "surplus":
        ranked = df_yr.nlargest(top_n, "BALANCE")
        title = f"Top {top_n} US Trade Surplus Partners — {year}"
        value_col, sign = "BALANCE", "surplus"
    elif rank_type == "total":
        df_yr["TOTAL"] = df_yr["EYR"] + df_yr["IYR"]
        ranked = df_yr.nlargest(top_n, "TOTAL")
        title = f"Top {top_n} US Trading Partners (Total Volume) — {year}"
        value_col, sign = "TOTAL", "total trade"
    else:
        ranked = df_yr.nsmallest(top_n, "BALANCE")
        title = f"Top {top_n} US Trade Deficit Partners — {year}"
        value_col, sign = "BALANCE", "deficit"

    lines = [title]
    for rank, (_, row) in enumerate(ranked.iterrows(), 1):
        val = row[value_col]
        lines.append(
            f"  {rank:2d}. {row['CTYNAME']:<30s}  "
            f"{sign}=${abs(val):>10,.0f}M  "
            f"(Exp=${row['EYR']:,.0f}M / Imp=${row['IYR']:,.0f}M)"
        )
    return "\n".join(lines)


# ── Tool 4: Query user-uploaded DataFrame ────────────────────────────────────

def _query_uploaded_data(df: "pd.DataFrame", operation: str,
                         column: str = None, value: str = None,
                         agg_column: str = None, agg_func: str = "sum",
                         top_n: int = 20) -> str:
    """Safe, structured operations on a user-uploaded DataFrame."""
    try:
        if operation == "schema":
            lines = [f"Shape: {df.shape[0]} rows × {df.shape[1]} columns", "Columns:"]
            for col in df.columns:
                n_unique = df[col].nunique()
                lines.append(f"  {col!r}: {df[col].dtype}  ({n_unique} unique values)")
            lines.append("\nSample (first 5 rows):")
            lines.append(df.head(5).to_string(index=False))
            return "\n".join(lines)

        elif operation == "describe":
            return df.describe(include="all").to_string()

        elif operation == "filter":
            if column not in df.columns:
                return f"Column '{column}' not found. Available: {list(df.columns)}"
            mask = df[column].astype(str).str.lower().str.contains(
                str(value).lower(), na=False
            )
            result = df[mask].head(top_n)
            return f"Found {mask.sum()} rows where {column!r} contains '{value}':\n{result.to_string(index=False)}"

        elif operation == "groupby":
            if column not in df.columns:
                return f"Column '{column}' not found."
            if agg_column not in df.columns:
                return f"Aggregation column '{agg_column}' not found."
            result = (
                df.groupby(column)[agg_column]
                .agg(agg_func)
                .reset_index()
                .sort_values(agg_column, ascending=False)
                .head(top_n)
            )
            return f"Group by {column!r}, {agg_func}({agg_column!r}):\n{result.to_string(index=False)}"

        elif operation == "top":
            if column not in df.columns:
                return f"Column '{column}' not found."
            result = df.nlargest(top_n, column)
            return f"Top {top_n} rows by {column!r}:\n{result.to_string(index=False)}"

        elif operation == "timeseries":
            # Group by a year/date column, sum a value column
            if column not in df.columns:
                return f"Time column '{column}' not found."
            if agg_column not in df.columns:
                return f"Value column '{agg_column}' not found."
            result = (
                df.groupby(column)[agg_column]
                .sum()
                .reset_index()
                .sort_values(column)
            )
            return f"Time series — {agg_column!r} by {column!r}:\n{result.to_string(index=False)}"

        else:
            return (
                f"Unknown operation '{operation}'. "
                "Use: schema, describe, filter, groupby, top, timeseries"
            )
    except Exception as e:
        return f"Error executing '{operation}': {e}"


# ── Tool dispatch ─────────────────────────────────────────────────────────────

def _dispatch(tool_name: str, tool_input: dict, uploaded_df=None) -> str:
    if tool_name == "query_country_data":
        return _query_country_data(**tool_input)
    elif tool_name == "query_product_data":
        return _query_product_data(**tool_input)
    elif tool_name == "get_rankings":
        return _get_rankings(**tool_input)
    elif tool_name == "query_uploaded_data" and uploaded_df is not None:
        return _query_uploaded_data(uploaded_df, **tool_input)
    return f"Unknown tool: {tool_name}"


# ── Tool schemas for the Anthropic API ───────────────────────────────────────

_TOOLS = [
    {
        "name": "query_country_data",
        "description": (
            "Query US trade data (exports, imports, balance, YoY change) "
            "for one or two countries over a year range. "
            "Values are in million USD. Data covers 1985–2026."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "country":    {"type": "string",  "description": "Country name, e.g. 'China'"},
                "country2":   {"type": "string",  "description": "Second country for comparison (optional)"},
                "year_start": {"type": "integer", "description": "Start year (default 1985)"},
                "year_end":   {"type": "integer", "description": "End year (default 2026)"},
            },
            "required": ["country"],
        },
    },
    {
        "name": "query_product_data",
        "description": (
            "Query US trade data by product/commodity category. "
            "Data covers 2016–2025 only. Returns export value, import value, "
            "balance, and trend. Leave product empty to get top N import categories."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product":    {"type": "string",  "description": "Commodity keyword, e.g. 'semiconductor'"},
                "year_start": {"type": "integer", "description": "Start year (default 2016)"},
                "year_end":   {"type": "integer", "description": "End year (default 2025)"},
                "top_n":      {"type": "integer", "description": "How many top categories (default 5)"},
            },
            "required": [],
        },
    },
    {
        "name": "get_rankings",
        "description": (
            "Get a ranked list of US trading partners by surplus, deficit, "
            "or total trade volume for a specific year."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type":  {"type": "string",  "description": "'surplus', 'deficit', or 'total'"},
                "year":  {"type": "integer", "description": "Year to rank (default 2024)"},
                "top_n": {"type": "integer", "description": "How many countries to return (default 10)"},
            },
            "required": ["type"],
        },
    },
]

_UPLOADED_DATA_TOOL = {
    "name": "query_uploaded_data",
    "description": (
        "Query the user-uploaded custom dataset. Use this tool to explore and "
        "analyze data the user has provided. Always call with operation='schema' "
        "first to understand the columns before running other operations."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": (
                    "'schema' — show columns & sample rows; "
                    "'describe' — summary statistics; "
                    "'filter' — filter rows by column value; "
                    "'groupby' — group by column, aggregate another; "
                    "'top' — top N rows by a numeric column; "
                    "'timeseries' — sum a value column grouped by a time column"
                ),
            },
            "column":     {"type": "string", "description": "Primary column to operate on"},
            "value":      {"type": "string", "description": "Filter value (for 'filter' operation)"},
            "agg_column": {"type": "string", "description": "Column to aggregate (for 'groupby'/'timeseries')"},
            "agg_func":   {"type": "string", "description": "Aggregation function: sum, mean, count, max, min"},
            "top_n":      {"type": "integer", "description": "Max rows to return (default 20)"},
        },
        "required": ["operation"],
    },
}

_SYSTEM = (
    "You are a US trade data analyst with access to official U.S. Census Bureau "
    "trade data from 1985 to 2026.\n\n"
    "IMPORTANT FORMATTING RULES:\n"
    "- Always use plain text, never LaTeX or math notation\n"
    "- Write numbers like: $295.5 billion (not $295.5B or mathematical notation)\n"
    "- Never use $...$ for dollar amounts in text\n"
    "- Use simple bullet points with -\n"
    "- Keep bold text minimal, only for key findings\n"
    "- Write in flowing paragraphs, not fragmented sentences\n"
    "- Never put a line break between a bold word and its surrounding sentence\n\n"
    "Always answer with specific numbers from the data. "
    "Keep answers concise but informative."
)


# ── Public API ────────────────────────────────────────────────────────────────

def run_agent(question: str, api_key: str, uploaded_df=None) -> str:
    """Run the ReACT trade analyst agent and return a plain-text answer.

    Args:
        question:    Natural-language question about trade data.
        api_key:     Anthropic API key.
        uploaded_df: Optional user-uploaded pandas DataFrame for Phase 3.
    """
    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": question}]

    active_tools = list(_TOOLS)
    system = _SYSTEM
    if uploaded_df is not None:
        active_tools.append(_UPLOADED_DATA_TOOL)
        system = (
            _SYSTEM
            + "\n\nThe user has also uploaded a custom dataset. "
            "Use the query_uploaded_data tool to explore it. "
            "Start with operation='schema' to understand the columns."
        )

    for _ in range(5):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # 最便宜，速度最快
            max_tokens=2048,
            system=system,
            tools=active_tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "No answer returned."

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _dispatch(block.name, block.input, uploaded_df)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return "Agent reached maximum iterations without a final answer."
