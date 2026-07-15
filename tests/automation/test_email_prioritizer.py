from automation.enrichment.email_prioritizer import (
    prioritize_emails,
)


def test_company_domain_email_is_prioritized():
    result = prioritize_emails(
        emails=[
            "owner@gmail.com",
            "info@examplecompany.com",
        ],
        website="https://www.examplecompany.com",
    )

    assert result.primary_email == (
        "info@examplecompany.com"
    )

    assert result.business_emails == [
        "info@examplecompany.com",
    ]

    assert result.personal_emails == [
        "owner@gmail.com",
    ]


def test_generic_business_email_beats_named_email():
    result = prioritize_emails(
        emails=[
            "john.smith@example.com",
            "contact@example.com",
            "sales@example.com",
        ],
        website="https://example.com",
    )

    assert result.primary_email == (
        "contact@example.com"
    )

    assert result.business_emails == [
        "contact@example.com",
        "sales@example.com",
        "john.smith@example.com",
    ]


def test_free_email_is_used_when_no_business_email_exists():
    result = prioritize_emails(
        emails=[
            "Owner@Gmail.com",
            "owner@gmail.com",
        ],
    )

    assert result.primary_email == (
        "owner@gmail.com"
    )

    assert result.business_emails == []

    assert result.personal_emails == [
        "owner@gmail.com",
    ]


def test_invalid_and_placeholder_emails_are_rejected():
    result = prioritize_emails(
        emails=[
            "not-an-email",
            "test@example.com",
            "info@example.com",
        ],
        website="https://example.com",
    )

    assert result.primary_email == (
        "info@example.com"
    )

    assert "not-an-email" in (
        result.rejected_emails
    )

    assert "test@example.com" in (
        result.rejected_emails
    )


def test_no_reply_email_is_ranked_below_contact_email():
    result = prioritize_emails(
        emails=[
            "no-reply@example.com",
            "contact@example.com",
        ],
        website="https://example.com",
    )

    assert result.primary_email == (
        "contact@example.com"
    )


def test_empty_email_list_returns_empty_result():
    result = prioritize_emails(
        emails=[],
        website="https://example.com",
    )

    assert result.primary_email is None
    assert result.business_emails == []
    assert result.personal_emails == []
    assert result.rejected_emails == []