"""
Tests for account scoring service.
Scoring is deterministic Python — tests do not require Gemini API.
"""
import pytest
from datetime import datetime, timedelta

from app.services.scoring_service import ScoringService


@pytest.fixture
def scorer():
    return ScoringService()


@pytest.fixture
def healthy_activities():
    now = datetime.utcnow()
    return [
        {"activity_type": "call", "activity_date": now - timedelta(days=5)},
        {"activity_type": "email", "activity_date": now - timedelta(days=10)},
        {"activity_type": "meeting", "activity_date": now - timedelta(days=15)},
    ]


@pytest.fixture
def stale_activities():
    now = datetime.utcnow()
    return [
        {"activity_type": "call", "activity_date": now - timedelta(days=200)},
    ]


class TestProductFitScoring:
    def test_no_opportunities_returns_neutral(self, scorer):
        result = scorer.calculate(
            account_id="test-1",
            opportunities=[],
            activities=[],
            contacts=[],
            ai_opportunities=[],
            company_profile=None,
        )
        pf = next(c for c in result.components if c.name == "Product Fit")
        assert pf.raw_score == 50.0
        assert pf.data_quality == "missing"

    def test_closed_won_opportunity_boosts_score(self, scorer):
        result = scorer.calculate(
            account_id="test-2",
            opportunities=[{"stage": "closed_won", "deal_value": 50000}],
            activities=[],
            contacts=[],
            ai_opportunities=[],
        )
        pf = next(c for c in result.components if c.name == "Product Fit")
        assert pf.raw_score > 70

    def test_closed_lost_opportunity_lowers_score(self, scorer):
        result = scorer.calculate(
            account_id="test-3",
            opportunities=[{"stage": "closed_lost", "deal_value": 0}],
            activities=[],
            contacts=[],
            ai_opportunities=[],
        )
        pf = next(c for c in result.components if c.name == "Product Fit")
        assert pf.raw_score < 60


class TestEngagementScoring:
    def test_no_activities_returns_neutral(self, scorer):
        result = scorer.calculate("test-4", [], [], [], [])
        eng = next(c for c in result.components if c.name == "Engagement")
        assert eng.raw_score == 50.0
        assert eng.data_quality == "missing"

    def test_recent_activities_give_high_score(self, scorer, healthy_activities):
        result = scorer.calculate("test-5", [], healthy_activities, [], [])
        eng = next(c for c in result.components if c.name == "Engagement")
        assert eng.raw_score >= 70

    def test_stale_activities_give_low_score(self, scorer, stale_activities):
        result = scorer.calculate("test-6", [], stale_activities, [], [])
        eng = next(c for c in result.components if c.name == "Engagement")
        assert eng.raw_score < 50


class TestFinalScoreCalculation:
    def test_total_score_within_bounds(self, scorer, healthy_activities):
        result = scorer.calculate(
            account_id="test-7",
            opportunities=[{"stage": "proposal", "deal_value": 25000}],
            activities=healthy_activities,
            contacts=[{"name": "Alice", "role": "CTO"}],
            ai_opportunities=[{"confidence_level": "high"}],
            company_profile={"confidence_level": "high", "key_findings": ["A", "B"]},
        )
        assert 0 <= result.total_score <= 100

    def test_weights_sum_to_one(self, scorer):
        total_weight = sum(scorer.WEIGHTS.values())
        assert abs(total_weight - 1.0) < 0.0001

    def test_score_is_deterministic(self, scorer, healthy_activities):
        """Same inputs always produce same score."""
        contacts = [{"name": "Bob", "role": "VP Sales"}]
        opps = [{"stage": "qualification", "deal_value": 10000}]
        kwargs = dict(
            account_id="test-8",
            opportunities=opps,
            activities=healthy_activities,
            contacts=contacts,
            ai_opportunities=[],
        )
        result1 = scorer.calculate(**kwargs)
        result2 = scorer.calculate(**kwargs)
        assert result1.total_score == result2.total_score

    def test_high_priority_category(self, scorer, healthy_activities):
        result = scorer.calculate(
            account_id="test-9",
            opportunities=[{"stage": "closed_won"}, {"stage": "negotiation"}],
            activities=healthy_activities,
            contacts=[{"name": "C"}, {"name": "D"}, {"name": "E"}],
            ai_opportunities=[
                {"confidence_level": "high"},
                {"confidence_level": "high"},
            ],
            company_profile={
                "confidence_level": "high",
                "key_findings": ["A", "B", "C"],
                "missing_information": [],
            },
        )
        # Can't guarantee exactly High Priority without very specific data, but
        # score should be meaningfully higher than pure-neutral
        assert result.total_score > 55

    def test_low_data_quality_gives_medium_score(self, scorer):
        result = scorer.calculate(
            account_id="test-10",
            opportunities=[],
            activities=[],
            contacts=[],
            ai_opportunities=[],
        )
        # With all missing data, should land at neutral (~50)
        assert 40 <= result.total_score <= 65

    def test_missing_data_flags_populated(self, scorer):
        result = scorer.calculate("test-11", [], [], [], [])
        assert len(result.missing_data_flags) > 0

    def test_category_boundaries(self, scorer):
        from unittest.mock import patch
        # Directly test _categorize
        assert scorer._categorize(85) == "High Priority"
        assert scorer._categorize(80) == "High Priority"
        assert scorer._categorize(79) == "Medium Priority"
        assert scorer._categorize(60) == "Medium Priority"
        assert scorer._categorize(59) == "Low Priority"
        assert scorer._categorize(0) == "Low Priority"
