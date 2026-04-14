"""
view_multi_agent.py — Phase 4 Multi-Agent Architecture UI (Tab 7).
Layout: left control panel | right chat panel (fixed-height scroll area).
"""

import os
import re
import streamlit as st
from view_agent import render_file_uploader, _fix_response

# ── Suggested questions ───────────────────────────────────────────────────────

_SUGGESTIONS = [
    "Give me a full trade report on US-China relations from 2018 to 2024",
    "What if the US imposed a 50% tariff on all Chinese goods tomorrow?",
    "Analyse US semiconductor trade trends and project the next 3 years",
    "What would happen to US trade if USMCA were renegotiated unfavourably?",
]


# ── Agent badge helper ────────────────────────────────────────────────────────

def _agent_badge(icon: str, name: str, accent: str) -> str:
    return (
        f"<span style='display:inline-flex;align-items:center;gap:6px;"
        f"background:{accent}18;border:1px solid {accent}40;"
        f"border-radius:6px;padding:3px 10px;font-size:0.78rem;"
        f"font-weight:600;color:{accent};'>{icon} {name}</span>"
    )


_AGENT_COLORS = {
    "Query Agent":   ("#5b8dee", "🔍"),
    "Report Agent":  ("#22c55e", "📊"),
    "What-If Agent": ("#f59e0b", "🔮"),
}


# ── Activity log renderer ─────────────────────────────────────────────────────

def _render_activity_log(activity_log: list):
    if not activity_log:
        return
    st.markdown(
        "<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
        "text-transform:uppercase;color:#52525e;margin:1rem 0 0.4rem;'>"
        "Agent Activity Log</div>",
        unsafe_allow_html=True,
    )
    for i, step in enumerate(activity_log, 1):
        agent_name = step["agent"]
        color, icon = _AGENT_COLORS.get(agent_name, ("#8b8b96", "🤖"))
        badge = _agent_badge(icon, agent_name, color)
        with st.expander(f"Step {i} — {agent_name}", expanded=False):
            st.markdown(badge, unsafe_allow_html=True)
            st.markdown(
                "<div style='font-size:0.78rem;color:#8b8b96;margin:0.5rem 0 0.2rem;'>Input</div>",
                unsafe_allow_html=True,
            )
            st.info(step["input"])
            st.markdown(
                "<div style='font-size:0.78rem;color:#8b8b96;margin:0.5rem 0 0.2rem;'>Output</div>",
                unsafe_allow_html=True,
            )
            output = step["output"]
            # Markdown output (Report/What-If agents use ## headers)
            if "##" in output or output.strip().startswith("#"):
                st.markdown(_fix_response(output), unsafe_allow_html=True)
            else:
                # Plain-text data from Query Agent — preserve newlines and indentation
                st.code(output, language=None)


# ── Architecture diagram (pure HTML — avoids nested columns bug) ──────────────

