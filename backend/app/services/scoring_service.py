"""
Deterministic account scoring service.
Gemini explains scores but NEVER calculates them — Python does.
Weights and thresholds are fully configurable via settings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "1.0"


@dataclass
class ScoreComponent:
    name: str
    raw_score: float          # 0–100
    weight: float
    weighted_score: float
    reasoning: str
    data_quality: str         # "sufficient" | "partial" | "missing"


@dataclass
class AccountScore:
    total_score: float
    category: str             # "High Priority" | "Medium Priority" | "Low Priority"
    components: List[ScoreComponent]
    missing_data_flags: List[str]
    scoring_notes: str
    prompt_version: str = PROMPT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": round(self.total_score, 2),
            "category": self.category,
            "components": [
                {
                    "name": c.name,
                    "raw_score": round(c.raw_score, 2),
                    "weight": c.weight,
                    "weighted_score": round(c.weighted_score, 2),
                    "reasoning": c.reasoning,
                    "data_quality": c.data_quality,
                }
                for c in self.components
            ],
            "missing_data_flags": self.missing_data_flags,
            "scoring_notes": self.scoring_notes,
            "prompt_version": self.prompt_version,
        }


class ScoringService:
    """
    Calculates a deterministic, explainable account score from structured signals.

    Scoring formula:
        Score = 0.35 × ProductFit + 0.25 × Engagement + 0.20 × GrowthSignals + 0.20 × CRMQuality

    All components normalized to 0–100. Missing data is treated neutrally (50),
    not penalized unless there is explicit evidence of a problem.
    """

    # Component weights — read from settings for configurability
    WEIGHTS = {
        "product_fit": settings.SCORE_WEIGHT_PRODUCT_FIT,
        "engagement": settings.SCORE_WEIGHT_ENGAGEMENT,
        "growth_signals": settings.SCORE_WEIGHT_GROWTH_SIGNALS,
        "crm_quality": settings.SCORE_WEIGHT_CRM_QUALITY,
    }

    def calculate(
        self,
        account_id: str,
        opportunities: List[Dict[str, Any]],
        activities: List[Dict[str, Any]],
        contacts: List[Dict[str, Any]],
        ai_opportunities: List[Dict[str, Any]],
        company_profile: Optional[Dict[str, Any]] = None,
    ) -> AccountScore:
        """
        Calculate the account score from CRM data and AI-identified signals.

        Args:
            account_id: The account being scored.
            opportunities: List of CRM opportunity dicts (stage, deal_value, etc.).
            activities: List of CRM activity dicts (activity_type, activity_date, etc.).
            contacts: List of contact dicts.
            ai_opportunities: Opportunities identified by the Opportunity Agent.
            company_profile: Optional company profile from the Research Agent.

        Returns:
            AccountScore with component breakdown and explanations.
        """
        missing_flags: List[str] = []

        # 1. Product Fit Score
        product_fit_score, product_fit_reasoning, product_fit_quality = self._score_product_fit(
            opportunities, ai_opportunities, missing_flags
        )

        # 2. Engagement Score
        engagement_score, engagement_reasoning, engagement_quality = self._score_engagement(
            activities, contacts, missing_flags
        )

        # 3. Growth Signals Score
        growth_score, growth_reasoning, growth_quality = self._score_growth_signals(
            company_profile, missing_flags
        )

        # 4. CRM Quality Score
        crm_quality_score, crm_quality_reasoning, crm_quality_quality = self._score_crm_quality(
            contacts, activities, opportunities, missing_flags
        )

        components = [
            ScoreComponent(
                name="Product Fit",
                raw_score=product_fit_score,
                weight=self.WEIGHTS["product_fit"],
                weighted_score=product_fit_score * self.WEIGHTS["product_fit"],
                reasoning=product_fit_reasoning,
                data_quality=product_fit_quality,
            ),
            ScoreComponent(
                name="Engagement",
                raw_score=engagement_score,
                weight=self.WEIGHTS["engagement"],
                weighted_score=engagement_score * self.WEIGHTS["engagement"],
                reasoning=engagement_reasoning,
                data_quality=engagement_quality,
            ),
            ScoreComponent(
                name="Growth Signals",
                raw_score=growth_score,
                weight=self.WEIGHTS["growth_signals"],
                weighted_score=growth_score * self.WEIGHTS["growth_signals"],
                reasoning=growth_reasoning,
                data_quality=growth_quality,
            ),
            ScoreComponent(
                name="CRM Quality",
                raw_score=crm_quality_score,
                weight=self.WEIGHTS["crm_quality"],
                weighted_score=crm_quality_score * self.WEIGHTS["crm_quality"],
                reasoning=crm_quality_reasoning,
                data_quality=crm_quality_quality,
            ),
        ]

        total = sum(c.weighted_score for c in components)
        total = max(0.0, min(100.0, total))

        category = self._categorize(total)

        scoring_notes = (
            f"Score calculated deterministically. "
            f"Missing data treated neutrally (50/100 baseline). "
            f"Weights: Product Fit {self.WEIGHTS['product_fit']:.0%}, "
            f"Engagement {self.WEIGHTS['engagement']:.0%}, "
            f"Growth {self.WEIGHTS['growth_signals']:.0%}, "
            f"CRM Quality {self.WEIGHTS['crm_quality']:.0%}."
        )

        logger.info(
            "Account %s scored: %.1f (%s). Missing data: %s",
            account_id, total, category, missing_flags or "none",
        )

        return AccountScore(
            total_score=total,
            category=category,
            components=components,
            missing_data_flags=missing_flags,
            scoring_notes=scoring_notes,
        )

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def _score_product_fit(
        self,
        crm_opps: List[Dict],
        ai_opps: List[Dict],
        missing_flags: List[str],
    ) -> tuple[float, str, str]:
        """
        Score based on evidence of product-company fit.
        Uses CRM opportunity stages and AI-identified opportunities.
        """
        if not crm_opps and not ai_opps:
            missing_flags.append("No opportunity data available.")
            return 50.0, "No opportunity data available. Using neutral baseline.", "missing"

        score = 50.0
        reasons = []

        # CRM opportunities with positive stages boost score
        stage_scores = {
            "closed_won": 100,
            "negotiation": 85,
            "proposal": 70,
            "qualification": 60,
            "prospecting": 50,
            "closed_lost": 20,
        }
        if crm_opps:
            stage_values = [stage_scores.get(o.get("stage", ""), 50) for o in crm_opps]
            avg_stage_score = sum(stage_values) / len(stage_values)
            score = (score + avg_stage_score) / 2
            best_stage = max(crm_opps, key=lambda o: stage_scores.get(o.get("stage", ""), 0))
            reasons.append(f"{len(crm_opps)} CRM opportunity(ies), best stage: {best_stage.get('stage', 'unknown')}.")

        # AI-identified high-confidence opportunities boost score
        if ai_opps:
            high_conf = [o for o in ai_opps if o.get("confidence", "").lower() in ("high", "medium")]
            if high_conf:
                score = min(100, score + len(high_conf) * 8)
                reasons.append(f"{len(high_conf)} AI-identified opportunity(ies) with medium/high confidence.")

        return min(100.0, score), " ".join(reasons) or "Limited product fit signals.", "sufficient" if crm_opps else "partial"

    def _score_engagement(
        self,
        activities: List[Dict],
        contacts: List[Dict],
        missing_flags: List[str],
    ) -> tuple[float, str, str]:
        """
        Score based on recency and frequency of CRM activity and contact coverage.
        """
        if not activities:
            missing_flags.append("No CRM activity history found.")
            return 50.0, "No CRM activity history. Using neutral baseline.", "missing"

        score = 0.0
        reasons = []

        # Recency: most recent activity within last 30/90/180 days
        now = datetime.utcnow()
        dates = []
        for a in activities:
            date_val = a.get("activity_date")
            if isinstance(date_val, datetime):
                dates.append(date_val)
            elif isinstance(date_val, str):
                try:
                    dates.append(datetime.fromisoformat(date_val))
                except ValueError:
                    pass

        if dates:
            most_recent = max(dates)
            days_ago = (now - most_recent).days
            if days_ago <= 30:
                recency_score = 100
                reasons.append(f"Last activity {days_ago} day(s) ago (very recent).")
            elif days_ago <= 90:
                recency_score = 70
                reasons.append(f"Last activity {days_ago} day(s) ago (recent).")
            elif days_ago <= 180:
                recency_score = 40
                reasons.append(f"Last activity {days_ago} day(s) ago (aging).")
            else:
                recency_score = 15
                reasons.append(f"Last activity {days_ago} day(s) ago (stale).")
            score += recency_score * 0.6
        else:
            score += 50 * 0.6
            missing_flags.append("Activity dates not parseable.")

        # Frequency: number of activities in last 90 days
        if dates:
            recent_count = sum(1 for d in dates if (now - d).days <= 90)
            freq_score = min(100, recent_count * 15)
            score += freq_score * 0.3
            reasons.append(f"{recent_count} activity(ies) in last 90 days.")
        else:
            score += 50 * 0.3

        # Contact coverage
        contact_score = min(100, len(contacts) * 25)
        score += contact_score * 0.1
        reasons.append(f"{len(contacts)} known contact(s).")

        return min(100.0, round(score, 1)), " ".join(reasons), "sufficient"

    def _score_growth_signals(
        self,
        company_profile: Optional[Dict],
        missing_flags: List[str],
    ) -> tuple[float, str, str]:
        """
        Score based on company growth indicators from the research profile.
        Without data, return neutral (not punitive).
        """
        if not company_profile:
            missing_flags.append("Company research profile not available.")
            return 50.0, "No company research data available. Using neutral baseline.", "missing"

        score = 50.0
        reasons = []

        # Confidence from Research Agent
        confidence = company_profile.get("confidence_level", "").lower()
        if confidence == "high":
            score = min(100, score + 20)
            reasons.append("High research confidence.")
        elif confidence == "medium":
            score = min(100, score + 10)
            reasons.append("Medium research confidence.")

        # Key findings count (proxy for available growth signals)
        findings = company_profile.get("key_findings", [])
        if findings:
            score = min(100, score + min(20, len(findings) * 5))
            reasons.append(f"{len(findings)} key finding(s) identified.")

        # Missing information penalizes slightly
        missing = company_profile.get("missing_information", [])
        if missing:
            score = max(0, score - len(missing) * 3)
            reasons.append(f"{len(missing)} missing information item(s).")

        return round(score, 1), " ".join(reasons) or "Limited growth signal data.", "partial" if company_profile else "missing"

    def _score_crm_quality(
        self,
        contacts: List[Dict],
        activities: List[Dict],
        opportunities: List[Dict],
        missing_flags: List[str],
    ) -> tuple[float, str, str]:
        """
        Score based on completeness and quality of CRM data.
        """
        score = 0.0
        reasons = []
        data_quality = "sufficient"

        # Has contacts
        if contacts:
            contact_score = min(40, len(contacts) * 10)
            score += contact_score
            reasons.append(f"{len(contacts)} contact(s) on record.")
        else:
            score += 0
            missing_flags.append("No contacts in CRM.")
            data_quality = "partial"

        # Has activities
        if activities:
            activity_score = min(35, len(activities) * 5)
            score += activity_score
            reasons.append(f"{len(activities)} activity record(s).")
        else:
            score += 0
            missing_flags.append("No CRM activities recorded.")
            data_quality = "partial"

        # Has opportunities with deal values
        valued_opps = [o for o in opportunities if o.get("deal_value")]
        if valued_opps:
            score += 25
            reasons.append(f"{len(valued_opps)} opportunity(ies) with deal values.")
        elif opportunities:
            score += 10
            reasons.append(f"{len(opportunities)} opportunity(ies) without deal values.")
        else:
            missing_flags.append("No CRM opportunities recorded.")
            data_quality = "missing" if not contacts and not activities else "partial"

        if score == 0:
            return 20.0, "Minimal CRM data. Score reflects data scarcity, not performance.", "missing"

        return min(100.0, round(score, 1)), " ".join(reasons), data_quality

    def _categorize(self, score: float) -> str:
        if score >= settings.SCORE_HIGH_THRESHOLD:
            return "High Priority"
        elif score >= settings.SCORE_MEDIUM_THRESHOLD:
            return "Medium Priority"
        return "Low Priority"


from functools import lru_cache

@lru_cache(maxsize=1)
def get_scoring_service() -> ScoringService:
    """Return the application-wide ScoringService singleton."""
    return ScoringService()
