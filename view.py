import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

TRADE_EVENTS = {
    2001: "China joins WTO",
    2008: "Financial Crisis",
    2018: "US-China Trade War",
    2020: "COVID-19",
    2022: "Russia-Ukraine War",
}

# ════════════════════════════════════════════════════
# 資料載入（用 @st.cache_data 快取，只讀一次）
# ════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def load_country_data(data_source: str = "local"):
    """Load country trade data from local Excel or live Census Bureau API."""
    if data_source == "live":
        try:
            from census_api import fetch_live_data
            with st.spinner("Fetching live data from Census Bureau API…"):
                df = fetch_live_data(2013, 2024)
        except Exception as e:
            st.warning(
                f"Live API unavailable ({e}). "
                "Falling back to local data automatically."
            )
            df = pd.read_excel("data/country.xlsx")
            df = df[df["CTY_CODE"] > 1000].copy()
            df["BALANCE"] = df["EYR"] - df["IYR"]
    else:
        df = pd.read_excel("data/country.xlsx")
        df = df[df["CTY_CODE"] > 1000].copy()
        df["BALANCE"] = df["EYR"] - df["IYR"]
    df["CTYNAME"] = df["CTYNAME"].astype(str)
    return df

@st.cache_data
def load_enduse_data():
    """讀取出口/進口商品數據，轉成長格式方便繪圖"""
    exp = pd.read_excel("data/enduse_exports.xlsx", sheet_name="Enduse Exports")
    imp = pd.read_excel("data/enduse_imports.xlsx", sheet_name="EnduseImp")

    # 把 value_16, value_17... 這種欄位轉成 year, value 兩欄（長格式）
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

    # 把 "value_23" 轉成 2023 這樣的整數年份
    exp_long["year"] = exp_long["year_code"].str.replace("value_", "20").astype(int)
    imp_long["year"] = imp_long["year_code"].str.replace("value_", "20").astype(int)

    return exp_long, imp_long


# ════════════════════════════════════════════════════
# 主函式：把五個 tab 的內容全部填入
# ════════════════════════════════════════════════════

def render_view(tab1, tab2, tab3, tab4, tab5, filters):
    data_source = "live" if "Live" in filters.get("data_source", "") else "local"
    df_country = load_country_data(data_source)
    exp_long, imp_long = load_enduse_data()

    render_tab1_world_map(tab1, df_country, filters)
    render_tab2_bilateral(tab2, df_country, filters)
    render_tab3_product_trend(tab3, exp_long, imp_long, filters)
    render_tab4_trade_balance(tab4, df_country, filters)
    render_tab5_time_machine(tab5, df_country, filters)


# ════════════════════════════════════════════════════
# TAB 1：世界地圖熱力圖
# ════════════════════════════════════════════════════

def render_tab1_world_map(tab, df, filters):
    with tab:
        # [Feature 1] unit
        unit_divisor = filters["unit_divisor"]
        unit_label   = filters["unit_label"]

        st.subheader("US Trade Snapshot — 2024")
        st.caption("A fixed snapshot of 2024. To explore other years, see the Historical Evolution tab.")
        st.caption(f"Color intensity = total trade (exports + imports) in {unit_label}")

        # 取 2024 年資料，計算總貿易量
        df_2024 = df[df["year"] == 2024].copy()
        df_2024["TOTAL_TRADE"] = (df_2024["IYR"] + df_2024["EYR"]) / unit_divisor
        df_2024["EYR"] = df_2024["EYR"] / unit_divisor
        df_2024["IYR"] = df_2024["IYR"] / unit_divisor

        # 用 Plotly 畫世界地圖（choropleth 需要國家名稱）
        fig = px.choropleth(
            df_2024,
            locations="CTYNAME",           # 國家名稱欄位
            locationmode="country names",   # 用名稱對應地圖
            color="TOTAL_TRADE",            # 顏色深淺 = 貿易量
            hover_name="CTYNAME",
            hover_data={
                "TOTAL_TRADE": ":,.2f",
                "EYR": ":,.2f",
                "IYR": ":,.2f",
            },
            color_continuous_scale="Blues", # 藍色漸層，可改成 "Viridis", "Reds" 等
            labels={
                "TOTAL_TRADE": f"Total Trade ({unit_label})",
                "EYR": f"Exports ({unit_label})",
                "IYR": f"Imports ({unit_label})",
            },
            title="US Total Trade by Partner Country — 2024",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(title=unit_label),
            height=520,
        )
        st.plotly_chart(fig, use_container_width=True)

        # 顯示前 5 名摘要指標
        top5 = df_2024.nlargest(5, "TOTAL_TRADE")[["CTYNAME", "TOTAL_TRADE", "EYR", "IYR"]].copy()
        st.markdown("#### Top 5 Trading Partners (2024)")

        def fmt(val):
            if unit_divisor == 1000:
                return f"${val:.2f}B"
            else:
                return f"${val/1000:.1f}M" if val >= 1000 else f"${val:.1f}M"

        top5.insert(0, "Rank", range(1, 6))
        top5["Total Trade"] = top5["TOTAL_TRADE"].apply(fmt)
        top5["Exports"]     = top5["EYR"].apply(fmt)
        top5["Imports"]     = top5["IYR"].apply(fmt)
        st.dataframe(
            top5[["Rank", "CTYNAME", "Total Trade", "Exports", "Imports"]].rename(columns={"CTYNAME": "Country"}),
            hide_index=True,
            use_container_width=True,
        )


