"""
Accounts API routes.
CRUD operations for company accounts with proper validation and pagination.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import PaginationParams, get_database
from app.core.logging import get_logger
from app.database.models import Account, AccountReport, Activity, Contact, Opportunity
from app.database.schemas import (
    AccountCreate,
    AccountDetail,
    AccountSummary,
    AccountUpdate,
    APIResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("/accounts", response_model=APIResponse)
async def list_accounts(
    db: AsyncSession = Depends(get_database),
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search by company name"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    score_category: Optional[str] = Query(None, description="Filter by priority category"),
) -> APIResponse:
    """List all accounts with optional filtering and pagination."""
    query = select(Account)

    if search:
        query = query.where(Account.company_name.ilike(f"%{search}%"))
    if industry:
        query = query.where(Account.industry.ilike(f"%{industry}%"))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginated results
    query = query.order_by(Account.updated_at.desc()).offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Enrich with score/opportunity data from latest report
    summaries = []
    for acc in accounts:
        report_q = (
            select(AccountReport)
            .where(AccountReport.account_id == acc.account_id)
            .where(AccountReport.status == "complete")
            .order_by(AccountReport.generated_at.desc())
            .limit(1)
        )
        report_r = await db.execute(report_q)
        latest_report = report_r.scalar_one_or_none()

        opp_count_q = select(func.count()).where(Opportunity.account_id == acc.account_id)
        opp_count_r = await db.execute(opp_count_q)
        opp_count = opp_count_r.scalar() or 0

        summaries.append(AccountSummary(
            account_id=acc.account_id,
            company_name=acc.company_name,
            industry=acc.industry,
            website=acc.website,
            employee_band=acc.employee_band,
            created_at=acc.created_at,
            updated_at=acc.updated_at,
            account_score=latest_report.account_score if latest_report else None,
            score_category=latest_report.score_category if latest_report else None,
            opportunity_count=opp_count,
            last_researched=latest_report.generated_at if latest_report else None,
        ))

    if score_category:
        summaries = [s for s in summaries if s.score_category and s.score_category.lower() == score_category.lower()]

    pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
    return APIResponse(
        success=True,
        data={
            "items": [s.model_dump() for s in summaries],
            "total": total,
            "page": pagination.page,
            "page_size": pagination.page_size,
            "pages": pages,
        },
    )


@router.post("/accounts", response_model=APIResponse, status_code=201)
async def create_account(
    payload: AccountCreate,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Create a new company account."""
    # Check for duplicate website
    if payload.website:
        existing_q = select(Account).where(Account.website == payload.website)
        existing_r = await db.execute(existing_q)
        if existing_r.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"An account with website '{payload.website}' already exists.",
            )

    account = Account(
        company_name=payload.company_name,
        industry=payload.industry,
        website=payload.website,
        employee_band=payload.employee_band,
        company_description=payload.company_description,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    logger.info("Created account: %s (%s)", account.company_name, account.account_id)

    return APIResponse(
        success=True,
        message="Account created successfully.",
        data={"account_id": account.account_id, "company_name": account.company_name},
    )


@router.get("/accounts/{account_id}", response_model=APIResponse)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Get detailed account information including contacts, activities, and latest report."""
    result = await db.execute(
        select(Account)
        .options(
            selectinload(Account.contacts),
            selectinload(Account.activities),
            selectinload(Account.opportunities),
        )
        .where(Account.account_id == account_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    # Latest complete report
    report_q = (
        select(AccountReport)
        .where(AccountReport.account_id == account_id)
        .where(AccountReport.status == "complete")
        .order_by(AccountReport.generated_at.desc())
        .limit(1)
    )
    report_r = await db.execute(report_q)
    latest_report = report_r.scalar_one_or_none()

    from app.database.schemas import ActivityOut, ContactOut, OpportunityOut, ReportSummary

    detail = AccountDetail(
        account_id=account.account_id,
        company_name=account.company_name,
        industry=account.industry,
        website=account.website,
        employee_band=account.employee_band,
        company_description=account.company_description,
        created_at=account.created_at,
        updated_at=account.updated_at,
        account_score=latest_report.account_score if latest_report else None,
        score_category=latest_report.score_category if latest_report else None,
        opportunity_count=len(account.opportunities),
        last_researched=latest_report.generated_at if latest_report else None,
        contacts=[ContactOut.model_validate(c) for c in account.contacts],
        activities=[ActivityOut.model_validate(a) for a in account.activities],
        opportunities=[OpportunityOut.model_validate(o) for o in account.opportunities],
        latest_report=ReportSummary.model_validate(latest_report) if latest_report else None,
    )
    return APIResponse(success=True, data=detail.model_dump())


@router.patch("/accounts/{account_id}", response_model=APIResponse)
async def update_account(
    account_id: str,
    payload: AccountUpdate,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Update account fields."""
    result = await db.execute(select(Account).where(Account.account_id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.flush()
    logger.info("Updated account: %s", account_id)
    return APIResponse(success=True, message="Account updated.", data={"account_id": account_id})


@router.delete("/accounts/{account_id}", response_model=APIResponse)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Delete an account and all associated data."""
    result = await db.execute(select(Account).where(Account.account_id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    await db.delete(account)
    logger.info("Deleted account: %s", account_id)
    return APIResponse(success=True, message="Account deleted.")
