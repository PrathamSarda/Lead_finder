Project context:

I am building a professional freelance project called "Company Lead Finder" for a client.

The client owns a booktelling company called Prokizen Global LLP.

The goal is NOT LinkedIn automation anymore.

The goal is:

Automatically discover around 80 US companies per day that have approximately 1–20 employees and provide their contact information to the client.

The client will provide login credentials for several job websites.

Current planned websites:

- Indeed
- ZipRecruiter
- Glassdoor
- Monster
- CareerBuilder
- SimplyHired
- Snagajob

The workflow should be:

1. Login to each website.
2. Search for companies according to filters.
3. Extract company information.
4. Remove duplicates across all sources.
5. Find the company's official website.
6. Visit the official website.
7. Extract email, phone, contact page, and other useful contact information.
8. Save everything into PostgreSQL.
9. Show results on a React dashboard.
10. Export today's qualified leads as Excel.

The application should be modular because new websites may be added later.


Architecture

Current project architecture:

company-lead-finder/

automation/
    browser/
    cache/
        companies/
        websites/
        emails/

    enrichment/
        website_fetcher.py
        contact_page_finder.py

    extractors/
        email_extractor.py
        regex_patterns.py

    models/
        company_lead.py
        search_filters.py

    normalizer/

    sources/
        base_source.py
        google/
        indeed/
        linkedin/
        wellfound/

    storage/

    utils/

    workers/
        search_worker.py
        enrichment_worker.py

backend/
    FastAPI
    PostgreSQL

frontend/
    React


Coding Rules
While helping me code, follow these rules:

1. Never redesign the architecture unless absolutely necessary.

2. Build one module completely before starting another.

3. Every coding session should end with a working feature.

4. Never create empty placeholder files unless they are required immediately.

5. Prefer reusable modules.

6. Avoid code duplication.

7. Keep production code and testing code logically separated, but do not force refactoring during active development.

8. Every module should have only one responsibility.

9. We use Playwright for browser automation.

10. The code should be production quality because this is a paid client project.

Current Progress
Completed:

✔ Project architecture
✔ FastAPI backend
✔ React frontend
✔ Database models
✔ Company model
✔ SearchFilters
✔ CompanyLead
✔ BaseSource abstraction
✔ Search Worker
✔ Dummy Google pipeline
✔ Website fetching
✔ Email extraction using regex

Current status:

We have NOT started implementing the real website connectors yet because the client's office was closed and I do not yet have access to the logged-in accounts.

The next development task is to build the Lead Enrichment Engine before implementing the first website connector.

Immediate Goal
Current sprint:

Build the Lead Enrichment Engine.

The objective is:

Given a company website,

↓

Download homepage

↓

Extract emails

↓

Find Contact/About pages

↓

Visit those pages

↓

Extract additional emails and phone numbers

↓

Return all contact information.

We will later plug this enrichment engine into every website connector (Indeed, Monster, Glassdoor, etc.).

Do not redesign the project.

Continue from this point.

How I want ChatGPT to behave
Act as the lead software architect for this project.

Do not overengineer.

Do not keep changing the architecture.

If you recommend changing the architecture, explain why and whether it is worth changing at this stage.

Think like a senior backend engineer building a production SaaS application.

Prioritize maintainability, modularity, and delivering value to the client.

If I make a mistake, correct me.

If the architecture is already good enough, continue coding instead of redesigning.