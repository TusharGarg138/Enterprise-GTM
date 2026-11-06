# API Documentation — Enterprise GTM Intelligence Agent

Base URL: `http://localhost:8000/api/v1`

---

## 1. System Endpoints

### `GET /health`
Returns system health status for the database and Gemini API connection.
- **Response `200 OK`**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "gemini": "ok",
  "environment": "development",
  "timestamp": "2026-11-05T07:30:00Z"
}
```

---

## 2. Accounts API

### `GET /accounts`
Retrieve paginated company accounts with search, industry filter, and priority score filter.
- **Query Parameters**:
  - `search` (optional string): Case-insensitive match on company name.
  - `industry` (optional string): Industry filter.
  - `score_category` (optional string): `High Priority` | `Medium Priority` | `Low Priority`.
  - `page` (integer, default 1): Page number.
  - `page_size` (integer, default 20): Items per page.

### `POST /accounts`
Create a new company account.
- **Request Body**:
```json
{
  "company_name": "Nexus Dynamics",
  "industry": "Technology",
  "website": "https://nexusdynamics.example.com",
  "employee_band": "200-500",
  "company_description": "Enterprise cloud infrastructure provider."
}
```

### `GET /accounts/{account_id}`
Returns complete account profile including linked contacts, CRM activities, opportunities, and the most recent intelligence report.

---

## 3. Data Ingestion API

### `POST /ingestion/website`
Trigger SSRF-protected website scraping, sentence chunking, embedding, and storage in ChromaDB.
- **Request Body**:
```json
{
  "account_id": "acc-uuid",
  "url": "https://company.example.com",
  "max_pages": 5
}
```

### `POST /ingestion/csv`
Upload and validate synthetic CRM CSV records.
- **Form Data**:
  - `file`: CSV file.
  - `csv_type`: `accounts` | `contacts` | `activities` | `opportunities`.

---

## 4. Research & Multi-Agent Jobs API

### `POST /accounts/{account_id}/research`
Trigger an asynchronous multi-agent research workflow (Status `202 Accepted`).
- **Response**:
```json
{
  "success": true,
  "message": "Research job queued.",
  "data": {
    "job_id": "job-uuid",
    "account_id": "acc-uuid",
    "status": "queued"
  }
}
```

### `GET /research/jobs/{job_id}`
Poll research job status (`queued` | `running` | `complete` | `failed`).

---

## 5. Grounded Q&A / Chat API

### `POST /chat`
Ask questions about an account's ingested website documents and CRM activity.
- **Request Body**:
```json
{
  "account_id": "acc-uuid",
  "question": "What are the primary products and recent strategic initiatives for this company?"
}
```
- **Response**:
```json
{
  "success": true,
  "data": {
    "answer": "Nexus Dynamics provides cloud infrastructure management... [SOURCE: https://nexusdynamics.example.com/products]",
    "sources": [
      {
        "source_url": "https://nexusdynamics.example.com/products",
        "source_title": "Products - Nexus Dynamics",
        "chunk_text": "Our flagship platform delivers multi-cloud orchestration...",
        "relevance_score": 0.8841
      }
    ],
    "account_id": "acc-uuid",
    "is_grounded": true,
    "model_name": "gemini-2.0-flash"
  }
}
```
