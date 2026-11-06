"""
Database connection setup using SQLAlchemy with async support.
Uses psycopg3 (psycopg) driver.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


def _make_async_url(url: str) -> str:
    """Convert a sync SQLAlchemy URL to its async counterpart."""
    # Support both postgresql+psycopg and postgresql+asyncpg drivers
    if url.startswith("postgresql+psycopg://") and "+asyncpg" not in url:
        return url.replace("postgresql+psycopg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def create_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine from application settings."""
    db_url = _make_async_url(settings.DATABASE_URL)
    
    if "sqlite" in db_url:
        engine = create_async_engine(
            db_url,
            echo=settings.DATABASE_ECHO,
            connect_args={"check_same_thread": False},
            future=True,
        )
        logger.info("SQLite database engine created: %s", db_url)
    else:
        engine = create_async_engine(
            db_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DATABASE_ECHO,
            future=True,
        )
        logger.info("Database engine created. Pool size: %d", settings.DATABASE_POOL_SIZE)
    return engine


# Application-level engine and session factory (singletons)
engine: AsyncEngine = create_engine()
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager that yields a database session and handles cleanup."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    async with get_session() as session:
        yield session


async def _ensure_opportunity_columns(conn) -> None:
    """Ensure newly introduced Opportunity columns exist on existing databases."""
    try:
        # Check dialect
        dialect_name = conn.dialect.name
        if dialect_name == "postgresql":
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='opportunities'")
            )
            existing_cols = {row[0].lower() for row in result.fetchall()}
            needed_cols = {
                "report_id": "VARCHAR(36)",
                "opportunity_title": "VARCHAR(255)",
                "description": "TEXT",
                "business_rationale": "TEXT",
                "relevant_product": "VARCHAR(255)",
                "confidence_level": "VARCHAR(50)",
                "validation_question": "TEXT",
                "recommended_action": "TEXT",
                "supporting_evidence": "JSONB",
            }
        else:
            # SQLite
            result = await conn.execute(text("PRAGMA table_info(opportunities)"))
            existing_cols = {row[1].lower() for row in result.fetchall()}
            needed_cols = {
                "report_id": "VARCHAR(36)",
                "opportunity_title": "VARCHAR(255)",
                "description": "TEXT",
                "business_rationale": "TEXT",
                "relevant_product": "VARCHAR(255)",
                "confidence_level": "VARCHAR(50)",
                "validation_question": "TEXT",
                "recommended_action": "TEXT",
                "supporting_evidence": "JSON",
            }

        for col, col_type in needed_cols.items():
            if col.lower() not in existing_cols:
                await conn.execute(text(f"ALTER TABLE opportunities ADD COLUMN {col} {col_type}"))
                logger.info("Migrated schema: added column '%s' to opportunities table.", col)
    except Exception as exc:
        logger.warning("Could not auto-migrate opportunities columns: %s", exc)


async def backfill_report_opportunities() -> int:
    """
    Backfill opportunities from previously completed research reports into the opportunities table.
    Ensures existing research reports populate the Opportunities Hub without duplicates.
    """
    from datetime import datetime
    import uuid
    from sqlalchemy import select
    from app.database.models import AccountReport, Opportunity

    count = 0
    try:
        async with AsyncSessionFactory() as db:
            reports_q = await db.execute(
                select(AccountReport).where(AccountReport.status == "complete")
            )
            reports = reports_q.scalars().all()

            for rep in reports:
                if not rep.report_json:
                    continue
                opps_list = rep.report_json.get("opportunities", [])
                if not opps_list:
                    continue

                for opp_data in opps_list:
                    title = opp_data.get("opportunity_title")
                    if not title:
                        continue

                    # Check if already exists for this report or account
                    check_q = await db.execute(
                        select(Opportunity).where(
                            Opportunity.account_id == rep.account_id,
                            Opportunity.opportunity_title == title,
                        )
                    )
                    existing = check_q.scalar_one_or_none()
                    if not existing:
                        new_opp = Opportunity(
                            opportunity_id=str(uuid.uuid4()),
                            account_id=rep.account_id,
                            report_id=rep.report_id,
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
                            created_at=rep.generated_at or datetime.utcnow(),
                        )
                        db.add(new_opp)
                        count += 1
            if count > 0:
                await db.commit()
                logger.info("Successfully backfilled %d opportunities from previous reports.", count)
    except Exception as exc:
        logger.warning("Opportunity backfill failed: %s", exc)
    return count


async def init_db() -> None:
    """
    Create all tables if they do not already exist.
    Ensure columns exist for sqlite/postgres and backfill opportunities
    from existing completed reports.
    """
    # Import models here to ensure they are registered with Base before create_all
    from app.database import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_opportunity_columns(conn)

    # Backfill opportunities from previously generated reports
    await backfill_report_opportunities()
    logger.info("Database tables and opportunities initialized.")


async def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection check failed: %s", exc)
        return False


async def close_db() -> None:
    """Dispose the engine connection pool cleanly on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed.")
