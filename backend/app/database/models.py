"""
SQLAlchemy ORM models for the GTM Intelligence platform.

Design decisions:
- Models are kept separate from Pydantic API schemas (in schemas.py).
- All foreign keys include cascade rules.
- JSON is stored in a JSONB column where PostgreSQL supports it.
- Use UUID primary keys for accounts, contacts and reports for portability.
- Use integer sequences for activities and opportunities (simpler CRM import).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    website: Mapped[Optional[str]] = mapped_column(String(512))
    employee_band: Mapped[Optional[str]] = mapped_column(String(50))  # e.g. "50-200"
    company_description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=_now, onupdate=_now, server_default=func.now()
    )

    # Relationships
    contacts: Mapped[List["Contact"]] = relationship(
        "Contact", back_populates="account", cascade="all, delete-orphan"
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity", back_populates="account", cascade="all, delete-orphan"
    )
    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity", back_populates="account", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="account", cascade="all, delete-orphan"
    )
    reports: Mapped[List["AccountReport"]] = relationship(
        "AccountReport", back_populates="account", cascade="all, delete-orphan"
    )
    research_jobs: Mapped[List["ResearchJob"]] = relationship(
        "ResearchJob", back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_accounts_company_name", "company_name"),
        UniqueConstraint("website", name="uq_accounts_website"),
    )

    def __repr__(self) -> str:
        return f"<Account id={self.account_id!r} name={self.company_name!r}>"


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

class Contact(Base):
    __tablename__ = "contacts"

    contact_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    account: Mapped["Account"] = relationship("Account", back_populates="contacts")

    __table_args__ = (
        Index("ix_contacts_account_id", "account_id"),
        Index("ix_contacts_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<Contact id={self.contact_id!r} name={self.name!r}>"


# ---------------------------------------------------------------------------
# Activities (CRM interactions)
# ---------------------------------------------------------------------------

class Activity(Base):
    __tablename__ = "activities"

    activity_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "call", "email", "meeting", "demo", "note"
    activity_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    account: Mapped["Account"] = relationship("Account", back_populates="activities")

    __table_args__ = (
        Index("ix_activities_account_id", "account_id"),
        Index("ix_activities_date", "activity_date"),
    )


# ---------------------------------------------------------------------------
# Products (hypothetical catalogue for opportunity detection)
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    target_industry: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity", back_populates="product"
    )


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

class Opportunity(Base):
    __tablename__ = "opportunities"

    opportunity_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("account_reports.report_id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("products.product_id", ondelete="SET NULL"), nullable=True
    )
    deal_value: Mapped[Optional[float]] = mapped_column(Float)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="prospecting")
    # e.g. prospecting | qualification | proposal | negotiation | closed_won | closed_lost
    close_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    opportunity_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    business_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relevant_product: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    validation_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_evidence: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    account: Mapped["Account"] = relationship("Account", back_populates="opportunities")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="opportunities")
    report: Mapped[Optional["AccountReport"]] = relationship("AccountReport", back_populates="opportunities")

    __table_args__ = (
        Index("ix_opportunities_account_id", "account_id"),
        Index("ix_opportunities_stage", "stage"),
        Index("ix_opportunities_report_id", "report_id"),
    )


# ---------------------------------------------------------------------------
# Documents (ingested web pages / uploaded files)
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g. "website", "csv", "manual"
    source_url: Mapped[Optional[str]] = mapped_column(String(1024))
    source_title: Mapped[Optional[str]] = mapped_column(String(512))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA-256 hex
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    account: Mapped["Account"] = relationship("Account", back_populates="documents")

    __table_args__ = (
        Index("ix_documents_account_id", "account_id"),
        Index("ix_documents_content_hash", "content_hash"),
        UniqueConstraint("account_id", "content_hash", name="uq_document_hash"),
    )


# ---------------------------------------------------------------------------
# Account Reports
# ---------------------------------------------------------------------------

class AccountReport(Base):
    __tablename__ = "account_reports"

    report_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    report_json: Mapped[Optional[dict]] = mapped_column(JSON)
    account_score: Mapped[Optional[float]] = mapped_column(Float)
    score_category: Mapped[Optional[str]] = mapped_column(String(20))
    model_name: Mapped[Optional[str]] = mapped_column(String(100))
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20))
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # e.g. pending | generating | complete | failed

    account: Mapped["Account"] = relationship("Account", back_populates="reports")
    opportunities: Mapped[List["Opportunity"]] = relationship(
        "Opportunity", back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_account_reports_account_id", "account_id"),
        Index("ix_account_reports_status", "status"),
        Index("ix_account_reports_generated_at", "generated_at"),
    )


# ---------------------------------------------------------------------------
# Research Jobs (background processing)
# ---------------------------------------------------------------------------

class ResearchJob(Base):
    __tablename__ = "research_jobs"

    job_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")
    # queued | running | complete | failed | timeout
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False))
    report_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("account_reports.report_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=_now)

    account: Mapped["Account"] = relationship("Account", back_populates="research_jobs")

    __table_args__ = (
        Index("ix_research_jobs_account_id", "account_id"),
        Index("ix_research_jobs_status", "status"),
    )
