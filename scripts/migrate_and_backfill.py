"""
Migration and backfill script:
1. Adds missing columns to the `opportunities` table in SQLite/PostgreSQL.
2. Backfills all AI opportunities from existing completed account reports.
"""
import json
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(r"e:\kaboom\enterprise-gtm-intelligence-agent\backend\gtm_intelligence.db")

def run():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. Inspect existing columns
    cur.execute("PRAGMA table_info(opportunities)")
    existing_cols = {row[1].lower() for row in cur.fetchall()}
    print("Existing columns:", sorted(existing_cols))

    needed = [
        ("report_id", "VARCHAR(36)"),
        ("opportunity_title", "VARCHAR(255)"),
        ("description", "TEXT"),
        ("business_rationale", "TEXT"),
        ("relevant_product", "VARCHAR(255)"),
        ("confidence_level", "VARCHAR(50)"),
        ("validation_question", "TEXT"),
        ("recommended_action", "TEXT"),
        ("supporting_evidence", "JSON"),
    ]

    for col, col_type in needed:
        if col.lower() not in existing_cols:
            print(f"Adding column '{col}' ({col_type})...")
            cur.execute(f"ALTER TABLE opportunities ADD COLUMN {col} {col_type}")

    con.commit()

    # 2. Backfill from account_reports
    cur.execute("SELECT report_id, account_id, report_json, generated_at FROM account_reports WHERE status='complete'")
    reports = cur.fetchall()
    print(f"Found {len(reports)} completed reports.")

    backfilled = 0
    for rid, aid, rjson, gen_at in reports:
        if not rjson:
            continue
        data = json.loads(rjson) if isinstance(rjson, str) else rjson
        opps = data.get("opportunities", [])
        for o in opps:
            title = o.get("opportunity_title")
            if not title:
                continue

            cur.execute("SELECT 1 FROM opportunities WHERE account_id=? AND opportunity_title=?", (aid, title))
            if cur.fetchone():
                print(f"Already exists: '{title}'")
                continue

            cur.execute("""
                INSERT INTO opportunities (
                    opportunity_id, account_id, report_id, opportunity_title,
                    description, business_rationale, relevant_product,
                    confidence_level, validation_question, recommended_action,
                    supporting_evidence, stage, is_ai_generated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), aid, rid, title,
                o.get("description"), o.get("business_rationale"), o.get("relevant_product"),
                o.get("confidence_level", "low"), o.get("validation_question"), o.get("recommended_action"),
                json.dumps(o.get("supporting_evidence", [])),
                "qualification" if o.get("confidence_level") == "high" else "prospecting",
                1, gen_at
            ))
            backfilled += 1
            print(f"Inserted opportunity: '{title}' for account {aid}")

    con.commit()
    print(f"\nMigration complete. Backfilled {backfilled} AI-generated opportunities.")

    cur.execute("SELECT COUNT(*) FROM opportunities WHERE is_ai_generated=1")
    print("Total AI-generated opportunities in table:", cur.fetchone()[0])
    con.close()

if __name__ == "__main__":
    run()
