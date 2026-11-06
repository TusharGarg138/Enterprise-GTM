<div align="center">

```
  ______       _                                  _____ _______ __  __ 
 |  ____|     | |                                / ____|__   __|  \/  |
 | |__   _ __ | |_ ___ _ __ _ __  _ __ _   ___  | |  __   | |  | \  / |
 |  __| | '_ \| __/ _ \ '__| '_ \| '__| | / __| | | |_ |  | |  | |\/| |
 | |____| | | | ||  __/ |  | |_) | |  | |_\__ \ | |__| |  | |  | |  | |
 |______|_| |_|\__\___|_|  | .__/|_|   \__,___/  \_____|  |_|  |_|  |_|
                           | |                                         
                           |_|                                         
```

# 🚀 Enterprise GTM Intelligence Agent
### *Autonomous Multi-Agent Go-to-Market Research, ICP Scoring & Strategic Sales Orchestration*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Async%20Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph%20StateGraph-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Vector DB](https://img.shields.io/badge/Retrieval-ChromaDB%20Hybrid%20RAG-7C3AED?style=for-the-badge)](https://www.trychroma.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>A production-grade multi-agent autonomous system built to orchestrate enterprise go-to-market workflows, conduct automated account enrichment, run deterministic ICP qualification scoring, and generate targeted sales battlecards at scale.</b>
</p>

---

</div>

