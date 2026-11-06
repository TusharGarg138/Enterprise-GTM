"""
Pydantic API schemas — separated from SQLAlchemy ORM models.
These define what the API accepts and returns, not the DB structure.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class APIResponse(BaseModel):
    """Standard envelope used for all API responses."""
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class PaginatedResponse(BaseModel):
    """Standard paginated list response."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ---------------------------------------------------------------------------
# Account schemas
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=512)
    employee_band: Optional[str] = Field(None, max_length=50)
    company_description: Optional[str] = None

    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            if not v.startswith(("http://", "https://")):
                v = "https://" + v
        return v


class AccountUpdate(BaseModel):
    company_name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=512)
    employee_band: Optional[str] = Field(None, max_length=50)
    company_description: Optional[str] = None


class AccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    company_name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    employee_band: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    account_score: Optional[float] = None
    score_category: Optional[str] = None
    opportunity_count: int = 0
    risk_flag: bool = False
    last_researched: Optional[datetime] = None


class AccountDetail(AccountSummary):
    company_description: Optional[str] = None
    contacts: List["ContactOut"] = []
    activities: List["ActivityOut"] = []
    opportunities: List["OpportunityOut"] = []
    latest_report: Optional["ReportSummary"] = None


# ---------------------------------------------------------------------------
# Contact schemas
# ---------------------------------------------------------------------------

class ContactCreate(BaseModel):
    account_id: str
    name: str = Field(..., min_length=1, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact_id: str
    account_id: str
    name: str
    role: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Activity schemas
# ---------------------------------------------------------------------------

class ActivityCreate(BaseModel):
    account_id: str
    activity_type: str = Field(..., max_length=50)
    activity_date: Optional[datetime] = None
    notes: Optional[str] = None


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: str
    account_id: str
    activity_type: str
    activity_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Opportunity schemas
# ---------------------------------------------------------------------------

class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: str
    account_id: str
    report_id: Optional[str] = None
    product_id: Optional[str] = None
    deal_value: Optional[float] = None
    stage: str
    close_date: Optional[datetime] = None
    is_ai_generated: bool = False
    opportunity_title: Optional[str] = None
    description: Optional[str] = None
    business_rationale: Optional[str] = None
    relevant_product: Optional[str] = None
    confidence_level: Optional[str] = None
    validation_question: Optional[str] = None
    recommended_action: Optional[str] = None
    supporting_evidence: Optional[List[str]] = None
    created_at: datetime
    company_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Report schemas
# ---------------------------------------------------------------------------

class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: str
    account_id: str
    account_score: Optional[float] = None
    score_category: Optional[str] = None
    model_name: Optional[str] = None
    generated_at: Optional[datetime] = None
    status: str
    report_json: Optional[Dict[str, Any]] = None


class ReportDetail(ReportSummary):
    prompt_version: Optional[str] = None


# ---------------------------------------------------------------------------
# Research job schemas
# ---------------------------------------------------------------------------

class ResearchJobCreate(BaseModel):
    account_id: str
    website_url: Optional[str] = None


class ResearchJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    account_id: str
    status: str
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    report_id: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Ingestion schemas
# ---------------------------------------------------------------------------

class WebsiteIngestionRequest(BaseModel):
    account_id: str
    url: str = Field(..., description="Public company website URL to ingest")
    max_pages: Optional[int] = Field(None, ge=1, le=20)


class CSVIngestionResult(BaseModel):
    file_name: str
    rows_processed: int
    rows_inserted: int
    rows_skipped: int
    errors: List[str] = []


# ---------------------------------------------------------------------------
# Chat / Q&A schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    account_id: str
    question: str = Field(..., min_length=3, max_length=2000)
    conversation_id: Optional[str] = None


class SourceReference(BaseModel):
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    chunk_text: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceReference] = []
    account_id: str
    conversation_id: Optional[str] = None
    is_grounded: bool = True
    model_name: str


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    gemini: str
    environment: str
    timestamp: datetime