# ════════════════════════════════════════════════════
# TAB 2：兩國貿易流向比較
# ════════════════════════════════════════════════════

def render_tab2_bilateral(tab, df, filters):
    with tab:
        yr_start, yr_end = filters["year_range"]
        # [Feature 1] unit
        unit_divisor  = filters["unit_divisor"]
        unit_label    = filters["unit_label"]
        # [Feature 2] preset
        preset_a      = filters["preset_country_a"]
        preset_b      = filters["preset_country_b"]
        is_preset     = preset_a is not None

        country_list = sorted(df["CTYNAME"].dropna().unique())
        default_a = country_list.index(preset_a) if is_preset and preset_a in country_list else (country_list.index("China") if "China" in country_list else 0)
        default_b = country_list.index(preset_b) if is_preset and preset_b in country_list else (country_list.index("Canada") if "Canada" in country_list else 1)

        col_a, col_b = st.columns(2)
        with col_a:
            country_a = st.selectbox(
                "Country A", options=country_list, index=default_a, disabled=is_preset,
            )
        with col_b:
            country_b = st.selectbox(
                "Country B", options=country_list, index=default_b, disabled=is_preset,
            )
        # When preset is active, enforce the preset values regardless of widget state
        if is_preset:
            country_a = preset_a if preset_a in country_list else country_a
            country_b = preset_b if preset_b in country_list else country_b

        st.subheader(f"US Trade: {country_a} vs {country_b}")

        # 篩選兩個國家的資料
        df_a = df[(df["CTYNAME"] == country_a) & (df["year"].between(yr_start, yr_end))].copy()
        df_b = df[(df["CTYNAME"] == country_b) & (df["year"].between(yr_start, yr_end))].copy()

        if df_a.empty or df_b.empty:
            st.warning("No data found for selected countries. Try adjusting the year range.")
            return

        # [Feature 1] apply unit divisor
        for _df in (df_a, df_b):
            _df["EYR"]     = _df["EYR"]     / unit_divisor
            _df["IYR"]     = _df["IYR"]     / unit_divisor
            _df["BALANCE"] = _df["BALANCE"] / unit_divisor

        # 左右分欄顯示
        col1, col2 = st.columns(2)

        # ── 左：出口比較 ──
        with col1:
            st.markdown(f"**Exports to {country_a} vs {country_b}**")
            fig_exp = go.Figure()
            fig_exp.add_trace(go.Bar(
                x=df_a["year"], y=df_a["EYR"],
                name=country_a, marker_color="#1a6fc4"
            ))
            fig_exp.add_trace(go.Bar(
                x=df_b["year"], y=df_b["EYR"],
                name=country_b, marker_color="#00b4d8"
            ))
            fig_exp.update_layout(
                barmode="group",
                xaxis_title="Year",
                yaxis_title=unit_label,
                height=360,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_exp, use_container_width=True)

        # ── 右：進口比較 ──
        with col2:
            st.markdown(f"**Imports from {country_a} vs {country_b}**")
            fig_imp = go.Figure()
            fig_imp.add_trace(go.Bar(
                x=df_a["year"], y=df_a["IYR"],
                name=country_a, marker_color="#e63946"
            ))
            fig_imp.add_trace(go.Bar(
                x=df_b["year"], y=df_b["IYR"],
                name=country_b, marker_color="#f4a261"
            ))
            fig_imp.update_layout(
                barmode="group",
                xaxis_title="Year",
                yaxis_title=unit_label,
                height=360,
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig_imp, use_container_width=True)

        # ── 貿易差額折線圖 ──
        st.markdown("**Trade Balance Comparison (Exports − Imports)**")
        fig_bal = go.Figure()
        fig_bal.add_trace(go.Scatter(
            x=df_a["year"], y=df_a["BALANCE"],
            name=country_a, mode="lines+markers",
            line=dict(color="#1a6fc4", width=2),
        ))
        fig_bal.add_trace(go.Scatter(
            x=df_b["year"], y=df_b["BALANCE"],
            name=country_b, mode="lines+markers",
            line=dict(color="#e63946", width=2, dash="dot"),
        ))
        fig_bal.add_hline(y=0, line_color="gray", line_dash="dash", line_width=1)
        for year, label in TRADE_EVENTS.items():
            if yr_start <= year <= yr_end:
                fig_bal.add_vline(
                    x=year,
                    line_dash="dot",
                    line_color="rgba(255,255,255,0.3)",
                    line_width=1,
                    annotation_text=label,
                    annotation_position="top right",
                    annotation_textangle=90,
                    annotation_font_size=10,
                    annotation_font_color="rgba(255,255,255,0.8)",
                )
        fig_bal.update_layout(
            xaxis_title="Year",
            yaxis_title=unit_label,
            height=320,
        )
        st.plotly_chart(fig_bal, use_container_width=True)


