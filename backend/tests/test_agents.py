"""
Tests for agent input/output schemas and mocked agent execution.
Agents are tested with mocked Gemini to avoid API calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_state(**overrides):
    """Create a minimal GTMAgentState for testing."""
    base = {
        "account_id": "test-account-123",
        "company_name": "Test Corp",
        "website_url": "https://testcorp.com",
        "model_name": "gemini-2.0-flash",
        "prompt_version": "1.0",
        "crm_contacts": [],
        "crm_activities": [],
        "crm_opportunities": [],
        "retrieved_documents": [],
        "product_catalogue": [],
        "research_output": None,
        "opportunities": [],
        "risks": [],
        "account_score": None,
        "strategy_output": None,
        "agent_statuses": {},
        "final_report": None,
        "report_status": "pending",
        "workflow_errors": [],
        "retry_count": 0,
        "max_retries": 2,
    }
    base.update(overrides)
    return base


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_research_agent_no_documents(self):
        """Research agent with no documents should return low-confidence profile."""
        from app.agents.research_agent import research_agent_node

        with patch("app.services.retrieval_service.get_retrieval_service") as mock_ret, \
             patch("app.agents.research_agent.get_gemini_service") as mock_gem:

            mock_ret.return_value.retrieve = AsyncMock(return_value=[])
            mock_gem.return_value.generate_structured = AsyncMock(
                return_value={
                    "company_overview": "Test Corp overview",
                    "industry": "Technology",
                    "business_model": "SaaS",
                    "products_and_services": [],
                    "target_customers": "SMBs",
                    "market_segments": [],
                    "business_priorities": [],
                    "key_findings": [],
                    "evidence_references": [],
                    "confidence_level": "low",
                    "missing_information": ["No web content available"],
                }
            )

            state = _make_state()
            result = await research_agent_node(state)

            # With no docs, should return empty/low confidence profile
            assert "research_output" in result
            assert "agent_statuses" in result

    @pytest.mark.asyncio
    async def test_research_agent_handles_gemini_error(self):
        """Research agent should handle Gemini failures gracefully."""
        from app.agents.research_agent import research_agent_node
        from app.services.gemini_service import GeminiServiceError

        with patch("app.services.retrieval_service.get_retrieval_service") as mock_ret, \
             patch("app.agents.research_agent.get_gemini_service") as mock_gem:

            # Return some docs so it tries to call Gemini
            mock_ret.return_value.retrieve = AsyncMock(return_value=[
                {"text": "Test Corp content", "source_url": "https://test.com", "document_id": "d1", "chunk_index": 0, "score": 0.9}
            ])
            mock_gem.return_value.generate_structured = AsyncMock(
                side_effect=GeminiServiceError("API quota exceeded", is_quota_error=True)
            )

            state = _make_state()
            result = await research_agent_node(state)

            assert result["agent_statuses"]["research"]["status"] == "failed"
            assert len(result.get("workflow_errors", [])) > 0


class TestOpportunityAgent:
    @pytest.mark.asyncio
    async def test_opportunity_agent_skipped_without_research(self):
        """Opportunity agent should skip if research output is missing."""
        from app.agents.opportunity_agent import opportunity_agent_node

        state = _make_state(research_output=None)
        result = await opportunity_agent_node(state)

        assert result["agent_statuses"]["opportunity"]["status"] == "skipped"
        assert result["opportunities"] == []

    @pytest.mark.asyncio
    async def test_opportunity_agent_with_research(self):
        """Opportunity agent should identify opportunities from research."""
        from app.agents.opportunity_agent import opportunity_agent_node

        research_output = {
            "company_overview": "Tech company providing SaaS tools",
            "industry": "Technology",
            "business_model": "SaaS",
            "products_and_services": ["CRM", "Analytics"],
            "target_customers": "Enterprise",
            "market_segments": ["B2B"],
            "business_priorities": ["Scale", "Integration"],
            "key_findings": ["Growing rapidly", "Needs data integration"],
            "evidence_references": [],
            "confidence_level": "medium",
            "missing_information": [],
        }

        with patch("app.services.retrieval_service.get_retrieval_service") as mock_ret, \
             patch("app.agents.opportunity_agent.get_gemini_service") as mock_gem:

            mock_ret.return_value.retrieve = AsyncMock(return_value=[])
            mock_gem.return_value.generate_structured = AsyncMock(
                return_value={
                    "opportunities": [
                        {
                            "opportunity_title": "Data Integration Opportunity",
                            "description": "They need better data integration",
                            "business_rationale": "They process large volumes of data",
                            "relevant_product": "DataSync Enterprise",
                            "supporting_evidence": ["Key finding: Needs data integration"],
                            "confidence_level": "medium",
                            "validation_question": "What is your current data integration setup?",
                            "recommended_action": "Schedule a discovery call",
                        }
                    ],
                    "total_opportunities": 1,
                    "analysis_notes": "One high-value opportunity identified.",
                }
            )

            state = _make_state(research_output=research_output)
            result = await opportunity_agent_node(state)

            assert len(result["opportunities"]) == 1
            opp = result["opportunities"][0]
            assert opp["opportunity_title"] == "Data Integration Opportunity"
            assert opp["confidence_level"] == "medium"
            assert result["agent_statuses"]["opportunity"]["status"] == "complete"


class TestRiskAgent:
    @pytest.mark.asyncio
    async def test_risk_agent_no_crm_data(self):
        """Risk agent with no CRM data should report insufficient data, not risks."""
        from app.agents.risk_agent import risk_agent_node

        state = _make_state()
        result = await risk_agent_node(state)

        assert result["agent_statuses"]["risk"]["status"] == "complete"
        assert len(result["risks"]) >= 1
        # Should indicate data gap, not a real risk
        risk = result["risks"][0]
        assert risk["severity"] == "low"
        assert risk["risk_category"] == "data_quality"

    @pytest.mark.asyncio
    async def test_risk_agent_with_stale_activities(self):
        """Risk agent should detect stale engagement."""
        from datetime import datetime, timedelta
        from app.agents.risk_agent import risk_agent_node

        old_activity = {
            "activity_type": "call",
            "activity_date": datetime.utcnow() - timedelta(days=200),
        }

        with patch("app.agents.risk_agent.get_gemini_service") as mock_gem:
            mock_gem.return_value.generate_structured = AsyncMock(
                return_value={
                    "risks": [
                        {
                            "risk_category": "engagement",
                            "risk_description": "No recent activity in 200 days",
                            "severity": "high",
                            "supporting_evidence": ["Last call was 200 days ago"],
                            "detection_reason": "No recent CRM activity",
                            "suggested_action": "Reach out immediately",
                        }
                    ],
                    "total_risks": 1,
                    "data_sufficiency": "partial",
                    "analysis_notes": "Risk based on activity gap",
                }
            )

            state = _make_state(crm_activities=[old_activity])
            result = await risk_agent_node(state)

            assert result["agent_statuses"]["risk"]["status"] == "complete"


class TestScoringNode:
    @pytest.mark.asyncio
    async def test_scoring_node_produces_score(self):
        """Scoring node should always produce a valid score."""
        from app.agents.graph import scoring_node

        state = _make_state(
            opportunities=[{"opportunity_title": "Test", "confidence_level": "medium"}],
            crm_opportunities=[{"stage": "qualification", "deal_value": 10000}],
        )
        result = await scoring_node(state)

        assert "account_score" in result
        score = result["account_score"]
        assert 0 <= score["total_score"] <= 100
        assert score["category"] in ("High Priority", "Medium Priority", "Low Priority")
        assert len(score["components"]) == 4
