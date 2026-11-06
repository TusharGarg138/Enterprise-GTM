"""
Seed database with pre-generated synthetic CRM records.
Usage: python scripts/seed_database.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.database.connection import AsyncSessionFactory, init_db
from app.ingestion.csv_loader import CSVLoader


async def seed():
    print("1. Initializing database schema...")
    await init_db()
    print("   Database schema created.")

    data_dir = Path(__file__).parent.parent / "data" / "sample_crm"
    files = [
        ("accounts.csv", "accounts"),
        ("contacts.csv", "contacts"),
        ("activities.csv", "activities"),
        ("opportunities.csv", "opportunities"),
    ]

    print("\n2. Loading synthetic CRM records...")
    async with AsyncSessionFactory() as db:
        loader = CSVLoader(db=db)
        for fname, csv_type in files:
            path = data_dir / fname
            if not path.exists():
                print(f"   Warning: {fname} not found at {path}")
                continue

            with open(path, "rb") as f:
                content = f.read()

            result = await loader.load(content, csv_type=csv_type, file_name=fname)
            print(f"   [{csv_type.upper()}] Processed: {result.rows_processed}, Inserted: {result.rows_inserted}, Skipped: {result.rows_skipped}")
            if result.errors:
                print(f"     Errors: {result.errors[:3]}")

        await db.commit()

    print("\n Seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
