"""
Account Risk Agent: identifies CRM-based risk signals.
Missing data is explicitly distinguished from actual negative signals.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.agents.state import GTMAgentState, RiskOutput
from app.core.logging import get_logger
from app.services.gemini_service import GeminiServiceError, get_gemini_service

logger = get_logger(__name__)

RISK_SYSTEM_INSTRUCTION = """You are an enterprise account risk analyst.
Your role is to identify CRM-based risk signals that may indicate account health issues.

STRICT RULES:
1. Only identify risks with supporting CRM evidence provided in the context.
2. Missing data is NOT a risk signal — clearly distinguish data gaps from actual problems.
3. Never invent churn risks, customer problems, or negative signals without evidence.
4. If CRM evidence is insufficient, state clearly that risk assessment is limited.
5. Set severity honestly based on evidence strength and business impact.
6. Each risk must have a specific suggested_action for the sales team.
7. Do not assume negative intent from ambiguous CRM data.
"""

RISK_SCHEMA = """{
  "risks": [
    {
      "risk_category": "engagement | progression | data_quality | relationship | competitive",
      "risk_description": "Specific description of the identified risk",
      "severity": "high | medium | low",
      "supporting_evidence": ["CRM evidence item 1", "CRM evidence item 2"],
      "detection_reason": "Why this was flagged as a risk",
      "suggested_action": "Specific recommended action for the sales team"
    }
  ],
  "total_risks": 0,
  "data_sufficiency": "sufficient | partial | insufficient",
  "analysis_notes": "Overall assessment and any caveats"
}"""


def _build_crm_summary(state: GTMAgentState) -> Dict[str, Any]:
    """Build structured CRM summary for risk analysis."""
    activities = state.get("crm_activities", [])
    contacts = state.get("crm_contacts", [])
    opportunities = state.get("crm_opportunities", [])

    now = datetime.utcnow()

    # Last activity date
    activity_dates = []
    for a in activities:
        date_val = a.get("activity_date")
        if isinstance(date_val, datetime):
            activity_dates.append(date_val)
        elif isinstance(date_val, str):
            try:
                activity_dates.append(datetime.fromisoformat(date_val))
            except ValueError:
                pass

    last_activity = max(activity_dates) if activity_dates else None
    days_since_last = (now - last_activity).days if last_activity else None

    # Stalled opportunities
    stalled_opps = [
        o for o in opportunities
        if o.get("stage") in ("qualification", "proposal", "negotiation")
        and o.get("close_date")
        and _is_past_due(o.get("close_date"))
    ]

    # Recent activities (last 30 days)
    recent_activities = [
        a for a in activities
        if a.get("activity_date") and _is_recent(a.get("activity_date"), days=30)
    ]

    return {
        "total_activities": len(activities),
        "recent_activities_30d": len(recent_activities),
        "total_contacts": len(contacts),
        "total_opportunities": len(opportunities),
        "stalled_opportunities": len(stalled_opps),
        "days_since_last_activity": days_since_last,
        "opportunity_stages": [o.get("stage", "unknown") for o in opportunities],
        "activity_types": list(set(a.get("activity_type", "") for a in activities)),
        "has_contacts": len(contacts) > 0,
        "has_activities": len(activities) > 0,
    }


def _is_past_due(close_date_val) -> bool:
    now = datetime.utcnow()
    if isinstance(close_date_val, datetime):
        return close_date_val < now
    if isinstance(close_date_val, str):
        try:
            return datetime.fromisoformat(close_date_val) < now
        except ValueError:
            pass
    return False


def _is_recent(date_val, days: int = 30) -> bool:
    now = datetime.utcnow()
    if isinstance(date_val, datetime):
        return (now - date_val).days <= days
    if isinstance(date_val, str):
        try:
            return (now - datetime.fromisoformat(date_val)).days <= days
        except ValueError:
            pass
    return False


async def risk_agent_node(state: GTMAgentState) -> Dict[str, Any]:
    """
    LangGraph node: Risk Agent.
    Runs in parallel with Opportunity Agent after Research Agent completes.
    """
    start = time.time()
    agent_name = "risk"

    logger.info("Risk Agent starting for account: %s", state["account_id"])

    statuses = dict(state.get("agent_statuses", {}))
    statuses[agent_name] = {
        "status": "running",
        "error": None,
        "duration_seconds": None,
        "retry_count": state.get("retry_count", 0),
    }

    # Check if there's enough CRM data to analyze
    has_any_crm = (
        state.get("crm_activities") or
        state.get("crm_contacts") or
        state.get("crm_opportunities")
    )

    if not has_any_crm:
        logger.info("Risk Agent: no CRM data available for account %s", state["account_id"])
        statuses[agent_name]["status"] = "complete"
        statuses[agent_name]["duration_seconds"] = round(time.time() - start, 2)
        insufficient_risk: RiskOutput = {
            "risk_category": "data_quality",
            "risk_description": "No CRM history is available for this account.",
            "severity": "low",
            "supporting_evidence": ["No CRM activities, contacts, or opportunities found."],
            "detection_reason": "Missing CRM data prevents risk assessment, not evidence of risk.",
            "suggested_action": "Begin CRM data entry for this account to enable risk monitoring.",
        }
        return {
            "risks": [insufficient_risk],
            "agent_statuses": statuses,
        }

    crm_summary = _build_crm_summary(state)

    prompt = (
        f"Company: {state['company_name']}\n"
        f"CRM Summary:\n"
        f"- Total activities: {crm_summary['total_activities']}\n"
        f"- Activities in last 30 days: {crm_summary['recent_activities_30d']}\n"
        f"- Days since last activity: {crm_summary['days_since_last_activity'] or 'Unknown'}\n"
        f"- Total contacts: {crm_summary['total_contacts']}\n"
        f"- Total opportunities: {crm_summary['total_opportunities']}\n"
        f"- Stalled/overdue opportunities: {crm_summary['stalled_opportunities']}\n"
        f"- Opportunity stages: {', '.join(crm_summary['opportunity_stages']) or 'None'}\n"
        f"- Activity types: {', '.join(crm_summary['activity_types']) or 'None'}\n\n"
        "Identify risk signals based strictly on the CRM data above. "
        "Do not invent risks. If CRM data is limited, reflect that in data_sufficiency. "
        "Missing data should be noted but NOT treated as a risk signal itself."
    )

    gemini = get_gemini_service()

    try:
        output_dict = await gemini.generate_structured(
            prompt=prompt,
            schema_description=RISK_SCHEMA,
            system_instruction=RISK_SYSTEM_INSTRUCTION,
        )

        raw_risks = output_dict.get("risks", [])
        risks: List[RiskOutput] = []

        for risk in raw_risks:
            if not risk.get("risk_description"):
                continue
            risks.append({
                "risk_category": str(risk.get("risk_category", "engagement")),
                "risk_description": str(risk.get("risk_description", "")),
                "severity": str(risk.get("severity", "low")),
                "supporting_evidence": list(risk.get("supporting_evidence", [])),
                "detection_reason": str(risk.get("detection_reason", "")),
                "suggested_action": str(risk.get("suggested_action", "")),
            })

        statuses[agent_name]["status"] = "complete"
        statuses[agent_name]["duration_seconds"] = round(time.time() - start, 2)
        logger.info("Risk Agent complete. Identified: %d risk(s).", len(risks))

        return {
            "risks": risks,
            "agent_statuses": statuses,
        }

    except GeminiServiceError as exc:
        logger.error("Risk Agent Gemini error: %s", exc)
        statuses[agent_name]["status"] = "failed"
        statuses[agent_name]["error"] = str(exc)
        statuses[agent_name]["duration_seconds"] = round(time.time() - start, 2)
        return {
            "risks": [],
            "agent_statuses": statuses,
            "workflow_errors": state.get("workflow_errors", []) + [f"Risk Agent failed: {exc}"],
        }
