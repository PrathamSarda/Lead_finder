
from app.core.config import settings
from automation.intelligence.models import CompanyEvidence, CompanyInput
from automation.intelligence.llm.website_judge import WebsiteJudge


company = CompanyInput(
    name="American Industrial Contracting",
    city="Pittsburgh",
    state="PA",
)

evidence = [
    CompanyEvidence(
        source="generic",
        title="American Industrial Contracting Inc",
        url="https://aicpittsburgh.com",
        snippet="Industrial contracting company",
        company_name="American Industrial Contracting",
        website="https://aicpittsburgh.com",
        confidence=0.8,
    ),
    CompanyEvidence(
        source="generic",
        title="American Industrial Contracting | Get a Bid",
        url="https://buildzoom.com/contractor/example",
        snippet="Contractor listing",
        company_name="American Industrial Contracting",
        website="https://buildzoom.com",
        confidence=0.85,
    ),
    CompanyEvidence(
        source="generic",
        title="American Industrial Contracting Inc.",
        url="https://2findlocal.com/example",
        snippet="Business directory listing",
        company_name="American Industrial Contracting",
        website="https://2findlocal.com",
        confidence=0.8,
    ),
]

judge = WebsiteJudge(api_key=settings.GEMINI_API_KEY)
result = judge.judge(company, evidence)

if result is None:
    print("No judgment returned. Check the error above.")
else:
    for item in result.candidates:
        print(
            item.classification,
            "|",
            item.url,
            "|",
            item.confidence,
            "|",
            item.reason,
        )