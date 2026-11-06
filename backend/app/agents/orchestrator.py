"""
Orchestrator: sets up the initial GTM agent state and runs the LangGraph workflow.
Called by background research jobs.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.agents.graph import gtm_graph
from app.agents.state import GTMAgentState
from app.core.config import settings
from app.core.logging import get_logger
from app.services.retrieval_service import get_retrieval_service

logger = get_logger(__name__)


async def run_account_research(
    account_id: str,
    website_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Entry point for the multi-agent research workflow.
    Loads account context, initializes state, and runs the LangGraph graph.

    Returns the final report dict.
    """
    logger.info("Starting GTM research workflow for account: %s", account_id)

    # Load account data from database
    from app.database.connection import AsyncSessionFactory
    from app.database.models import Account, Activity, Contact, Opportunity

    async with AsyncSessionFactory() as db:
        # Account
        acc_q = await db.execute(select(Account).where(Account.account_id == account_id))
        account = acc_q.scalar_one_or_none()
        if not account:
            raise ValueError(f"Account '{account_id}' not found.")

        company_name = account.company_name
        url = website_url or account.website

        # CRM data
        contacts_q = await db.execute(select(Contact).where(Contact.account_id == account_id))
        contacts = [
            {"contact_id": c.contact_id, "name": c.name, "role": c.role, "email": c.email}
            for c in contacts_q.scalars().all()
        ]

        activities_q = await db.execute(
            select(Activity).where(Activity.account_id == account_id)
            .order_by(Activity.activity_date.desc())
        )
        activities = [
            {
                "activity_id": a.activity_id,
                "activity_type": a.activity_type,
                "activity_date": a.activity_date,
                "notes": a.notes,
            }
            for a in activities_q.scalars().all()
        ]

        opps_q = await db.execute(select(Opportunity).where(Opportunity.account_id == account_id))
        opportunities = [
            {
                "opportunity_id": o.opportunity_id,
                "stage": o.stage,
                "deal_value": o.deal_value,
                "close_date": o.close_date,
                "is_ai_generated": o.is_ai_generated,
            }
            for o in opps_q.scalars().all()
        ]

    # Pre-retrieve documents from ChromaDB for initial context
    retrieval_svc = get_retrieval_service()
    initial_docs = await retrieval_svc.retrieve(
        query=f"{company_name} company overview",
        account_id=account_id,
        top_k=settings.RAG_TOP_K,
    )

    # Initialize LangGraph state
    initial_state: GTMAgentState = {
        "account_id": account_id,
        "company_name": company_name,
        "website_url": url,
        "model_name": settings.GEMINI_MODEL,
        "prompt_version": "1.0",
        "crm_contacts": contacts,
        "crm_activities": activities,
        "crm_opportunities": opportunities,
        "retrieved_documents": initial_docs,
        "product_catalogue": [],  # Will use defaults in opportunity agent
        "research_output": None,
        "opportunities": [],
        "risks": [],
        "account_score": None,
        "strategy_output": None,
        "agent_statuses": {
            "research": {"status": "pending", "error": None, "duration_seconds": None, "retry_count": 0},
            "opportunity": {"status": "pending", "error": None, "duration_seconds": None, "retry_count": 0},
            "risk": {"status": "pending", "error": None, "duration_seconds": None, "retry_count": 0},
            "scoring": {"status": "pending", "error": None, "duration_seconds": None, "retry_count": 0},
            "strategy": {"status": "pending", "error": None, "duration_seconds": None, "retry_count": 0},
        },
        "final_report": None,
        "report_status": "pending",
        "workflow_errors": [],
        "retry_count": 0,
        "max_retries": settings.GEMINI_MAX_RETRIES,
    }

    logger.info(
        "GTM workflow initialized. Contacts: %d, Activities: %d, Opportunities: %d, Docs: %d",
        len(contacts), len(activities), len(opportunities), len(initial_docs),
    )

    # Run the LangGraph workflow
    final_state = await gtm_graph.ainvoke(initial_state)

    report = final_state.get("final_report")
    if not report:
        raise RuntimeError("Workflow completed but no final report was generated.")

    logger.info(
        "GTM workflow complete. Status: %s, Score: %s",
        final_state.get("report_status"),
        final_state.get("account_score", {}).get("total_score") if final_state.get("account_score") else "N/A",
    )

    return report
