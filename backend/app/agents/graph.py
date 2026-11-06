"""
LangGraph workflow graph definition.
Coordinates Research → (Opportunity + Risk in parallel) → Scoring → Strategy → Report.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.agents.opportunity_agent import opportunity_agent_node
from app.agents.research_agent import research_agent_node
from app.agents.risk_agent import risk_agent_node
from app.agents.state import GTMAgentState
from app.agents.strategy_agent import strategy_agent_node
from app.core.logging import get_logger

logger = get_logger(__name__)


async def scoring_node(state: GTMAgentState) -> Dict[str, Any]:
    """
    Deterministic scoring node. Runs after opportunity and risk agents.
    Scoring is NEVER done by Gemini — this is pure Python.
    """
    from app.services.scoring_service import get_scoring_service

    scorer = get_scoring_service()

    research = state.get("research_output") or {}
    opportunities = state.get("opportunities", [])
    risks = state.get("risks", [])
    contacts = state.get("crm_contacts", [])
    activities = state.get("crm_activities", [])
    crm_opps = state.get("crm_opportunities", [])

    score = scorer.calculate(
        account_id=state["account_id"],
        opportunities=crm_opps,
        activities=activities,
        contacts=contacts,
        ai_opportunities=opportunities,
        company_profile=research if research else None,
    )

    statuses = dict(state.get("agent_statuses", {}))
    statuses["scoring"] = {
        "status": "complete",
        "error": None,
        "duration_seconds": 0.0,
        "retry_count": 0,
    }

    logger.info(
        "Scoring complete. Score: %.1f (%s)", score.total_score, score.category
    )

    return {
        "account_score": score.to_dict(),
        "agent_statuses": statuses,
    }


async def report_assembly_node(state: GTMAgentState) -> Dict[str, Any]:
    """
    Assembles the final structured report from all agent outputs.
    Validates required fields and marks report status.
    """
    from datetime import datetime
    from app.services.gemini_service import get_gemini_service

    logger.info("Assembling final report for account: %s", state["account_id"])

    errors = state.get("workflow_errors", [])
    research = state.get("research_output") or {}
    opportunities = state.get("opportunities", [])
    risks = state.get("risks", [])
    score = state.get("account_score") or {}
    strategy = state.get("strategy_output") or {}

    # Collect all evidence references
    evidence = list(research.get("evidence_references", []))

    # Collect missing information across all agents
    missing_info = list(research.get("missing_information", []))
    missing_info += list(strategy.get("missing_information", []))

    report = {
        "account_id": state["account_id"],
        "company_name": state["company_name"],
        "company_profile": {
            "overview": research.get("company_overview", ""),
            "industry": research.get("industry", "Unknown"),
            "business_model": research.get("business_model", "Unknown"),
            "products_and_services": research.get("products_and_services", []),
            "target_customers": research.get("target_customers", ""),
            "market_segments": research.get("market_segments", []),
            "confidence_level": research.get("confidence_level", "low"),
        },
        "research_findings": research.get("key_findings", []),
        "opportunities": opportunities,
        "risks": risks,
        "account_score": score,
        "strategy": {
            "account_summary": strategy.get("account_summary", ""),
            "primary_opportunity": strategy.get("primary_opportunity", ""),
            "main_risks": strategy.get("main_risks", []),
            "recommended_actions": strategy.get("recommended_actions", []),
            "suggested_stakeholder": strategy.get("suggested_stakeholder"),
            "discovery_questions": strategy.get("discovery_questions", []),
            "suggested_priority": strategy.get("suggested_priority", "medium"),
        },
        "outreach_draft": strategy.get("outreach_draft", {}),
        "evidence": evidence,
        "missing_information": list(set(missing_info)),
        "agent_statuses": state.get("agent_statuses", {}),
        "workflow_errors": errors,
        "generated_at": datetime.utcnow().isoformat(),
        "model_name": state.get("model_name", ""),
        "prompt_version": state.get("prompt_version", "1.0"),
    }

    report_status = "complete" if not any(
        s.get("status") == "failed"
        for s in state.get("agent_statuses", {}).values()
    ) else "partial"

    logger.info("Report assembled. Status: %s", report_status)

    return {
        "final_report": report,
        "report_status": report_status,
    }


def should_retry(state: GTMAgentState) -> str:
    """Conditional routing: retry if failures occurred and retries remain."""
    has_critical_failure = (
        state.get("research_output") is None and
        state.get("retry_count", 0) < state.get("max_retries", 1)
    )
    if has_critical_failure:
        return "retry"
    return "continue"


def build_gtm_graph() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    graph = StateGraph(GTMAgentState)

    # Register nodes
    graph.add_node("research", research_agent_node)
    graph.add_node("opportunity", opportunity_agent_node)
    graph.add_node("risk", risk_agent_node)
    graph.add_node("scoring", scoring_node)
    graph.add_node("strategy", strategy_agent_node)
    graph.add_node("report", report_assembly_node)

    # Define edges
    graph.set_entry_point("research")

    # Sequential orchestration pipeline:
    # research -> opportunity -> risk -> scoring -> strategy -> report -> END
    graph.add_edge("research", "opportunity")
    graph.add_edge("opportunity", "risk")
    graph.add_edge("risk", "scoring")

    # Scoring → strategy → report → END
    graph.add_edge("scoring", "strategy")
    graph.add_edge("strategy", "report")
    graph.add_edge("report", END)

    return graph.compile()


# Module-level compiled graph
gtm_graph = build_gtm_graph()
