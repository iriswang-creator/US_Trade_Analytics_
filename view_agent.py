"""
view_agent.py — Streamlit UI for the AI Trade Analyst tab (Tab 6).
Phase 3: optional custom CSV/Excel upload analysed alongside built-in data.
Layout: left control panel | right chat panel (fixed-height scroll area).
"""

import os
import re
import pandas as pd
import streamlit as st


def _fix_response(text: str) -> str:
    """Escape $ used as currency so Streamlit doesn't treat them as LaTeX."""
    return re.sub(r'\$(?=\d)', r'\\$', text)


# ── Suggested questions ───────────────────────────────────────────────────────

_SUGGESTIONS = [
    "Which country has the largest trade deficit with US in 2024?",
    "How did US-China trade change after the 2018 trade war?",
    "What is the fastest growing import category since 2020?",
    "Compare US trade with Mexico vs Canada in recent years",
]


# ── Shared file-uploader widget (also used by Tab 7) ─────────────────────────

def render_file_uploader(key_prefix: str = "tab6"):
    with st.expander("📂 Upload Your Own Dataset (optional)", expanded=False):
        st.caption(
            "Upload any CSV or Excel file. The AI will automatically "
            "detect columns and adapt its analysis to your data."
        )
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["csv", "xlsx", "xls"],
            key=f"{key_prefix}_uploader",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            try:
                df = (
                    pd.read_csv(uploaded_file)
                    if uploaded_file.name.endswith(".csv")
                    else pd.read_excel(uploaded_file)
                )
                st.session_state["uploaded_df"] = df
                st.success(
                    f"Loaded **{uploaded_file.name}** — "
                    f"{df.shape[0]:,} rows × {df.shape[1]} columns"
                )
                st.dataframe(df.head(3), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Could not read file: {e}")
                st.session_state.pop("uploaded_df", None)
    return st.session_state.get("uploaded_df")


# ── Main render function ──────────────────────────────────────────────────────

def render_tab6_ai_analyst(filters):

    # ── API key ──
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.error("API key not configured on server. Please contact administrator.")
        return

    # ── Session state init ──
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # ════════════════════════════════════════════════════
    # Two-column layout: left = controls, right = chat
    # ════════════════════════════════════════════════════
    left, right = st.columns([1, 2], gap="large")

    # ─────────────────────────────
    # LEFT: controls
    # ─────────────────────────────
    with left:
        st.markdown(
            "<div style='font-family:Syne,sans-serif;font-size:1.4rem;"
            "font-weight:800;letter-spacing:-0.02em;margin-bottom:2px;'>"
            "AI TRADE ANALYST</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:0.82rem;color:#8b8b96;margin-bottom:1.2rem;'>"
            "US Census Bureau data · 1985–2026</div>",
            unsafe_allow_html=True,
        )

        # Suggested questions
        st.markdown(
            "<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
            "text-transform:uppercase;color:#52525e;margin-bottom:0.5rem;'>"
            "Suggested Questions</div>",
            unsafe_allow_html=True,
        )
        for idx, question in enumerate(_SUGGESTIONS):
            if st.button(question, key=f"t6_sug_{idx}", use_container_width=True):
                st.session_state["t6_pending"] = question

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

        # File upload
        uploaded_df = render_file_uploader(key_prefix="tab6")
        if uploaded_df is not None:
            st.caption(
                f"Dataset active — {uploaded_df.shape[0]:,} rows. "
                "Agent will include your data in analysis."
            )

        # Clear button (only when there's history)
        if st.session_state["chat_history"]:
            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
            if st.button("Clear conversation", key="t6_clear", use_container_width=True):
                st.session_state["chat_history"] = []
                st.rerun()

    # ─────────────────────────────
    # RIGHT: chat
    # ─────────────────────────────
    with right:
        # Fixed-height scrollable chat history container
        chat_container = st.container(height=520, border=False)
        with chat_container:
            if not st.session_state["chat_history"]:
                st.markdown(
                    "<div style='height:200px;display:flex;align-items:center;"
                    "justify-content:center;color:#3f3f46;font-size:0.88rem;'>"
                    "Ask a question to get started</div>",
                    unsafe_allow_html=True,
                )
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)
                    if msg["role"] == "assistant":
                        st.caption("Based on U.S. Census Bureau data")

        # Handle pending question from suggestion buttons
        pending = st.session_state.pop("t6_pending", None)

        # Chat input — sits directly below the history container
        user_input = st.chat_input("Ask about US trade data…") or pending

        if user_input:
            # Append user message and rerun so it shows in the container
            st.session_state["chat_history"].append(
                {"role": "user", "content": user_input}
            )

            with st.spinner("Analyzing trade data…"):
                try:
                    from agent import run_agent
                    answer = _fix_response(
                        run_agent(user_input, api_key, uploaded_df=uploaded_df)
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "401" in err_msg or "authentication" in err_msg.lower():
                        answer = "Invalid API key. Please contact administrator."
                    elif "429" in err_msg or "rate_limit" in err_msg.lower():
                        answer = "Rate limit reached. Please wait a moment and try again."
                    else:
                        answer = f"An error occurred: {err_msg}"

            st.session_state["chat_history"].append(
                {"role": "assistant", "content": answer}
            )
            st.rerun()
