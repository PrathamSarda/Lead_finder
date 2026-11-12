# Company Lead Finder

Local lead qualification workflow for small US businesses. Candidate businesses are sourced from active US FMCSA records. Serper Google Maps enriches those records with a likely website, phone, and address; Serper web search finds their LinkedIn company page; Apify checks that company headcount is within the **10–15 employee range**; the system verifies bookkeeping requirements via **company LinkedIn activity OR Indeed job postings** (evaluating whether the company is actively seeking bookkeeping, accounting, tax, or payroll services); Serper finds the decision-maker's public LinkedIn profile (Owner, Founder, CEO, President, Managing Partner); Hunter finds and verifies that named decision-maker's work email (with company website email fallback). All results and verification sources are displayed on the React frontend dashboard and exported to client-ready Excel and CSV reports.

## Workflow

1. Sourcing: Pull active US carrier records from the FMCSA Company Census, optionally filtered by city and state.
2. Local Enrichment: Enrich each record with likely business website, phone, and address via Serper Google Maps.
3. Employee Size Gate: Find the company LinkedIn page and check headcount using Apify. Enforces the **10–15 employee range** (companies outside 10–15 employees are dropped).
4. Bookkeeping Requirement Verification (LinkedIn OR Indeed):
   - **LinkedIn Check**: Evaluate recent company LinkedIn posts using Gemini 3.8 Flash (with rule-based fallback) for bookkeeping, accounting, tax, payroll, and financial scaling needs.
   - **Indeed Check**: If LinkedIn activity does not confirm bookkeeping intent, search Indeed for active job listings (e.g. Bookkeeper, Full Charge Bookkeeper, Staff Accountant, Payroll Specialist, QuickBooks, Tax Preparer).
   - **Confirmation Gate**: Only companies with confirmed bookkeeping requirements via LinkedIn or Indeed advance to qualification.
5. Decision Maker & Email Retrieval: Find the decision-maker's public LinkedIn profile using Serper, then find and verify their work email with Hunter (with website fallback).
6. Dashboard & Export: Show all verified leads, headcount, intent confirmation source (LinkedIn vs Indeed), decision maker, email verification status, and profile URLs directly on the frontend dashboard, and export client-ready CSV and Excel (.xlsx) files.

Serper results can be ambiguous and public LinkedIn data can be incomplete. Review the website, match, employee count, activity dates, and profile links before outreach. A missing public post or profile is not proof a company is closed.

## Local setup

Requirements: Python 3.10+, Node.js 20+, local PostgreSQL for the existing sign-in flow, Serper API key, Apify API token, and Hunter API key. Gemini is optional; without it the deterministic fallback runs. The model is called through its API when enabled; it is not deployed in the client environment. Pipeline history uses the local SQLite database.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SERPER_API_KEY`, `APIFY_API_TOKEN`, and `HUNTER_API_KEY` in `backend/.env`.
Optionally set `GEMINI_API_KEY`. Hunter uses its Email Finder and Email Verifier
API endpoints; account credits and plan limits apply. The default Apify actors can be changed with
`APIFY_LINKEDIN_COMPANY_ACTOR` and `APIFY_LINKEDIN_POSTS_ACTOR` if the client
uses compatible actors. Then start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The PostgreSQL database named in `DATABASE_URL` must be running before the
migration and sign-in. Create the local login account through the backend's
`POST /api/v1/auth/register` endpoint; the current frontend provides sign-in but
does not include an account-registration screen.

### Frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL. In the dashboard choose **Run Lead Discovery Pipeline**,
set a qualified-lead target, optional city/state, and the buying-intent niche.
The API reports the current stage and company while the run executes. Export
qualified records from the dashboard as CSV or Excel.

## Data and privacy

- Provider API keys stay in the local backend configuration and are not sent to the browser.
- FMCSA candidates, run state, and CSV exports are local. Qualified pipeline history is stored in the existing SQLite database under `data/`.
- Serper and Apify API usage may incur charges under the client's plans. Gemini usage is also billed according to its API account when enabled.
- `outputs/` and `data/` contain historical local project data and are not cleared by a run.
