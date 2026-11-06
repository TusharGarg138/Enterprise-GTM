"""
Research job API routes: trigger and monitor multi-agent research workflows.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.core.logging import get_logger
from app.database.models import Account, AccountReport, Opportunity, ResearchJob
from app.database.schemas import APIResponse, ResearchJobCreate, ResearchJobOut

router = APIRouter()
logger = get_logger(__name__)


async def _run_research_workflow(job_id: str, account_id: str, website_url: Optional[str]) -> None:
    """
    Background task: runs the LangGraph multi-agent research workflow.
    Updates job and report status throughout.
    """
    from app.database.connection import AsyncSessionFactory
    from app.agents.orchestrator import run_account_research

    async with AsyncSessionFactory() as db:
        # Mark job as running
        job_q = await db.execute(select(ResearchJob).where(ResearchJob.job_id == job_id))
        job = job_q.scalar_one_or_none()
        if not job:
            return
        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()

        try:
            report = await run_account_research(account_id=account_id, website_url=website_url)

            # Save report
            account_report = AccountReport(
                account_id=account_id,
                report_json=report,
                account_score=report.get("account_score", {}).get("total_score"),
                score_category=report.get("account_score", {}).get("category"),
                model_name=report.get("model_name"),
                prompt_version=report.get("prompt_version", "1.0"),
                generated_at=datetime.utcnow(),
                status="complete",
            )
            db.add(account_report)
            await db.flush()

            # Save generated opportunities to database
            raw_opps = report.get("opportunities", [])
            for opp_data in raw_opps:
                title = opp_data.get("opportunity_title")
                if not title:
                    continue
                opp_record = Opportunity(
                    account_id=account_id,
                    report_id=account_report.report_id,
                    opportunity_title=title,
                    description=opp_data.get("description"),
                    business_rationale=opp_data.get("business_rationale"),
                    relevant_product=opp_data.get("relevant_product"),
                    confidence_level=opp_data.get("confidence_level", "low"),
                    validation_question=opp_data.get("validation_question"),
                    recommended_action=opp_data.get("recommended_action"),
                    supporting_evidence=opp_data.get("supporting_evidence", []),
                    stage="qualification" if opp_data.get("confidence_level") == "high" else "prospecting",
                    is_ai_generated=True,
                    created_at=datetime.utcnow(),
                )
                db.add(opp_record)

            job.status = "complete"
            job.completed_at = datetime.utcnow()
            job.report_id = account_report.report_id
            await db.commit()
            logger.info(
                "Research job %s completed. Report: %s, Opportunities saved: %d",
                job_id, account_report.report_id, len(raw_opps)
            )

        except Exception as exc:
            logger.error("Research job %s failed: %s", job_id, exc, exc_info=True)
            async with AsyncSessionFactory() as err_db:
                err_job_q = await err_db.execute(select(ResearchJob).where(ResearchJob.job_id == job_id))
                err_job = err_job_q.scalar_one_or_none()
                if err_job:
                    err_job.status = "failed"
                    err_job.error_message = str(exc)[:500]
                    err_job.completed_at = datetime.utcnow()
                    await err_db.commit()


@router.post("/accounts/{account_id}/research", response_model=APIResponse, status_code=202)
async def trigger_research(
    account_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database),
    website_url: Optional[str] = Query(None, description="Override website URL for this research run"),
) -> APIResponse:
    """
    Trigger a multi-agent research workflow for an account.
    Returns a job ID immediately; poll /research/jobs/{job_id} for status.
    """
    # Verify account
    acc_q = await db.execute(select(Account).where(Account.account_id == account_id))
    account = acc_q.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    # Create a research job record
    job = ResearchJob(account_id=account_id, status="queued")
    db.add(job)
    await db.flush()
    await db.refresh(job)
    job_id = job.job_id
    await db.commit()

    url = website_url or account.website
    background_tasks.add_task(_run_research_workflow, job_id, account_id, url)

    logger.info("Research job queued: %s for account %s", job_id, account_id)
    return APIResponse(
        success=True,
        message="Research job queued. Use the job_id to poll for status.",
        data={"job_id": job_id, "account_id": account_id, "status": "queued"},
    )


@router.get("/research/jobs/{job_id}", response_model=APIResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """Poll research job status."""
    result = await db.execute(select(ResearchJob).where(ResearchJob.job_id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return APIResponse(
        success=True,
        data=ResearchJobOut.model_validate(job).model_dump(),
    )


@router.get("/accounts/{account_id}/reports", response_model=APIResponse)
async def list_account_reports(
    account_id: str,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """List all research reports for an account (most recent first)."""
    acc_q = await db.execute(select(Account).where(Account.account_id == account_id))
    if not acc_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

    reports_q = await db.execute(
        select(AccountReport)
        .where(AccountReport.account_id == account_id)
        .order_by(AccountReport.generated_at.desc())
    )
    reports = reports_q.scalars().all()

    from app.database.schemas import ReportSummary
    return APIResponse(
        success=True,
        data=[ReportSummary.model_validate(r).model_dump() for r in reports],
    )