def _render_arch_diagram():
    def badge(icon, name, color):
        return (
            f"<span style='display:inline-flex;align-items:center;gap:5px;"
            f"background:{color}18;border:1px solid {color}40;border-radius:6px;"
            f"padding:4px 10px;font-size:0.76rem;font-weight:600;color:{color};'>"
            f"{icon} {name}</span>"
        )
    arrow = "<span style='color:#52525e;font-size:1rem;margin:0 8px;'>→</span>"
    specialists = (
        f"<div style='display:inline-flex;flex-direction:column;gap:5px;vertical-align:middle;'>"
        f"{badge('🔍','Query Agent','#5b8dee')}"
        f"{badge('📊','Report Agent','#22c55e')}"
        f"{badge('🔮','What-If Agent','#f59e0b')}"
        f"</div>"
    )
    html = (
        f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:4px;"
        f"margin-bottom:1rem;'>"
        f"{badge('🧠','Orchestrator','#a855f7')}"
        f"{arrow}"
        f"{specialists}"
        f"{arrow}"
        f"{badge('✅','Final Answer','#22c55e')}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Main render function ──────────────────────────────────────────────────────

def render_tab7_multi_agent(filters):

    # ── API key ──
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.error("API key not configured on server. Please contact administrator.")
        return

    # ── Session state init ──
    if "ma_chat_history" not in st.session_state:
        st.session_state["ma_chat_history"] = []

    # ── Header + arch diagram (outside columns to avoid nested-columns bug) ──
    st.markdown(
        "<div style='font-family:Syne,sans-serif;font-size:1.4rem;"
        "font-weight:800;letter-spacing:-0.02em;margin-bottom:2px;'>"
        "MULTI-AGENT ANALYST</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.82rem;color:#8b8b96;margin-bottom:0.8rem;'>"
        "Orchestrator · Query · Report · What-If</div>",
        unsafe_allow_html=True,
    )
    _render_arch_diagram()

    # ════════════════════════════════════════════════════
    # Two-column layout: left = controls, right = chat
    # ════════════════════════════════════════════════════
    left, right = st.columns([1, 2], gap="large")

    # ─────────────────────────────
    # LEFT: controls
    # ─────────────────────────────
    with left:
        # Suggested questions
        st.markdown(
            "<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
            "text-transform:uppercase;color:#52525e;margin-bottom:0.5rem;'>"
            "Deep-Analysis Questions</div>",
            unsafe_allow_html=True,
        )
        for idx, question in enumerate(_SUGGESTIONS):
            if st.button(question, key=f"t7_sug_{idx}", use_container_width=True):
                st.session_state["t7_pending"] = question

        st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

        # File upload
        uploaded_df = render_file_uploader(key_prefix="tab7")
        if uploaded_df is not None:
            st.caption(
                f"Dataset active — {uploaded_df.shape[0]:,} rows. "
                "Query Agent will include your data."
            )

        # Clear button
        if st.session_state["ma_chat_history"]:
            st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)
            if st.button("Clear conversation", key="t7_clear", use_container_width=True):
                st.session_state["ma_chat_history"] = []
                st.rerun()

    # ─────────────────────────────
    # RIGHT: chat
    # ─────────────────────────────
    with right:
        # Fixed-height scrollable chat history container
        chat_container = st.container(height=520, border=False)
        with chat_container:
            if not st.session_state["ma_chat_history"]:
                st.markdown(
                    "<div style='height:200px;display:flex;align-items:center;"
                    "justify-content:center;color:#3f3f46;font-size:0.88rem;'>"
                    "Ask a question for deep multi-agent analysis</div>",
                    unsafe_allow_html=True,
                )
            for msg_idx, msg in enumerate(st.session_state["ma_chat_history"]):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"], unsafe_allow_html=True)
                    if msg["role"] == "assistant":
                        if msg.get("activity_log"):
                            _render_activity_log(msg["activity_log"])
                        st.caption("Multi-agent analysis · Based on U.S. Census Bureau data")
                        # Build full report: all agent outputs + final synthesis
                        report_parts = []
                        for step in msg.get("activity_log", []):
                            report_parts.append(
                                f"## {step['icon']} {step['agent']}\n\n"
                                f"**Input:** {step['input']}\n\n"
                                f"{step['output']}\n\n"
                                f"---\n"
                            )
                        report_parts.append(f"## ✅ Final Synthesis\n\n{msg['content']}")
                        full_report = "\n".join(report_parts)

                        st.download_button(
                            label="⬇ Download Full Report",
                            data=full_report,
                            file_name=f"trade_report_{msg_idx}.md",
                            mime="text/markdown",
                            key=f"dl_{msg_idx}",
                        )

        # Handle pending question
        pending = st.session_state.pop("t7_pending", None)

        # Chat input
        user_input = st.chat_input("Ask for a deep report or what-if scenario…") or pending

        if user_input:
            st.session_state["ma_chat_history"].append(
                {"role": "user", "content": user_input}
            )

            activity_log = []
            answer = ""
            with st.status("Orchestrating agents…", expanded=True) as status:
                st.write("🧠 Orchestrator — planning agent calls…")
                try:
                    from orchestrator import run_orchestrator
                    answer, activity_log = run_orchestrator(
                        user_input, api_key, uploaded_df=uploaded_df
                    )
                    for step in activity_log:
                        st.write(f"{step['icon']} {step['agent']} — completed")
                    status.update(label="Analysis complete", state="complete")
                except Exception as e:
                    err_msg = str(e)
                    if "401" in err_msg or "authentication" in err_msg.lower():
                        answer = "Invalid API key. Please contact administrator."
                    elif "429" in err_msg or "rate_limit" in err_msg.lower():
                        answer = "Rate limit reached. Please wait a moment and try again."
                    else:
                        answer = f"An error occurred: {err_msg}"
                    status.update(label="Error", state="error")

            answer = _fix_response(answer)
            st.session_state["ma_chat_history"].append(
                {"role": "assistant", "content": answer, "activity_log": activity_log}
            )
            st.rerun()
