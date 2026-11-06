# System Architecture — Enterprise GTM Intelligence Agent

## 1. High-Level Architecture Overview

```
                      +-----------------------------+
                      |   Public Company Websites   |
                      |   Synthetic CRM CSV Data    |
                      +--------------+--------------+
                                     |
                                     v
                        DATA INGESTION PIPELINE
                     (SSRF Guard, Cleaner, Chunker)
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
             CHROMA DB (Local)              SQLITE DATABASE (Zero-Docker)
             Vector Chunks & Embeddings     Structured CRM Records:
             (all-MiniLM-L6-v2)             Accounts, Contacts,
                                            Activities, Opportunities
                     |                               |
                     +---------------+---------------+
                                     |
                                     v
                             FASTAPI BACKEND
                     (Centralized Reusable Gemini Service)
                                     |
                                     v
                         LANGGRAPH ORCHESTRATION
                                     |
                                     v
                            [ Research Agent ]
                                     |
                     +---------------+---------------+
                     |                               |
                     v                               v
          [ Opportunity Agent ]              [ Risk Agent ]
                     |                               |
                     +---------------+---------------+
                                     |
                                     v
                       [ Business Scoring Engine ]
                        (Deterministic Python Logic)
                                     |
                                     v
                            [ Strategy Agent ]
                                     |
                                     v
                        [ Report Assembly & Store ]
                                     |
                                     v
                           REACT SAAS DASHBOARD
```

---

## 2. Component Design & Separation of Concerns

### A. Data Ingestion & Sanitization
1. **SSRF Guard (`app/core/security.py`)**: Restricts all outbound HTTP calls to public schemes (`http`, `https`) and blocks loopback, private RFC-1918 IPv4 ranges, IPv6 localhost, and cloud metadata hostnames (`169.254.169.254`).
2. **Text Cleaner & Chunker (`app/ingestion/chunker.py`)**: Strips scripts, navigation, headers, footers, and normalizes sentence boundaries with 64-character overlap.
3. **CSV Validation Engine (`app/ingestion/csv_loader.py`)**: Validates columns, date formats, deal value types, and foreign keys against existing account records.

### B. Vector Storage & RAG Pipeline
1. **Local Sentence Transformers**: Uses `all-MiniLM-L6-v2` locally without calling external embedding APIs.
2. **ChromaDB**: Embedded persistent vector store located at `./chroma_data`. All documents carry metadata for account-scoped retrieval: `where={"account_id": account_id}`.
3. **Prompt Injection Defense**: Retrieved content is wrapped in clear `[BEGIN RETRIEVED DATA]` delimiters and sanitized for instruction override keywords.

### C. Multi-Agent Orchestration (LangGraph)
- **Shared Typed State**: Defined in `app/agents/state.py` (`GTMAgentState`).
- **Execution Order**:
  1. `research`: Extracts structured company profile and verifies citations.
  2. `opportunity` & `risk`: Execute concurrently over the shared context.
  3. `scoring`: Deterministic scoring algorithm runs on combined outputs.
  4. `strategy`: Produces recommended actions and outreach draft.
  5. `report`: Validates output against Pydantic schema and stores in PostgreSQL.

### D. Deterministic Scoring Logic
Scoring is calculated strictly in Python (`app/services/scoring_service.py`), not by the LLM:
$$\text{Score} = 0.35 \times \text{ProductFit} + 0.25 \times \text{Engagement} + 0.20 \times \text{GrowthSignals} + 0.20 \times \text{CRMQuality}$$
- Missing data is treated neutrally (50 points baseline), never penalizing an account due to sparse records.

### E. Human-in-the-Loop Governance
All outreach drafts and recommended CRM modifications are generated with status `Pending Approval`. External actions are never executed autonomously.
