"""
LangGraph shared state definition for the multi-agent research workflow.
All agents read from and write to this typed state.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class AgentStatus(TypedDict):
    """Track each agent's execution status."""
    status: str           # "pending" | "running" | "complete" | "failed" | "skipped"
    error: Optional[str]
    duration_seconds: Optional[float]
    retry_count: int


class ResearchOutput(TypedDict):
    """Structured output from the Research Agent."""
    company_overview: str
    industry: str
    business_model: str
    products_and_services: List[str]
    target_customers: str
    market_segments: List[str]
    business_priorities: List[str]
    key_findings: List[str]
    evidence_references: List[Dict[str, str]]
    confidence_level: str    # "high" | "medium" | "low"
    missing_information: List[str]


class OpportunityOutput(TypedDict):
    """Structured output from the Opportunity Detection Agent."""
    opportunity_title: str
    description: str
    business_rationale: str
    relevant_product: str
    supporting_evidence: List[str]
    confidence_level: str     # "high" | "medium" | "low"
    validation_question: str
    recommended_action: str


class RiskOutput(TypedDict):
    """Structured output from the Risk Agent."""
    risk_category: str       # "engagement" | "progression" | "data_quality" | "relationship"
    risk_description: str
    severity: str            # "high" | "medium" | "low"
    supporting_evidence: List[str]
    detection_reason: str
    suggested_action: str


class StrategyOutput(TypedDict):
    """Structured output from the Strategy Agent."""
    account_summary: str
    primary_opportunity: str
    main_risks: List[str]
    recommended_actions: List[Dict[str, str]]   # [{action, priority, timeline}]
    suggested_stakeholder: Optional[str]
    discovery_questions: List[str]
    outreach_draft: Dict[str, str]              # {subject, body, tone}
    suggested_priority: str
    missing_information: List[str]


class GTMAgentState(TypedDict):
    """
    Shared state for the GTM multi-agent LangGraph workflow.
    All agents read required fields and write to their designated output fields.
    """

    # ------- Inputs -------
    account_id: str
    company_name: str
    website_url: Optional[str]
    model_name: str
    prompt_version: str

    # ------- CRM Context (loaded at workflow start) -------
    crm_contacts: List[Dict[str, Any]]
    crm_activities: List[Dict[str, Any]]
    crm_opportunities: List[Dict[str, Any]]

    # ------- RAG Context -------
    retrieved_documents: List[Dict[str, Any]]   # from ChromaDB

    # ------- Product Catalogue -------
    product_catalogue: List[Dict[str, Any]]

    # ------- Agent Outputs -------
    research_output: Optional[ResearchOutput]
    opportunities: List[OpportunityOutput]
    risks: List[RiskOutput]
    account_score: Optional[Dict[str, Any]]     # AccountScore.to_dict()
    strategy_output: Optional[StrategyOutput]

    # ------- Agent Status Tracking -------
    agent_statuses: Dict[str, AgentStatus]

    # ------- Final Report -------
    final_report: Optional[Dict[str, Any]]
    report_status: str    # "pending" | "complete" | "failed"
    workflow_errors: List[str]

    # ------- Retry Control -------
    retry_count: int
    max_retries: int
