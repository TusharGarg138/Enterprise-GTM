"""
Ingestion API routes: website scraping and CSV upload.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import validate_url
from app.database.schemas import APIResponse, CSVIngestionResult, WebsiteIngestionRequest

router = APIRouter()
logger = get_logger(__name__)


@router.post("/ingestion/website", response_model=APIResponse)
async def ingest_website(
    payload: WebsiteIngestionRequest,
    db: AsyncSession = Depends(get_database),
) -> APIResponse:
    """
    Ingest a company website: validate URL, scrape pages, chunk text, store embeddings.
    Returns job status immediately; actual ingestion runs in background.
    """
    from sqlalchemy import select
    from app.database.models import Account

    # Verify account exists
    result = await db.execute(select(Account).where(Account.account_id == payload.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{payload.account_id}' not found.")

    # Validate URL for SSRF safety
    try:
        safe_url = validate_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Import ingestion service
    from app.ingestion.website_loader import WebsiteLoader
    from app.services.embedding_service import get_embedding_service
    from app.services.retrieval_service import get_retrieval_service

    max_pages = payload.max_pages or settings.INGESTION_MAX_PAGES

    try:
        loader = WebsiteLoader(max_pages=max_pages)
        pages = await loader.load(safe_url, account_id=payload.account_id, db=db)

        if not pages:
            return APIResponse(
                success=True,
                message="Website was accessible but no content could be extracted.",
                data={"pages_ingested": 0, "account_id": payload.account_id},
            )

        # Store chunks in ChromaDB
        retrieval_svc = get_retrieval_service()
        chunks_stored = 0
        for page in pages:
            stored = await retrieval_svc.store_document(
                account_id=payload.account_id,
                document_id=page["document_id"],
                text=page["text"],
                metadata={
                    "source_url": page["url"],
                    "source_title": page.get("title", ""),
                    "source_type": "website",
                    "account_id": payload.account_id,
                },
            )
            chunks_stored += stored

        logger.info(
            "Website ingested: %s pages, %d chunks for account %s",
            len(pages), chunks_stored, payload.account_id,
        )
        return APIResponse(
            success=True,
            message=f"Successfully ingested {len(pages)} page(s) ({chunks_stored} chunks).",
            data={
                "pages_ingested": len(pages),
                "chunks_stored": chunks_stored,
                "account_id": payload.account_id,
            },
        )
    except Exception as exc:
        logger.error("Website ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {type(exc).__name__}")


@router.post("/ingestion/csv", response_model=APIResponse)
async def ingest_csv(
    db: AsyncSession = Depends(get_database),
    file: UploadFile = File(...),
    csv_type: str = Form(..., description="Type: accounts | contacts | activities | opportunities"),
) -> APIResponse:
    """
    Upload and validate a CRM CSV file. Inserts valid rows into PostgreSQL.
    Returns row-level error details for invalid records.
    """
    allowed_types = {"accounts", "contacts", "activities", "opportunities"}
    if csv_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"csv_type must be one of: {', '.join(sorted(allowed_types))}",
        )

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted.")

    # Read and validate size
    content = await file.read()
    if len(content) > settings.CSV_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.CSV_MAX_FILE_SIZE // 1024 // 1024} MB",
        )

    # Import and use the CSV loader
    from app.ingestion.csv_loader import CSVLoader
    loader = CSVLoader(db=db)
    result: CSVIngestionResult = await loader.load(
        content=content,
        csv_type=csv_type,
        file_name=file.filename,
    )

    return APIResponse(
        success=True,
        message=(
            f"CSV processed: {result.rows_inserted} inserted, "
            f"{result.rows_skipped} skipped, {len(result.errors)} errors."
        ),
        data=result.model_dump(),
    )
