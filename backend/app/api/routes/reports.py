"""Reports API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.database.models import AccountReport
from app.database.schemas import APIResponse, ReportDetail

router = APIRouter()


@router.get("/reports/{report_id}", response_model=APIResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Retrieve a full account intelligence report by ID."""
    result = await db.execute(
        select(AccountReport).where(AccountReport.report_id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")

    return APIResponse(
        success=True,
        data=ReportDetail.model_validate(report).model_dump(),
    )


@router.get("/reports", response_model=APIResponse)
async def list_reports(
    db: AsyncSession = Depends(get_database),
    limit: int = 50,
) -> APIResponse:
    """List recent reports across all accounts."""
    result = await db.execute(
        select(AccountReport)
        .where(AccountReport.status == "complete")
        .order_by(AccountReport.generated_at.desc())
        .limit(limit)
    )
    reports = result.scalars().all()

    from app.database.schemas import ReportSummary
    return APIResponse(
        success=True,
        data=[ReportSummary.model_validate(r).model_dump() for r in reports],
    )
