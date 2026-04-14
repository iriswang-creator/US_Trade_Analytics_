"""
orchestrator.py — Phase 4 Multi-Agent Architecture.

Three specialist agents, each a separate Claude inference:
  1. Query Agent    — data lookup using the trade data tools
  2. Report Agent   — structures findings into a polished markdown report
  3. What-If Agent  — scenario / counterfactual analysis

An Orchestrator agent coordinates them via the "agents-as-tools" pattern:
it treats each specialist as a tool call, decides which to invoke and in
what order, then synthesises a final answer.

Public API:
    run_orchestrator(question, api_key, uploaded_df=None)
        → (final_answer: str, activity_log: list[dict])
"""

import anthropic
from agent import _TOOLS, _UPLOADED_DATA_TOOL, _dispatch

# ── Specialist system prompts ─────────────────────────────────────────────────

_QUERY_SYSTEM = """You are a US trade data lookup specialist with access to \
official U.S. Census Bureau trade data from 1985 to 2026. \
Your ONLY job is to retrieve accurate numbers from the data tools. \
Always use the tools — never guess figures. \
Return raw facts and numbers; another agent will write the narrative."""

_REPORT_SYSTEM = """You are a senior trade economist who writes concise, \
well-structured analytical reports. You will receive a question and \
data context already gathered by a data agent. \
Your job: synthesise the data into a clear markdown report with these sections:

## Executive Summary
(2–3 sentence headline finding)

## Key Findings
(bullet points with specific numbers)

## Analysis
(interpretation, trends, context)

## Conclusion
(so-what for policy or business)

Use **bold** for key figures. Be precise and cite years."""

_WHATIF_SYSTEM = """You are a trade policy scenario analyst. You will receive \
a what-if question and historical data context. \
Reason through the scenario using the data as a baseline. \
Structure your response:

## Scenario Assumptions
## Baseline Data
## Projected Impact
## Risks & Uncertainties

Be quantitative where possible. Acknowledge what the data cannot tell us."""

_ORCH_SYSTEM = """You are a trade analysis coordinator managing a team of \
specialist AI agents. Given a user question, decide which specialists to call \
and in what order.

Rules:
- For factual / lookup questions: call query_agent only.
- For "analyse", "report", "compare in depth": call query_agent first, \
then report_agent with the gathered data.
- For "what if", "scenario", "what would happen": call query_agent first, \
then whatif_agent with the gathered data.
- For complex questions requiring both analysis and scenario: \
call query_agent → report_agent → whatif_agent.
- Never fabricate data; always get facts from query_agent first.
- After all specialist calls, write a concise final synthesis."""

# ── Orchestrator tool schemas ─────────────────────────────────────────────────

_ORCH_TOOLS = [
    {
        "name": "call_query_agent",
        "description": (
            "Call the Data Query Specialist to retrieve specific trade statistics, "
            "rankings, or bilateral trade figures from the Census Bureau database. "
            "Always call this first before report_agent or whatif_agent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific data question for the query agent.",
                }
            },
            "required": ["question"],
        },
    },
    {
        "name": "call_report_agent",
        "description": (
            "Call the Report Writer Specialist to produce a structured analytical "
            "markdown report. Requires data_context from query_agent first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question":     {"type": "string", "description": "The original user question."},
                "data_context": {"type": "string", "description": "Raw data gathered by query_agent."},
            },
            "required": ["question", "data_context"],
        },
    },
    {
        "name": "call_whatif_agent",
        "description": (
            "Call the Scenario Analyst Specialist for what-if / counterfactual "
            "analysis. Requires data_context from query_agent as baseline."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario":     {"type": "string", "description": "The what-if scenario to analyse."},
                "data_context": {"type": "string", "description": "Baseline data from query_agent."},
            },
            "required": ["scenario", "data_context"],
        },
    },
]


# ── Specialist runners ────────────────────────────────────────────────────────

def _run_query_specialist(question: str, api_key: str, uploaded_df=None) -> str:
    """Runs the Query Specialist — a Claude call with all data tools."""
    client = anthropic.Anthropic(api_key=api_key)
    active_tools = list(_TOOLS)
    system = _QUERY_SYSTEM
    if uploaded_df is not None:
        active_tools.append(_UPLOADED_DATA_TOOL)
        system += (
            "\n\nThe user has uploaded a custom dataset. "
            "Use query_uploaded_data (start with operation='schema') "
            "to explore it alongside the built-in data."
        )

    messages = [{"role": "user", "content": question}]
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
            return "No data retrieved."

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

    return "Query agent reached max iterations."


def _run_report_specialist(question: str, data_context: str, api_key: str) -> str:
    """Runs the Report Specialist — no data tools, pure synthesis."""
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        f"Question: {question}\n\n"
        f"Data gathered by the query agent:\n{data_context}\n\n"
        "Please write a structured analytical report based on this data."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 最便宜，速度最快
        max_tokens=3000,
        system=_REPORT_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "Report agent produced no output."


def _run_whatif_specialist(scenario: str, data_context: str, api_key: str) -> str:
    """Runs the What-If Specialist — scenario reasoning over baseline data."""
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        f"Scenario: {scenario}\n\n"
        f"Baseline data:\n{data_context}\n\n"
        "Analyse this scenario using the baseline data above."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 最便宜，速度最快
        max_tokens=2500,
        system=_WHATIF_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "What-if agent produced no output."


# ── Orchestrator dispatch ─────────────────────────────────────────────────────

def _orch_dispatch(tool_name: str, tool_input: dict,
                   api_key: str, uploaded_df, activity_log: list) -> str:
    if tool_name == "call_query_agent":
        answer = _run_query_specialist(tool_input["question"], api_key, uploaded_df)
        activity_log.append({
            "agent": "Query Agent",
            "icon": "🔍",
            "input": tool_input["question"],
            "output": answer,
        })
        return answer

    elif tool_name == "call_report_agent":
        answer = _run_report_specialist(
            tool_input["question"],
            tool_input.get("data_context", ""),
            api_key,
        )
        activity_log.append({
            "agent": "Report Agent",
            "icon": "📊",
            "input": tool_input["question"],
            "output": answer,
        })
        return answer

    elif tool_name == "call_whatif_agent":
        answer = _run_whatif_specialist(
            tool_input["scenario"],
            tool_input.get("data_context", ""),
            api_key,
        )
        activity_log.append({
            "agent": "What-If Agent",
            "icon": "🔮",
            "input": tool_input["scenario"],
            "output": answer,
        })
        return answer

    return f"Unknown orchestrator tool: {tool_name}"


# ── Public API ────────────────────────────────────────────────────────────────

def run_orchestrator(question: str, api_key: str,
                     uploaded_df=None) -> tuple[str, list]:
    """Coordinate specialist agents and return the final answer + activity log.

    Returns:
        (final_answer, activity_log)
        activity_log is a list of dicts: {agent, icon, input, output}
    """
    client = anthropic.Anthropic(api_key=api_key)
    activity_log: list[dict] = []
    messages = [{"role": "user", "content": question}]

    for _ in range(6):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # 最便宜，速度最快
            max_tokens=3000,
            system=_ORCH_SYSTEM,
            tools=_ORCH_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text, activity_log
            return "No final answer produced.", activity_log

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _orch_dispatch(
                        block.name, block.input, api_key, uploaded_df, activity_log
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return "Orchestrator reached maximum iterations.", activity_log
