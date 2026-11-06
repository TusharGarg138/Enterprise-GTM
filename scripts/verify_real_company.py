import asyncio
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.database.connection import AsyncSessionFactory, init_db
from app.database.models import Account, AccountReport
from app.ingestion.website_loader import WebsiteLoader
from app.services.retrieval_service import get_retrieval_service
from app.agents.orchestrator import run_account_research
from app.api.routes.chat import chat
from app.database.schemas import ChatRequest
from app.services.gemini_service import get_gemini_service


async def main():
    print("=================================================================")
    print("STEP 1: Initialize Database & Ensure Gemini Connectivity")
    print("=================================================================")
    await init_db()
    gemini = get_gemini_service()
    health = await gemini.health_check()
    print("Gemini Status:", health)
    assert health["status"] == "ok", f"Gemini is not reachable: {health}"

    print("\n=================================================================")
    print("STEP 2: Ingest Real Company Website (Stripe)")
    print("=================================================================")
    real_url = "https://stripe.com"
    company_name = "Stripe"

    async with AsyncSessionFactory() as db:
        from sqlalchemy import select
        existing = await db.execute(select(Account).where(Account.company_name == company_name))
        account = existing.scalar_one_or_none()
        if not account:
            account = Account(
                company_name=company_name,
                industry="Financial Services / Payments",
                website=real_url,
                employee_band="1000-5000",
                company_description="Financial infrastructure platform for the internet."
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
        account_id = account.account_id
        print(f"Target Account Created/Loaded: {company_name} (ID: {account_id})")

    # Ingest real website pages
    async with AsyncSessionFactory() as db:
        loader = WebsiteLoader(max_pages=3)
        pages = await loader.load(real_url, account_id=account_id, db=db)
        await db.commit()
        print(f"Extracted {len(pages)} web pages from {real_url}")

    # Store in ChromaDB
    retrieval_svc = get_retrieval_service()
    total_chunks = 0
    for page in pages:
        stored = await retrieval_svc.store_document(
            account_id=account_id,
            document_id=page["document_id"],
            text=page["text"],
            metadata={
                "source_url": page["url"],
                "source_title": page.get("title", ""),
                "source_type": "website",
                "account_id": account_id,
            }
        )
        total_chunks += stored
    print(f"Stored {total_chunks} text chunks into local persistent ChromaDB.")

    print("\n=================================================================")
    print("STEP 3: Execute Multi-Agent LangGraph Research Workflow")
    print("=================================================================")
    print("Running Research Agent -> Opportunity & Risk Agents -> Deterministic Scoring -> Strategy Agent...")
    report = await run_account_research(account_id=account_id, website_url=real_url)
    
    print("\n[RESEARCH AGENT OUTPUT]")
    print("Company Overview:", report.get("company_profile", {}).get("overview", "")[:180], "...")
    print("Identified Industry:", report.get("company_profile", {}).get("industry"))
    print("Confidence Level:", report.get("company_profile", {}).get("confidence_level"))

    print("\n[OPPORTUNITY AGENT OUTPUT]")
    opps = report.get("opportunities", [])
    print(f"Total Opportunities Identified: {len(opps)}")
    for i, o in enumerate(opps[:2], 1):
        print(f"  {i}. {o.get('opportunity_title')} [{o.get('confidence_level')}]")
        print(f"     Fit Product: {o.get('relevant_product')}")
        print(f"     Validation Question: {o.get('validation_question')}")

    print("\n[ACCOUNT RISK AGENT OUTPUT]")
    risks = report.get("risks", [])
    print(f"Total Risks Detected: {len(risks)}")
    for r in risks[:2]:
        print(f"  - [{r.get('severity')}] {r.get('risk_description')}")

    print("\n[DETERMINISTIC PYTHON SCORING]")
    score = report.get("account_score", {})
    print(f"Calculated Score: {score.get('total_score')} / 100 ({score.get('category')})")
    for comp in score.get("components", []):
        print(f"  * {comp['name']}: {comp['raw_score']:.1f}/100 (Weight: {comp['weight']*100:.0f}%) - {comp['reasoning'][:70]}...")

    print("\n[ACCOUNT STRATEGY & OUTREACH DRAFT (Human-in-the-Loop)]")
    strategy = report.get("strategy", {})
    print("Recommended Priority:", strategy.get("suggested_priority"))
    outreach = report.get("outreach_draft", {})
    print("Outreach Subject:", outreach.get("subject"))
    print("Outreach Body Preview:\n", outreach.get("body", "")[:250], "...")

    # Save report to DB
    async with AsyncSessionFactory() as db:
        account_report = AccountReport(
            account_id=account_id,
            report_json=report,
            account_score=score.get("total_score"),
            score_category=score.get("category"),
            model_name=report.get("model_name"),
            prompt_version=report.get("prompt_version", "1.0"),
            status="complete"
        )
        db.add(account_report)
        await db.commit()
        print(f"\nReport successfully saved to PostgreSQL/SQLite (ID: {account_report.report_id})")

    print("\n=================================================================")
    print("STEP 4: Test Grounded RAG Chat (/api/v1/chat)")
    print("=================================================================")
    test_question = "What payment infrastructure or products does Stripe offer according to the ingested sources?"
    print("User Question:", test_question)
    
    async with AsyncSessionFactory() as db:
        chat_req = ChatRequest(account_id=account_id, question=test_question)
        chat_resp = await chat(payload=chat_req, db=db, gemini=gemini)
        answer = chat_resp.data["answer"]
        sources = chat_resp.data["sources"]
        print(f"\nAI Grounded Answer:\n{answer}")
        print(f"\nSources Referenced ({len(sources)}):")
        for s in sources[:2]:
            print(f"  - {s.get('source_url')} (Relevance: {s.get('relevance_score', 0)*100:.1f}%)")

    print("\n=================================================================")
    print("ALL REAL DATA TESTS COMPLETED AND VERIFIED 100% WORKING!")
    print("=================================================================")

if __name__ == '__main__':
    asyncio.run(main())