# ════════════════════════════════════════════════════
# TAB 3：商品趨勢折線圖
# ════════════════════════════════════════════════════

def render_tab3_product_trend(tab, exp_long, imp_long, filters):
    with tab:
        st.info(
            "**Data availability:** Product-level trade data is "
            "available from **2016 to 2025** only. "
            "The year range filter (sidebar) applies where data exists — "
            "selecting years before 2016 will still show from 2016 onwards."
        )
        st.subheader("US Trade by Product Category")
        yr_start, yr_end = filters["year_range"]

        # 商品選擇器（世界總量，CTY_CODE == 0）
        world_exp = exp_long[exp_long["CTY_CODE"] == 0]
        world_imp = imp_long[imp_long["CTY_CODE"] == 0]
        commodity_list = sorted(world_exp["COMM_DESC"].unique())

        selected_commodity = st.selectbox(
            "Select a commodity",
            options=commodity_list,
            index=commodity_list.index("Semiconductors") if "Semiconductors" in commodity_list else 0,
        )

        # 篩選選定商品，並套用年份範圍
        exp_data = world_exp[world_exp["COMM_DESC"] == selected_commodity]
        imp_data = world_imp[world_imp["COMM_DESC"] == selected_commodity]
        exp_data = exp_data[exp_data["year"].between(yr_start, yr_end)]
        imp_data = imp_data[imp_data["year"].between(yr_start, yr_end)]

        actual_start = int(exp_data["year"].min()) if not exp_data.empty else yr_start
        actual_end   = int(exp_data["year"].max()) if not exp_data.empty else yr_end

        # 把出口和進口合併到同一張圖
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=exp_data["year"], y=exp_data["export_value"] / 1e9,
            name="Exports", mode="lines+markers",
            line=dict(color="#1a6fc4", width=3),
            fill="tozeroy", fillcolor="rgba(26,111,196,0.1)",
        ))
        fig.add_trace(go.Scatter(
            x=imp_data["year"], y=imp_data["import_value"] / 1e9,
            name="Imports", mode="lines+markers",
            line=dict(color="#e63946", width=3),
            fill="tozeroy", fillcolor="rgba(230,57,70,0.1)",
        ))
        fig.update_layout(
            title=f"US {selected_commodity} Trade — {actual_start} to {actual_end}",
            xaxis_title="Year",
            yaxis_title="Billion USD",
            height=440,
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Showing {actual_start}–{actual_end} (product data limited to 2016–2025)")

        # 最新年份的指標
        latest_year = exp_data["year"].max()
        latest_exp = exp_data[exp_data["year"] == latest_year]["export_value"].sum() / 1e9
        latest_imp = imp_data[imp_data["year"] == latest_year]["import_value"].sum() / 1e9

        c1, c2, c3 = st.columns(3)
        c1.metric("Exports (latest year)", f"${latest_exp:.2f}B")
        c2.metric("Imports (latest year)", f"${latest_imp:.2f}B")
        c3.metric("Trade Balance", f"${latest_exp - latest_imp:.2f}B",
                  delta="Surplus" if latest_exp > latest_imp else "Deficit")
        st.caption(f"Metrics based on {yr_start}–{yr_end} average, latest year = {latest_year}")


# ════════════════════════════════════════════════════
# TAB 4：順差/逆差排行榜
# ════════════════════════════════════════════════════

def render_tab4_trade_balance(tab, df, filters):
    with tab:
        yr_start, yr_end = filters["year_range"]
        # [Feature 1] unit
        unit_divisor = filters["unit_divisor"]
        unit_label   = filters["unit_label"]

        top_n = st.radio(
            "Show top N countries", options=[10, 15, 20], index=0, horizontal=True
        )

        st.subheader(f"US Trade Balance — Top & Bottom {top_n} Partners")
        st.caption(f"Averaged over {yr_start}–{yr_end} · Green = surplus, Red = deficit")

        # 計算選定年份範圍的平均貿易差額
        df_range = df[df["year"].between(yr_start, yr_end)]
        df_avg = (
            df_range.groupby("CTYNAME")[["EYR", "IYR", "BALANCE"]]
            .mean()
            .reset_index()
        )

        # 過濾掉 NaN 和地區匯總（非真實國家）
        aggregate_keywords = ["World", "Total", "NAFTA", "OPEC", "Pacific",
                              "Europe", "Africa", "America", "Asia", "Union", "Advanced"]
        pattern = "|".join(aggregate_keywords)
        df_avg = df_avg.dropna(subset=["BALANCE"])
        df_avg = df_avg[~df_avg["CTYNAME"].str.contains(pattern, case=False, na=False)]

        # [Feature 1] apply unit divisor before ranking
        df_avg["EYR"]     = df_avg["EYR"]     / unit_divisor
        df_avg["IYR"]     = df_avg["IYR"]     / unit_divisor
        df_avg["BALANCE"] = df_avg["BALANCE"] / unit_divisor

        # 最大順差（正值）和最大逆差（負值）各取 top_n
        top_surplus = df_avg.nlargest(top_n, "BALANCE")
        top_deficit = df_avg.nsmallest(top_n, "BALANCE")

        chart_height = 300 + top_n * 18

        col1, col2 = st.columns(2)

        # ── 順差排行 ──
        with col1:
            st.markdown(f"**Largest Surpluses — Top {top_n}**")
            fig_sur = px.bar(
                top_surplus.sort_values("BALANCE"),
                x="BALANCE",
                y="CTYNAME",
                orientation="h",
                color="BALANCE",
                color_continuous_scale=[[0, "#90ee90"], [1, "#006400"]],
                labels={"BALANCE": f"Avg Balance ({unit_label})", "CTYNAME": ""},
            )
            fig_sur.update_layout(
                height=chart_height,
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_title=unit_label,
            )
            st.plotly_chart(fig_sur, use_container_width=True)

        # ── 逆差排行 ──
        with col2:
            st.markdown(f"**Largest Deficits — Top {top_n}**")
            fig_def = px.bar(
                top_deficit.sort_values("BALANCE", ascending=False),
                x="BALANCE",
                y="CTYNAME",
                orientation="h",
                color="BALANCE",
                color_continuous_scale=[[0, "#8b0000"], [1, "#ffb3b3"]],
                labels={"BALANCE": f"Avg Balance ({unit_label})", "CTYNAME": ""},
            )
            fig_def.update_layout(
                height=chart_height,
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_title=unit_label,
            )
            st.plotly_chart(fig_def, use_container_width=True)

        # ── 趨勢圖：選定幾個主要國家看差額走勢 ──
        st.markdown("**Trade Balance Trend — Selected Major Partners**")
        major = ["China", "Canada", "Mexico", "Germany", "Japan"]
        df_major = df[df["CTYNAME"].isin(major) & df["year"].between(yr_start, yr_end)].copy()
        df_major["BALANCE"] = df_major["BALANCE"] / unit_divisor
        fig_trend = px.line(
            df_major, x="year", y="BALANCE", color="CTYNAME",
            labels={"BALANCE": f"Trade Balance ({unit_label})", "year": "Year", "CTYNAME": "Country"},
            height=360,
        )
        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_trend, use_container_width=True)

        # [Feature 3] Download CSV
        st.markdown("---")
        st.markdown("#### Download Data")

        col_a, col_b = st.columns(2)

        with col_a:
            csv_surplus = top_surplus[["CTYNAME", "EYR", "IYR", "BALANCE"]].copy()
            csv_surplus.columns = ["Country", "Avg Exports", "Avg Imports", "Avg Balance"]
            st.download_button(
                label="Download Surplus Countries CSV",
                data=csv_surplus.to_csv(index=False),
                file_name="us_trade_surplus.csv",
                mime="text/csv",
            )

        with col_b:
            csv_deficit = top_deficit[["CTYNAME", "EYR", "IYR", "BALANCE"]].copy()
            csv_deficit.columns = ["Country", "Avg Exports", "Avg Imports", "Avg Balance"]
            st.download_button(
                label="Download Deficit Countries CSV",
                data=csv_deficit.to_csv(index=False),
                file_name="us_trade_deficit.csv",
                mime="text/csv",
            )

        st.markdown("---")
        st.markdown("#### Trade Relationship Map")
        st.caption(
            "Each bubble = one country · "
            "Size = total trade volume · "
            "Color = surplus (green) or deficit (red) · "
            "Diagonal line = balanced trade"
        )

        # 準備泡泡圖資料
        df_bubble = df_avg.copy()
        df_bubble["TOTAL"] = df_bubble["EYR"] + df_bubble["IYR"]
        df_bubble = df_bubble[df_bubble["TOTAL"] > 0].copy()

        # 套用單位換算
        divisor = filters.get("unit_divisor", 1)
        unit_label = filters.get("unit_label", "M USD")
        df_bubble["EYR_scaled"]     = df_bubble["EYR"]     / divisor
        df_bubble["IYR_scaled"]     = df_bubble["IYR"]     / divisor
        df_bubble["TOTAL_scaled"]   = df_bubble["TOTAL"]   / divisor
        df_bubble["BALANCE_scaled"] = df_bubble["BALANCE"] / divisor

        fig_bubble = px.scatter(
            df_bubble,
            x="EYR_scaled",
            y="IYR_scaled",
            size="TOTAL_scaled",
            color="BALANCE_scaled",
            hover_name="CTYNAME",
            hover_data={
                "EYR_scaled":     ":.1f",
                "IYR_scaled":     ":.1f",
                "BALANCE_scaled": ":.1f",
                "TOTAL_scaled":   False,
            },
            color_continuous_scale=[
                [0.0, "#8b0000"],
                [0.5, "#444444"],
                [1.0, "#006400"],
            ],
            size_max=60,
            labels={
                "EYR_scaled":     f"US Exports ({unit_label})",
                "IYR_scaled":     f"US Imports ({unit_label})",
                "BALANCE_scaled": f"Balance ({unit_label})",
                "CTYNAME":        "Country",
            },
            title=f"US Trade Relationship Map — {yr_start}–{yr_end} Average",
        )

        # 加入對角線（代表進出口平衡點）
        max_val = max(
            df_bubble["EYR_scaled"].max(),
            df_bubble["IYR_scaled"].max(),
        )
        fig_bubble.add_shape(
            type="line",
            x0=0, y0=0, x1=max_val, y1=max_val,
            line=dict(color="rgba(255,255,255,0.2)", dash="dash", width=1),
        )
        fig_bubble.add_annotation(
            x=max_val * 0.7,
            y=max_val * 0.7,
            text="Balanced trade line",
            showarrow=False,
            font=dict(size=10, color="rgba(255,255,255,0.4)"),
            textangle=-45,
        )

        fig_bubble.update_coloraxes(
            cmid=0,
            colorbar=dict(
                title=f"Balance<br>({unit_label})",
                tickformat=".0f",
            ),
        )
        fig_bubble.update_layout(
            height=520,
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        )

        top_labels = df_bubble.nlargest(8, "TOTAL_scaled")
        for _, row in top_labels.iterrows():
            fig_bubble.add_annotation(
                x=row["EYR_scaled"],
                y=row["IYR_scaled"],
                text=row["CTYNAME"],
                showarrow=False,
                font=dict(size=9, color="rgba(255,255,255,0.85)"),
                yshift=18,
            )

        st.plotly_chart(fig_bubble, use_container_width=True)
        st.caption(
            "Countries above the diagonal line = "
            "US imports more than it exports (deficit). "
            "Countries below = US surplus. "
            "Bubble size reflects total trade importance."
        )


