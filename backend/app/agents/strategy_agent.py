"""
Account Strategy Agent: synthesizes findings from all agents into actionable strategy.
Every recommendation is connected to a finding or supporting signal.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from app.agents.state import GTMAgentState, StrategyOutput
from app.core.logging import get_logger
from app.services.gemini_service import GeminiServiceError, get_gemini_service

logger = get_logger(__name__)

STRATEGY_SYSTEM_INSTRUCTION = """You are an enterprise account strategy expert.
Your role is to synthesize research, opportunities, risks, and scoring into an actionable account strategy.

STRICT RULES:
1. Every recommendation must connect to a specific finding, opportunity, or risk.
2. NEVER fabricate contact details, executive names, or company events.
3. The outreach_draft must be personalized to the actual company context found in research.
4. If information is missing, reflect this in missing_information — do not guess.
5. suggested_stakeholder should only be provided if a name appears in CRM contacts.
6. Discovery questions should be open-ended and specific to this company's context.
7. Keep recommendations specific and actionable, not generic sales advice.
"""

STRATEGY_SCHEMA = """{
  "account_summary": "2-3 sentence summary of the account situation",
  "primary_opportunity": "The single most compelling opportunity based on evidence",
  "main_risks": ["risk 1", "risk 2"],
  "recommended_actions": [
    {"action": "specific action", "priority": "high|medium|low", "timeline": "immediate|this_week|this_month"}
  ],
  "suggested_stakeholder": "Name and role if in CRM contacts, otherwise null",
  "discovery_questions": ["question 1", "question 2", "question 3"],
  "outreach_draft": {
    "subject": "Email subject line personalized to company context",
    "body": "Email body — specific to company findings, 3-4 short paragraphs",
    "tone": "professional|consultative|technical"
  },
  "suggested_priority": "high|medium|low",
  "missing_information": ["information gaps that limit the strategy quality"]
}"""


async def strategy_agent_node(state: GTMAgentState) -> Dict[str, Any]:
    """
    LangGraph node: Strategy Agent (runs last, after scoring).
    """
    start = time.time()
    agent_name = "strategy"

    logger.info("Strategy Agent starting for account: %s", state["account_id"])

    statuses = dict(state.get("agent_statuses", {}))
    statuses[agent_name] = {
        "status": "running",
        "error": None,
        "duration_seconds": None,
        "retry_count": state.get("retry_count", 0),
    }

    research = state.get("research_output") or {}
    opportunities = state.get("opportunities", [])
    risks = state.get("risks", [])
    account_score = state.get("account_score") or {}
    contacts = state.get("crm_contacts", [])

    # Build contacts summary (names only — do not fabricate)
    contacts_summary = ", ".join(
        f"{c.get('name', 'Unknown')} ({c.get('role', 'Unknown role')})"
        for c in contacts[:5]
    ) if contacts else "No CRM contacts on record"

    # Build opportunities summary
    opps_summary = "\n".join(
        f"- [{o.get('confidence_level', 'low').upper()}] {o.get('opportunity_title', '')}: "
        f"{o.get('description', '')}"
        for o in opportunities[:5]
    ) if opportunities else "No opportunities identified."

    # Build risks summary
    risks_summary = "\n".join(
        f"- [{r.get('severity', 'low').upper()}] {r.get('risk_category', '')}: "
        f"{r.get('risk_description', '')}"
        for r in risks[:5]
    ) if risks else "No significant risks identified."

    score_text = (
        f"Account Score: {account_score.get('total_score', 'N/A')}/100 "
        f"({account_score.get('category', 'Unknown')})"
        if account_score else "Account not scored yet."
    )

    prompt = (
        f"Company: {state['company_name']}\n"
        f"Industry: {research.get('industry', 'Unknown')}\n"
        f"Business Model: {research.get('business_model', 'Unknown')}\n"
        f"Overview: {research.get('company_overview', 'Not available')}\n"
        f"Products/Services: {', '.join(research.get('products_and_services', []))}\n"
        f"Key Findings: {', '.join(research.get('key_findings', []))}\n\n"
        f"CRM Contacts: {contacts_summary}\n\n"
        f"{score_text}\n\n"
        f"Identified Opportunities:\n{opps_summary}\n\n"
        f"Identified Risks:\n{risks_summary}\n\n"
        "Create a practical, personalized account strategy. "
        "Connect every recommendation to a specific finding. "
        "If suggested_stakeholder is requested, only use names from the CRM contacts list provided. "
        "The outreach_draft must reference the actual company context, not generic content."
    )

    gemini = get_gemini_service()

    try:
        output_dict = await gemini.generate_structured(
            prompt=prompt,
            schema_description=STRATEGY_SCHEMA,
            system_instruction=STRATEGY_SYSTEM_INSTRUCTION,
        )

        strategy: StrategyOutput = {
            "account_summary": str(output_dict.get("account_summary", "")),
            "primary_opportunity": str(output_dict.get("primary_opportunity", "")),
            "main_risks": list(output_dict.get("main_risks", [])),
            "recommended_actions": list(output_dict.get("recommended_actions", [])),
            "suggested_stakeholder": output_dict.get("suggested_stakeholder"),
            "discovery_questions": list(output_dict.get("discovery_questions", [])),
            "outreach_draft": dict(output_dict.get("outreach_draft", {})),
            "suggested_priority": str(output_dict.get("suggested_priority", "medium")),
            "missing_information": list(output_dict.get("missing_information", [])),
        }

        statuses[agent_name]["status"] = "complete"
        statuses[agent_name]["duration_seconds"] = round(time.time() - start, 2)
        logger.info("Strategy Agent complete.")

        return {
            "strategy_output": strategy,
            "agent_statuses": statuses,
        }

    except GeminiServiceError as exc:
        logger.error("Strategy Agent Gemini error: %s", exc)
        statuses[agent_name]["status"] = "failed"
        statuses[agent_name]["error"] = str(exc)
        statuses[agent_name]["duration_seconds"] = round(time.time() - start, 2)
        return {
            "strategy_output": None,
            "agent_statuses": statuses,
            "workflow_errors": state.get("workflow_errors", []) + [f"Strategy Agent failed: {exc}"],
        }
