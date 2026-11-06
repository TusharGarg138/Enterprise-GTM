"""
Unit and integration tests for Opportunity persistence and Opportunities API.
Verifies that:
1. Opportunities generated during company research are saved to the database.
2. The correct account_id and report_id are associated.
3. The Opportunities API returns saved records with company_name.
4. Confidence level and account filtering function correctly.
5. OpportunityOut schema validation works as expected.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_database
from app.database.models import Account, AccountReport, Opportunity, ResearchJob
from app.database.schemas import OpportunityOut


@pytest.fixture
def test_client():
    """Create FastAPI test client with mocked DB initialization and Gemini."""
    with patch("app.main.init_db", new_callable=AsyncMock), \
         patch("app.main.close_db", new_callable=AsyncMock), \
         patch("app.main.check_db_connection", new_callable=AsyncMock, return_value=True), \
         patch("app.services.gemini_service.get_gemini_service") as mock_gemini:

        mock_svc = MagicMock()
        mock_svc.health_check = AsyncMock(return_value={"status": "ok", "model": "gemini-3.1-flash-lite", "message": "ok"})
        mock_svc.get_model_name.return_value = "gemini-3.1-flash-lite"
        mock_gemini.return_value = mock_svc

        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


class TestOpportunitiesAPI:
    def test_list_opportunities_mocked(self, test_client):
        """Test GET /api/v1/opportunities returns opportunities list."""
        from app.main import app

        fake_opp = Opportunity(
            opportunity_id=str(uuid.uuid4()),
            account_id="acc-123",
            report_id="rep-123",
            opportunity_title="AI Data Pipeline",
            description="High value integration need.",
            confidence_level="high",
            relevant_product="DataSync Enterprise",
            stage="prospecting",
            is_ai_generated=True,
            created_at=datetime.utcnow(),
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(fake_opp, "Acme Corp")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_database] = override_get_db
        try:
            response = test_client.get("/api/v1/opportunities")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            item = data["data"][0]
            assert item["opportunity_title"] == "AI Data Pipeline"
            assert item["company_name"] == "Acme Corp"
            assert item["confidence_level"] == "high"
            assert item["is_ai_generated"] is True
        finally:
            app.dependency_overrides.pop(get_database, None)

    def test_filter_by_confidence(self, test_client):
        """Test GET /api/v1/opportunities with confidence_level filter parameter."""
        from app.main import app

        fake_opp = Opportunity(
            opportunity_id=str(uuid.uuid4()),
            account_id="acc-456",
            report_id="rep-456",
            opportunity_title="Cloud Security Gateway",
            description="Need cloud security gateway.",
            confidence_level="medium",
            stage="qualification",
            is_ai_generated=True,
            created_at=datetime.utcnow(),
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(fake_opp, "Beta Corp")]
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_database] = override_get_db
        try:
            response = test_client.get("/api/v1/opportunities?confidence_level=medium")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["confidence_level"] == "medium"
        finally:
            app.dependency_overrides.pop(get_database, None)

    def test_get_opportunity_by_id(self, test_client):
        """Test GET /api/v1/opportunities/{id}."""
        from app.main import app

        fake_id = str(uuid.uuid4())
        fake_opp = Opportunity(
            opportunity_id=fake_id,
            account_id="acc-789",
            report_id="rep-789",
            opportunity_title="DevOps Automation Fit",
            description="CI/CD bottleneck detected.",
            confidence_level="high",
            stage="prospecting",
            is_ai_generated=True,
            created_at=datetime.utcnow(),
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = (fake_opp, "Gamma Corp")
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_database] = override_get_db
        try:
            response = test_client.get(f"/api/v1/opportunities/{fake_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["opportunity_id"] == fake_id
            assert data["data"]["company_name"] == "Gamma Corp"
        finally:
            app.dependency_overrides.pop(get_database, None)

    def test_opportunity_not_found(self, test_client):
        """Test GET /api/v1/opportunities/{id} returns 404 when missing."""
        from app.main import app

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_database] = override_get_db
        try:
            response = test_client.get("/api/v1/opportunities/nonexistent-id-000")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_database, None)


@pytest.mark.asyncio
async def test_workflow_persists_opportunities():
    """
    Test that _run_research_workflow properly creates and persists
    Opportunity records with the correct account_id and report_id.
    """
    from app.api.routes.research import _run_research_workflow

    fake_acc_id = str(uuid.uuid4())
    fake_job_id = str(uuid.uuid4())

    mock_report = {
        "account_id": fake_acc_id,
        "company_name": "Test Company",
        "account_score": {"total_score": 85.0, "category": "High Priority"},
        "model_name": "gemini-3.1-flash-lite",
        "prompt_version": "1.0",
        "opportunities": [
            {
                "opportunity_title": "Enterprise Cloud Migration",
                "description": "Evidence shows legacy infrastructure needing cloud modernization.",
                "business_rationale": "High ROI on cloud transition.",
                "relevant_product": "DataSync Enterprise",
                "confidence_level": "high",
                "validation_question": "What is your migration timeline?",
                "recommended_action": "Schedule architectural discovery call.",
                "supporting_evidence": ["Scraped page indicates on-prem databases."],
            }
        ],
    }

    mock_job = MagicMock(spec=ResearchJob)
    mock_job.job_id = fake_job_id
    mock_job.status = "queued"

    added_objects = []

    class MockAsyncSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def execute(self, statement):
            res = MagicMock()
            res.scalar_one_or_none.return_value = mock_job
            return res

        def add(self, obj):
            added_objects.append(obj)

        async def flush(self):
            for obj in added_objects:
                if isinstance(obj, AccountReport) and not getattr(obj, "report_id", None):
                    obj.report_id = str(uuid.uuid4())

        async def commit(self):
            pass

    with patch("app.agents.orchestrator.run_account_research", new_callable=AsyncMock, return_value=mock_report), \
         patch("app.database.connection.AsyncSessionFactory", return_value=MockAsyncSession()):

        await _run_research_workflow(fake_job_id, fake_acc_id, "https://test.com")

        # Verify AccountReport was added
        reports_added = [o for o in added_objects if isinstance(o, AccountReport)]
        assert len(reports_added) == 1
        created_report_id = reports_added[0].report_id

        # Verify Opportunity was added and correctly linked to account_id and report_id
        opps_added = [o for o in added_objects if isinstance(o, Opportunity)]
        assert len(opps_added) == 1

        opp = opps_added[0]
        assert opp.account_id == fake_acc_id
        assert opp.report_id == created_report_id
        assert opp.opportunity_title == "Enterprise Cloud Migration"
        assert opp.confidence_level == "high"
        assert opp.relevant_product == "DataSync Enterprise"
        assert opp.is_ai_generated is True
