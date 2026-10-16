from automation.intelligence.evidence_merger import EvidenceMerger
from automation.intelligence.models import CompanyEvidence


def make_evidence(
    source="generic",
    title="Test Company",
    url="https://example.com",
    snippet="Test snippet",
    company_name="Test Company",
    website=None,
    email=None,
    phone=None,
    location=None,
    confidence=0.5,
):
    return CompanyEvidence(
        source=source,
        title=title,
        url=url,
        snippet=snippet,
        company_name=company_name,
        website=website,
        email=email,
        phone=phone,
        location=location,
        confidence=confidence,
    )


def test_empty_evidence_returns_none():
    merger = EvidenceMerger()

    result = merger.merge([])

    assert result is None


def test_highest_confidence_evidence_is_base():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="generic",
            title="Low Confidence",
            confidence=0.5,
        ),
        make_evidence(
            source="linkedin",
            title="High Confidence",
            confidence=0.95,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.title == "High Confidence"
    assert result.source == "linkedin"
    assert result.confidence == 0.95


def test_missing_fields_are_merged():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="linkedin",
            company_name="Test Company",
            confidence=0.95,
        ),
        make_evidence(
            source="generic",
            website="https://testcompany.com",
            phone="+123456789",
            location="Texas",
            confidence=0.8,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.website == "https://testcompany.com"
    assert result.phone == "+123456789"
    assert result.location == "Texas"


def test_highest_confidence_email_is_selected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="generic",
            email="info@testcompany.com",
            confidence=0.7,
        ),
        make_evidence(
            source="website",
            email="contact@testcompany.com",
            confidence=0.9,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.email == "contact@testcompany.com"


def test_placeholder_email_is_rejected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="website",
            email="filler@godaddy.com",
            confidence=0.95,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.email is None


def test_real_email_beats_placeholder_email():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="website",
            email="filler@godaddy.com",
            confidence=0.95,
        ),
        make_evidence(
            source="generic",
            email="contact@testcompany.com",
            confidence=0.7,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.email == "contact@testcompany.com"


def test_invalid_email_is_rejected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="website",
            email="not-an-email",
            confidence=0.95,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.email is None


def test_blocked_website_is_rejected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="linkedin",
            website="https://linkedin.com/company/test",
            confidence=0.95,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.website is None


def test_real_website_is_selected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="linkedin",
            website="https://linkedin.com/company/test",
            confidence=0.95,
        ),
        make_evidence(
            source="website",
            website="https://testcompany.com",
            confidence=0.8,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.website == "https://testcompany.com"


def test_sources_are_collected():
    merger = EvidenceMerger()

    evidence = [
        make_evidence(
            source="linkedin",
            confidence=0.95,
        ),
        make_evidence(
            source="website",
            confidence=0.8,
        ),
        make_evidence(
            source="linkedin",
            confidence=0.7,
        ),
    ]

    result = merger.merge(evidence)

    assert result is not None
    assert result.sources == [
        "linkedin",
        "website",
    ]