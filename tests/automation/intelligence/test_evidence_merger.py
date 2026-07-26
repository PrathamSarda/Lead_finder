from automation.intelligence.evidence_merger import EvidenceMerger
from automation.intelligence.models import CompanyEvidence


def make_evidence(
    *,
    source="generic",
    company_name="BROCKMAN TRUCKING INC",
    website=None,
    email=None,
    phone=None,
    location=None,
    confidence=0.5,
):
    return CompanyEvidence(
        source=source,
        title="",
        url="",
        snippet="",
        company_name=company_name,
        website=website,
        email=email,
        phone=phone,
        location=location,
        confidence=confidence,
    )


def test_empty_input_returns_none():
    merger = EvidenceMerger()

    assert merger.merge([]) is None


def test_single_evidence_is_returned():
    merger = EvidenceMerger()

    evidence = make_evidence(
        website="https://abc.com",
        confidence=0.9,
    )

    merged = merger.merge([evidence])

    assert merged.website == "https://abc.com"
    assert merged.company_name == "BROCKMAN TRUCKING INC"


def test_highest_confidence_website_is_selected():
    merger = EvidenceMerger()

    linkedin = make_evidence(
        source="linkedin",
        website="https://linkedin-site.com",
        confidence=0.95,
    )

    generic = make_evidence(
        source="generic",
        website="https://generic-site.com",
        confidence=0.70,
    )

    merged = merger.merge(
        [
            generic,
            linkedin,
        ]
    )

    assert merged.website == "https://linkedin-site.com"


def test_email_is_merged():
    merger = EvidenceMerger()

    generic = make_evidence(
        email="info@test.com",
        confidence=0.60,
    )

    linkedin = make_evidence(
        website="https://abc.com",
        confidence=0.95,
    )

    merged = merger.merge(
        [
            generic,
            linkedin,
        ]
    )

    assert merged.email == "info@test.com"


def test_phone_is_merged():
    merger = EvidenceMerger()

    generic = make_evidence(
        phone="123456",
        confidence=0.60,
    )

    linkedin = make_evidence(
        website="https://abc.com",
        confidence=0.95,
    )

    merged = merger.merge(
        [
            generic,
            linkedin,
        ]
    )

    assert merged.phone == "123456"


def test_location_is_merged():
    merger = EvidenceMerger()

    indeed = make_evidence(
        location="Afton, MN",
        confidence=0.85,
    )

    linkedin = make_evidence(
        website="https://abc.com",
        confidence=0.95,
    )

    merged = merger.merge(
        [
            linkedin,
            indeed,
        ]
    )

    assert merged.location == "Afton, MN"


def test_company_name_from_highest_confidence():
    merger = EvidenceMerger()

    first = make_evidence(
        company_name="ABC INC",
        confidence=0.5,
    )

    second = make_evidence(
        company_name="ABC Incorporated",
        confidence=0.9,
    )

    merged = merger.merge(
        [
            first,
            second,
        ]
    )

    assert merged.company_name == "ABC Incorporated"


def test_confidence_is_highest_value():
    merger = EvidenceMerger()

    first = make_evidence(
        confidence=0.65,
    )

    second = make_evidence(
        confidence=0.92,
    )

    merged = merger.merge(
        [
            first,
            second,
        ]
    )

    assert merged.confidence == 0.92


def test_sources_are_deduplicated():
    merger = EvidenceMerger()

    merged = merger.merge(
        [
            make_evidence(source="linkedin"),
            make_evidence(source="linkedin"),
            make_evidence(source="generic"),
        ]
    )

    assert sorted(merged.sources) == [
        "generic",
        "linkedin",
    ]