## 📌 Table of Contents
- [✨ System Architecture & Features](#-system-architecture--features)
- [🤖 Multi-Agent Graph Workflow](#-multi-agent-graph-workflow)
- [📂 Archive & Directory Structure](#-archive--directory-structure)
- [⚙️ Technical Specifications](#-technical-specifications)
- [🚀 Quickstart & Setup Guide](#-quickstart--setup-guide)
- [📊 API Endpoints & Interfaces](#-api-endpoints--interfaces)
- [📦 Packaging into `enterprise-gtm-intelligence-agent.zip`](#-packaging-into-enterprise-gtm-intelligence-agentzip)
- [📜 License & Citation](#-license--citation)

---

## ✨ System Architecture & Features

* **Deterministic Multi-Agent Orchestration:** Powered by **LangGraph** `StateGraph`, decomposing open-ended commercial prospecting into coordinated, stateful agent steps with automatic fallback handling.
* **Deep Account Research & Web Ingestion:** Gathers live firmographic, technographic, and leadership signals using dynamic scrapers and semantic text chunking.
* **Hybrid RAG Semantic Memory:** Leverages **ChromaDB** with dense embeddings and metadata filtering to cross-reference target accounts against existing winning deal patterns.
* **Algorithmic ICP Propensity Scoring:** Evaluates companies against customizable Ideal Customer Profile (ICP) criteria, providing clear mathematical justifications alongside executive summaries.
* **Automated Deliverables:** Generates structured **Account Dossiers**, **Executive Briefings**, **Risk & Objection Flags**, and **Personalized Outreach Sequences**.

---

## 🤖 Multi-Agent Graph Workflow

The system uses dedicated specialist agents collaborating over a unified state channel:

```
               ┌─────────────────────────────────┐
               │    Raw Prospect / Target Lead   │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │       Orchestrator Agent        │
               │  • Validates Input / Entity IDs │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │         Research Agent          │
               │  • Web & Technographic Crawl    │
               │  • Semantic Chunking & ChromaDB │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │      ICP Scoring Specialist     │
               │  • Propensity Weights Matrix    │
               │  • Budget & Decision Match      │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │       Risk & Objection Agent    │
               │  • Red Flags & Competitor Locks │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │     GTM Strategy & Outreach     │
               │  • Battlecards & Email Vectors  │
               └────────────────┬────────────────┘
                                │
                                ▼
               ┌─────────────────────────────────┐
               │  Structured JSON + Executive UI │
               └─────────────────────────────────┘
```

---

## 📂 Archive & Directory Structure

Inside `enterprise-gtm-intelligence-agent.zip`, the project is structured as follows:

```plaintext
enterprise-gtm-intelligence-agent/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py        # LangGraph StateGraph coordinator
│   │   ├── researcher.py          # Account intelligence & web enrichment agent
│   │   ├── scorer.py              # ICP scoring & qualification algorithm
│   │   ├── risk_analyzer.py       # Churn & competitor blocker analysis
│   │   └── strategist.py          # Value proposition & outreach synthesis
│   ├── core/
│   │   ├── config.py              # Environment settings & LLM configuration
│   │   └── state.py               # Shared Pydantic agent state schema
│   ├── rag/
│   │   ├── vector_store.py        # ChromaDB setup, collections & embeddings
│   │   └── retriever.py           # Hybrid dense retrieval pipeline
│   ├── api/
│   │   ├── routes.py              # REST API endpoints for agent triggers
│   │   └── models.py              # Request/response validation schemas
│   └── main.py                    # FastAPI application entrypoint
├── dashboard/                     # Executive frontend interface
│   ├── src/                       # React / TypeScript dashboard components
│   ├── package.json
│   └── tailwind.config.js
├── tests/
│   ├── test_agents.py             # Agent state transition & output tests
│   └── test_api.py                # Endpoint integration tests
├── requirements.txt               # Backend Python dependencies
├── .env.example                   # Environment variable template
├── Dockerfile                     # Containerization spec
└── README.md                      # Complete system documentation
```

---

## ⚙️ Technical Specifications

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Agent Framework** | LangGraph / LangChain | Stateful graph loops, routing, and tool-calling |
| **Foundation Model**| Google Gemini / Anthropic Claude | Reasoning, evaluation, and structured text generation |
| **Backend Engine** | Python 3.11+ / FastAPI / AsyncIO | High-throughput asynchronous orchestration API |
| **Vector Database**| ChromaDB | Semantic knowledge retrieval and account profiling |
| **Data Validation** | Pydantic v2 | Strict JSON schema enforcement across agent states |
| **Frontend UI** | React, TypeScript, Tailwind CSS | Real-time agent monitoring and executive dossier viewer |

---

## 🚀 Quickstart & Setup Guide

### 1. Extract the Archive

```bash
unzip enterprise-gtm-intelligence-agent.zip -d enterprise-gtm-intelligence-agent
cd enterprise-gtm-intelligence-agent
```

### 2. Environment Setup

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate       # On Windows: .\venv\Scripts\activate

pip install -r requirements.txt
```

Create your `.env` configuration:

```bash
cp .env.example .env
```

Add your API credentials:

```ini
GEMINI_API_KEY=your_api_key_here
CHROMA_PERSIST_DIRECTORY=./chroma_db
APP_ENV=development
```

### 3. Start the Backend API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access interactive Swagger docs at: **`http://localhost:8000/docs`**

### 4. (Optional) Run the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

---

## 📊 API Endpoints & Interfaces

### Run GTM Prospecting Pipeline

```http
POST /api/v1/analyze-account
Content-Type: application/json

{
  "company_name": "Acme Corp",
  "domain": "acmecorp.com",
  "icp_criteria": {
    "industry": "B2B SaaS",
    "target_revenue_min": 10000000,
    "tech_stack_requirements": ["Python", "AWS"]
  }
}
```

#### Sample Response:

```json
{
  "account_id": "acc_89f2a01",
  "company_name": "Acme Corp",
  "icp_score": 92.4,
  "fit_status": "STRONG_FIT",
  "key_findings": [
    "Expanding cloud infrastructure engineering headcount by 35% YoY",
    "Active migration toward distributed microservices"
  ],
  "recommended_strategy": {
    "primary_angle": "Infrastructure reliability and deployment velocity",
    "decision_maker_title": "VP of Engineering / Head of DevOps",
    "personalized_hook": "Noticed recent job openings focused on Python microservices..."
  }
}
```

---

## 📦 Packaging into `enterprise-gtm-intelligence-agent.zip`

To re-bundle the project into a clean archive without runtime caches or dependencies:

```bash
# Clean out build artifacts, virtual environments, and caches
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
rm -rf venv node_modules .DS_Store __MACOSX

# Create the archive
zip -r enterprise-gtm-intelligence-agent.zip . -x "venv/*" "node_modules/*" "*.git*" ".DS_Store" "__MACOSX/*"
```

---

## 📜 License & Citation

* **License:** Licensed under the [MIT License](LICENSE).
* **Architecture:** Designed and developed for scalable, automated enterprise go-to-market workflows.