"""
CSV ingestion loader with column validation, type checking, FK validation,
duplicate detection, and safe database insertion.
"""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.models import Account, Activity, Contact, Opportunity, Product
from app.database.schemas import CSVIngestionResult

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Column specifications per CSV type
# ---------------------------------------------------------------------------

COLUMN_SPECS: Dict[str, Dict] = {
    "accounts": {
        "required": ["company_name"],
        "optional": ["industry", "website", "employee_band", "company_description"],
    },
    "contacts": {
        "required": ["account_name", "name"],
        "optional": ["role", "email"],
    },
    "activities": {
        "required": ["account_name", "activity_type"],
        "optional": ["activity_date", "notes"],
    },
    "opportunities": {
        "required": ["account_name", "stage"],
        "optional": ["product_name", "deal_value", "close_date"],
    },
}


class CSVLoader:
    """
    Load, validate, and import CRM CSV data into PostgreSQL.
    Foreign-key lookups are done by name (e.g. account_name → account_id).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def load(
        self,
        content: bytes,
        csv_type: str,
        file_name: str,
    ) -> CSVIngestionResult:
        """Parse and import a CSV file. Returns a result summary."""
        result = CSVIngestionResult(
            file_name=file_name,
            rows_processed=0,
            rows_inserted=0,
            rows_skipped=0,
        )

        try:
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        except Exception as exc:
            result.errors.append(f"Could not parse CSV: {exc}")
            return result

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        result.rows_processed = len(df)

        # Validate required columns
        spec = COLUMN_SPECS.get(csv_type, {})
        required = spec.get("required", [])
        missing_cols = [c for c in required if c not in df.columns]
        if missing_cols:
            result.errors.append(
                f"Missing required columns: {', '.join(missing_cols)}. "
                f"Required: {', '.join(required)}"
            )
            return result

        # Dispatch to type-specific handler
        handlers = {
            "accounts": self._import_accounts,
            "contacts": self._import_contacts,
            "activities": self._import_activities,
            "opportunities": self._import_opportunities,
        }
        handler = handlers[csv_type]
        inserted, skipped, errors = await handler(df)

        result.rows_inserted = inserted
        result.rows_skipped = skipped
        result.errors.extend(errors)
        return result

    # ------------------------------------------------------------------
    # Type-specific importers
    # ------------------------------------------------------------------

    async def _import_accounts(
        self, df: pd.DataFrame
    ) -> Tuple[int, int, List[str]]:
        inserted = skipped = 0
        errors: List[str] = []

        for i, row in df.iterrows():
            company_name = str(row.get("company_name", "")).strip()
            if not company_name:
                errors.append(f"Row {i+2}: company_name is required.")
                skipped += 1
                continue

            # Duplicate check by company name
            existing = await self.db.execute(
                select(Account).where(Account.company_name == company_name)
            )
            if existing.scalar_one_or_none():
                logger.debug("Skipping duplicate account: %s", company_name)
                skipped += 1
                continue

            account = Account(
                company_name=company_name,
                industry=self._clean(row.get("industry")),
                website=self._clean(row.get("website")),
                employee_band=self._clean(row.get("employee_band")),
                company_description=self._clean(row.get("company_description")),
            )
            self.db.add(account)
            inserted += 1

        await self.db.flush()
        return inserted, skipped, errors

    async def _import_contacts(
        self, df: pd.DataFrame
    ) -> Tuple[int, int, List[str]]:
        inserted = skipped = 0
        errors: List[str] = []

        account_cache: Dict[str, Optional[str]] = {}

        for i, row in df.iterrows():
            account_name = str(row.get("account_name", "")).strip()
            name = str(row.get("name", "")).strip()

            if not name:
                errors.append(f"Row {i+2}: contact name is required.")
                skipped += 1
                continue

            account_id = await self._resolve_account(account_name, account_cache)
            if not account_id:
                errors.append(f"Row {i+2}: account '{account_name}' not found.")
                skipped += 1
                continue

            contact = Contact(
                account_id=account_id,
                name=name,
                role=self._clean(row.get("role")),
                email=self._clean(row.get("email")),
            )
            self.db.add(contact)
            inserted += 1

        await self.db.flush()
        return inserted, skipped, errors

    async def _import_activities(
        self, df: pd.DataFrame
    ) -> Tuple[int, int, List[str]]:
        inserted = skipped = 0
        errors: List[str] = []
        account_cache: Dict[str, Optional[str]] = {}

        VALID_TYPES = {"call", "email", "meeting", "demo", "note", "task", "other"}

        for i, row in df.iterrows():
            account_name = str(row.get("account_name", "")).strip()
            activity_type = str(row.get("activity_type", "")).strip().lower()

            if activity_type not in VALID_TYPES:
                errors.append(
                    f"Row {i+2}: invalid activity_type '{activity_type}'. "
                    f"Allowed: {', '.join(sorted(VALID_TYPES))}"
                )
                skipped += 1
                continue

            account_id = await self._resolve_account(account_name, account_cache)
            if not account_id:
                errors.append(f"Row {i+2}: account '{account_name}' not found.")
                skipped += 1
                continue

            activity_date = self._parse_date(row.get("activity_date"))

            activity = Activity(
                account_id=account_id,
                activity_type=activity_type,
                activity_date=activity_date,
                notes=self._clean(row.get("notes")),
            )
            self.db.add(activity)
            inserted += 1

        await self.db.flush()
        return inserted, skipped, errors

    async def _import_opportunities(
        self, df: pd.DataFrame
    ) -> Tuple[int, int, List[str]]:
        inserted = skipped = 0
        errors: List[str] = []
        account_cache: Dict[str, Optional[str]] = {}

        VALID_STAGES = {
            "prospecting", "qualification", "proposal",
            "negotiation", "closed_won", "closed_lost"
        }

        for i, row in df.iterrows():
            account_name = str(row.get("account_name", "")).strip()
            stage = str(row.get("stage", "")).strip().lower()

            if stage not in VALID_STAGES:
                errors.append(
                    f"Row {i+2}: invalid stage '{stage}'. "
                    f"Allowed: {', '.join(sorted(VALID_STAGES))}"
                )
                skipped += 1
                continue

            account_id = await self._resolve_account(account_name, account_cache)
            if not account_id:
                errors.append(f"Row {i+2}: account '{account_name}' not found.")
                skipped += 1
                continue

            deal_value = self._parse_float(row.get("deal_value"))
            close_date = self._parse_date(row.get("close_date"))

            opp = Opportunity(
                account_id=account_id,
                stage=stage,
                deal_value=deal_value,
                close_date=close_date,
                is_ai_generated=False,
            )
            self.db.add(opp)
            inserted += 1

        await self.db.flush()
        return inserted, skipped, errors

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    async def _resolve_account(
        self, name: str, cache: Dict[str, Optional[str]]
    ) -> Optional[str]:
        if name in cache:
            return cache[name]
        result = await self.db.execute(
            select(Account.account_id).where(Account.company_name == name)
        )
        account_id = result.scalar_one_or_none()
        cache[name] = account_id
        return account_id

    @staticmethod
    def _clean(value: Any) -> Optional[str]:
        if value is None or str(value).strip() in ("", "nan", "None"):
            return None
        return str(value).strip()

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if not value or str(value).strip() in ("", "nan", "None"):
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        if not value or str(value).strip() in ("", "nan", "None"):
            return None
        try:
            return float(str(value).replace(",", "").replace("$", "").strip())
        except ValueError:
            return None
