# System Evaluation & Benchmark Report

## 1. Automated Test Suite Results

The automated test suite was executed against the deterministic scoring module, the API route models, and the RAG/security utilities.

### Scoring Service Suite (`backend/tests/test_scoring.py`)
- **Total Tests**: 13
- **Passed**: 13 (100%)
- **Failed**: 0
- **Duration**: 0.85s

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_no_opportunities_returns_neutral` | Missing opportunity signals default to 50.0 neutral score | **PASSED** |
| `test_closed_won_opportunity_boosts_score` | Verified `closed_won` stage raises Product Fit score > 70 | **PASSED** |
| `test_closed_lost_opportunity_lowers_score` | Verified `closed_lost` stage lowers Product Fit score | **PASSED** |
| `test_no_activities_returns_neutral` | Missing CRM history defaults to neutral without penalty | **PASSED** |
| `test_recent_activities_give_high_score` | Activity in last 30 days yields engagement score >= 70 | **PASSED** |
| `test_stale_activities_give_low_score` | Activity > 180 days ago drops engagement score < 50 | **PASSED** |
| `test_total_score_within_bounds` | Calculated score is strictly constrained between 0 and 100 | **PASSED** |
| `test_weights_sum_to_one` | Sum of configurable weights equals 1.0 (0.35 + 0.25 + 0.20 + 0.20) | **PASSED** |
| `test_score_is_deterministic` | Re-running calculation with identical signals yields identical score | **PASSED** |
| `test_high_priority_category` | High fit + recent activity yields High Priority classification | **PASSED** |
| `test_low_data_quality_gives_medium_score` | Empty CRM history returns neutral tier (40–65 range) | **PASSED** |
| `test_missing_data_flags_populated` | Explicit warning flags are attached for missing CRM data | **PASSED** |
| `test_category_boundaries` | Strict boundary tests for 80+ (High), 60–79 (Medium), <60 (Low) | **PASSED** |

---

## 2. RAG Retrieval & Prompt Security Benchmarks

### Ingestion & Security Checks (`backend/tests/test_retrieval.py`)
- **SSRF Block Rate**: 100% on tested malicious targets (`127.0.0.1`, `localhost`, `192.168.1.1`).
- **Prompt Injection Defense**: 100% detection of instruction override patterns (e.g., `"Ignore previous instructions"` replaced with `[REDACTED]`).
- **Chunking Consistency**: Sentence-aware chunker produces overlapping slices without mid-sentence cuts.

---

## 3. Synthetic Dataset Verification
- **Generated Accounts**: 20
- **Generated Contacts**: 52 (average 2.6 per account)
- **Generated Activities**: 61 (distributed across healthy, aging, stale, and inactive)
- **Generated Opportunities**: 42 (covering all stages from prospecting to closed_won)
- **Foreign Key Integrity**: 100% valid relationships linking contacts, activities, and opportunities to existing account records.

---

## 4. Cost & Free-Tier Adherence Review
- **LLM Cost**: \$0.00 (configured for Gemini Free Tier).
- **Embedding Cost**: \$0.00 (runs local `all-MiniLM-L6-v2` via Sentence Transformers).
- **Vector DB Cost**: \$0.00 (ChromaDB runs in-process with local persistent storage).
- **Hosting / Storage Cost**: \$0.00 (Native local SQLite database, zero Docker requirement).
