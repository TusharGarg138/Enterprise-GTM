"""
Opportunities API routes: list, filter, and retrieve business opportunities.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.core.logging import get_logger
from app.database.models import Account, Opportunity
from app.database.schemas import APIResponse, OpportunityOut

router = APIRouter()
logger = get_logger(__name__)


@router.get("/opportunities", response_model=APIResponse)
async def list_opportunities(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    report_id: Optional[str] = Query(None, description="Filter by report ID"),
    confidence_level: Optional[str] = Query(None, description="Filter by confidence: high, medium, low"),
    is_ai_generated: Optional[bool] = Query(None, description="Filter by AI generated flag"),
    stage: Optional[str] = Query(None, description="Filter by deal stage"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """
    List opportunities across accounts with optional filters.
    Includes associated company name for rich dashboard display.
    """
    query = (
        select(Opportunity, Account.company_name)
        .outerjoin(Account, Opportunity.account_id == Account.account_id)
        .order_by(Opportunity.created_at.desc())
    )

    if account_id:
        query = query.where(Opportunity.account_id == account_id)
    if report_id:
        query = query.where(Opportunity.report_id == report_id)
    if confidence_level:
        query = query.where(Opportunity.confidence_level == confidence_level.lower())
    if is_ai_generated is not None:
        query = query.where(Opportunity.is_ai_generated == is_ai_generated)
    if stage:
        query = query.where(Opportunity.stage == stage)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    data = []
    for opp, company_name in rows:
        out = OpportunityOut.model_validate(opp)
        out.company_name = company_name or "Unknown Company"
        data.append(out.model_dump())

    return APIResponse(
        success=True,
        data=data,
    )


@router.get("/opportunities/{opportunity_id}", response_model=APIResponse)
async def get_opportunity(
    opportunity_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Get single opportunity by ID."""
    result = await db.execute(
        select(Opportunity, Account.company_name)
        .outerjoin(Account, Opportunity.account_id == Account.account_id)
        .where(Opportunity.opportunity_id == opportunity_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opportunity_id}' not found.")

    opp, company_name = row
    out = OpportunityOut.model_validate(opp)
    out.company_name = company_name or "Unknown Company"

    return APIResponse(
        success=True,
        data=out.model_dump(),
    )


@router.get("/accounts/{account_id}/opportunities", response_model=APIResponse)
async def list_account_opportunities(
    account_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """List all opportunities for an account."""
    acc_check = await db.execute(select(Account).where(Account.account_id == account_id))
    account = acc_check.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    result = await db.execute(
        select(Opportunity)
        .where(Opportunity.account_id == account_id)
        .order_by(Opportunity.created_at.desc())
    )
    opps = result.scalars().all()

    data = []
    for opp in opps:
        out = OpportunityOut.model_validate(opp)
        out.company_name = account.company_name
        data.append(out.model_dump())

    return APIResponse(
        success=True,
        data=data,
    )
