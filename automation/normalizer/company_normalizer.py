from automation.models.company_lead import CompanyLead


def normalize_google(data: dict) -> CompanyLead:
    return CompanyLead(
        company_name=data.get("company_name", ""),
        website=data.get("website"),
        industry=data.get("industry"),
        location=data.get("location"),
        employee_count=data.get("employee_count"),
        source="Google"
    )
    