# ════════════════════════════════════════════════════
# TAB 5：時間軸動態地圖
# ════════════════════════════════════════════════════

def render_tab5_time_machine(tab, df, filters):
    with tab:
        # [Feature 1] unit
        unit_divisor = filters["unit_divisor"]
        unit_label   = filters["unit_label"]

        st.info("Unlike the Trade Map tab, this tab lets you slide through any year from 1985 to 2024 to observe how US trade patterns shifted over time.")

        st.subheader("Historical Evolution of US Trade (1985–2024)")
        st.caption("Select a year to view the global trade map and top partners for that year.")

        time_year = st.slider(
            "Select year to display", min_value=1985, max_value=2024, value=2000
        )

        # 大標題顯示年份
        st.markdown(f"<h2 style='text-align:center; color:#1a6fc4;'>{time_year}</h2>",
                    unsafe_allow_html=True)

        # 顯示選定年份的地圖
        df_year = df[df["year"] == time_year].copy()
        df_year["TOTAL_TRADE"] = (df_year["IYR"] + df_year["EYR"]) / unit_divisor
        df_year["EYR"]         = df_year["EYR"]     / unit_divisor
        df_year["IYR"]         = df_year["IYR"]     / unit_divisor
        df_year["BALANCE"]     = df_year["BALANCE"] / unit_divisor

        fig = px.choropleth(
            df_year,
            locations="CTYNAME",
            locationmode="country names",
            color="TOTAL_TRADE",
            hover_name="CTYNAME",
            hover_data={
                "TOTAL_TRADE": ":,.2f",
                "EYR": ":,.2f",
                "IYR": ":,.2f",
                "BALANCE": ":,.2f",
            },
            color_continuous_scale="YlOrRd", # 黃→橘→紅，跟 Blues 不同讓 tab5 有特色
            labels={"TOTAL_TRADE": f"Total Trade ({unit_label})"},
            title=f"US Total Trade with the World — {time_year}",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=40, b=0),
            height=500,
            coloraxis_colorbar=dict(title=unit_label),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 顯示該年度前 3 大夥伴
        top3 = df_year.nlargest(3, "TOTAL_TRADE")[["CTYNAME", "TOTAL_TRADE", "BALANCE"]]
        st.markdown(f"#### {time_year} — Top 3 Trading Partners")
        c1, c2, c3 = st.columns(3)
        for col, (_, row) in zip([c1, c2, c3], top3.iterrows()):
            balance_str = f"${row['BALANCE']:+,.2f} {unit_label}"
            col.metric(
                label=row["CTYNAME"],
                value=f"${row['TOTAL_TRADE']:,.2f} {unit_label}",
                delta=balance_str,
            )

        # 歷年美國總貿易量趨勢（用折線圖）
        st.markdown("#### US Total Trade Volume — All Years")
        world_trend = df.groupby("year")[["EYR", "IYR"]].sum().reset_index()
        world_trend["TOTAL"] = world_trend["EYR"] + world_trend["IYR"]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=world_trend["year"], y=world_trend["TOTAL"] / unit_divisor,
            fill="tozeroy", mode="lines",
            line=dict(color="#1a6fc4", width=2),
            fillcolor="rgba(26,111,196,0.15)",
            name="Total Trade",
        ))
        # 在圖上標記使用者選的年份
        selected_val = world_trend[world_trend["year"] == time_year]["TOTAL"]
        if not selected_val.empty:
            fig2.add_vline(
                x=time_year, line_dash="dash",
                line_color="#e63946", line_width=2,
                annotation_text=f"  {time_year}",
                annotation_position="top right",
            )
        for year, label in TRADE_EVENTS.items():
            fig2.add_vline(
                x=year,
                line_dash="dot",
                line_color="rgba(255,255,255,0.3)",
                line_width=1,
                annotation_text=label,
                annotation_position="top right",
                annotation_textangle=90,
                annotation_font_size=10,
                annotation_font_color="rgba(255,255,255,0.5)",
            )
        fig2.update_layout(
            xaxis_title="Year",
            yaxis_title=unit_label,
            height=280,
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "Dotted lines mark major global events: "
            "WTO accession (2001), Financial Crisis (2008), "
            "US-China Trade War (2018), COVID-19 (2020), "
            "Russia-Ukraine War (2022)"
        )
