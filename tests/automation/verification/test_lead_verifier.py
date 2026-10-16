import pytest

from automation.intelligence.models import CompanyEvidence, CompanyInput
from automation.verification.lead_verifier import (
    LeadVerifier,
    check_geographic_conflict,
    format_phone_as_text,
    validate_email_ownership,
)
from automation.verification.models import VerificationStatus


def test_format_phone_as_text_prevents_scientific_notation():
    phone = "+14782144236"
    formatted = format_phone_as_text(phone)
    assert formatted == "+1 (478) 214-4236"
    assert not formatted.isdigit()
    assert "(" in formatted and ")" in formatted


def test_validate_email_ownership_rejects_directory_support():
    accepted, reason = validate_email_ownership(
        email="support@brokersnapshot.com",
        website="https://brokersnapshot.com",
        company_name="Richard D Austin",
    )
    assert accepted is None
    assert "directory" in reason


def test_validate_email_ownership_accepts_company_domain():
    accepted, reason = validate_email_ownership(
        email="hello@acmebrickmaterials.com",
        website="https://acmebrickmaterials.com",
        company_name="Acme Brick Sales Co",
    )
    assert accepted == "hello@acmebrickmaterials.com"
    assert reason is None


def test_validate_email_ownership_accepts_freemail_matching_company():
    accepted, reason = validate_email_ownership(
        email="cherokeeculvert@att.net",
        website="https://cherokeeculvert.com",
        company_name="Cherokee Culvert Company Inc",
    )
    assert accepted == "cherokeeculvert@att.net"
    assert reason is None


def test_check_geographic_conflict():
    # Alabama phone (+1 205...) with PA state
    conflict, desc = check_geographic_conflict("PA", "+12059084401")
    assert conflict is True
    assert "Alabama" in desc

    # Georgia phone (+1 478...) with GA state
    conflict, desc = check_geographic_conflict("GA", "+14782144236")
    assert conflict is False


def test_lead_verifier_verifies_cherokee_culvert():
    verifier = LeadVerifier()
    company = CompanyInput(name="CHEROKEE CULVERT COMPANY INC", city="MACON", state="GA")
    evidence = CompanyEvidence(
        source="ddgs",
        title="Cherokee Culvert Company Inc",
        url="https://cherokeeculvert.com/",
        snippet="Macon, GA culvert supplier",
        company_name="Cherokee Culvert Company Inc",
        website="https://cherokeeculvert.com/",
        email="cherokeeculvert@att.net",
        phone="+14782144236",
        location="Macon, GA",
        confidence=1.0,
        sources=["ddgs", "enrichment"],
    )

    verified = verifier.verify(company, evidence)
    assert verified.status == VerificationStatus.VERIFIED.value
    assert verified.website == "https://cherokeeculvert.com/"
    assert verified.email == "cherokeeculvert@att.net"
    assert verified.phone == "+1 (478) 214-4236"


def test_lead_verifier_rejects_directory_domain():
    verifier = LeadVerifier()
    company = CompanyInput(name="FELIX ANCHUSTEGUI TRUCKING INC", city="NAMPA", state="ID")
    evidence = CompanyEvidence(
        source="generic",
        title="Felix Anchustegui Trucking Inc",
        url="https://truckingdatabase.com/",
        snippet="Details on truckingdatabase",
        company_name="Felix Anchustegui Trucking Inc",
        website="https://truckingdatabase.com",
        confidence=0.8,
    )

    verified = verifier.verify(company, evidence)
    assert verified.status == VerificationStatus.UNRESOLVED.value
    assert verified.website is None
    assert "directory_domain" in verified.status_reason


def test_lead_verifier_rejects_foreign_domain_for_us_company():
    verifier = LeadVerifier()
    company = CompanyInput(name="JAMES AUSTIN COMPANY", city="MARS", state="PA")
    evidence = CompanyEvidence(
        source="generic",
        title="James Austin Company",
        url="http://james-austin.co.uk",
        snippet="UK steel fabricators",
        company_name="James Austin Company",
        website="http://james-austin.co.uk",
        confidence=0.9,
    )

    verified = verifier.verify(company, evidence)
    assert verified.status == VerificationStatus.UNRESOLVED.value
    assert verified.website is None
    assert "foreign_cctld" in verified.status_reason


def test_lead_verifier_flags_name_and_location_mismatch():
    verifier = LeadVerifier()
    company = CompanyInput(name="AMERICAN INDUSTRIAL CONTRACTING INC", city="SEWICKLEY", state="PA")
    evidence = CompanyEvidence(
        source="ddgs",
        title="American Industrial Construction",
        url="https://www.americanindustrialconstruction.com/",
        snippet="Alabama construction",
        company_name="American Industrial Construction",
        website="https://www.americanindustrialconstruction.com/",
        phone="+12059084401",
        confidence=0.9,
    )

    verified = verifier.verify(company, evidence)
    assert verified.status == VerificationStatus.NEEDS_REVIEW.value
    assert "discrepancy" in verified.status_reason or "Alabama" in verified.status_reason
