"""
Unit tests for IndeedBookkeepingChecker.
"""
from unittest.mock import patch, MagicMock

from automation.pipeline_v2.indeed_checker import IndeedBookkeepingChecker, IndeedIntentResult


def test_clean_job_title():
    checker = IndeedBookkeepingChecker()
    raw = "Full Charge Bookkeeper - Austin, TX 78701 - Indeed.com"
    clean = checker._clean_job_title(raw, "Austin Logistics")
    assert clean == "Full Charge Bookkeeper"


def test_relevance_matching():
    checker = IndeedBookkeepingChecker()
    # Relevant
    is_rel = checker._is_relevant_to_company(
        company_name="Apex Logistics LLC",
        domain="apexlogistics.com",
        title="Staff Accountant - Apex Logistics - Indeed",
        snippet="Apex Logistics is hiring a Staff Accountant to handle QuickBooks and bookkeeping.",
        link="https://www.indeed.com/cmp/apex-logistics/jobs",
    )
    assert is_rel is True

    # Irrelevant company
    is_not_rel = checker._is_relevant_to_company(
        company_name="Apex Logistics LLC",
        domain="apexlogistics.com",
        title="Bookkeeper - Walmart Inc - Indeed",
        snippet="Walmart is seeking a store bookkeeper in Dallas.",
        link="https://www.indeed.com/viewjob?jk=123",
    )
    assert is_not_rel is False


@patch("automation.pipeline_v2.indeed_checker.requests.post")
def test_indeed_intent_confirmed(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "Full Charge Bookkeeper - Summit Transport LLC - Indeed",
                "link": "https://www.indeed.com/viewjob?jk=abc123",
                "snippet": "Summit Transport LLC is seeking a Full Charge Bookkeeper with QuickBooks experience for accounts payable and payroll.",
            }
        ]
    }
    mock_post.return_value = mock_response

    checker = IndeedBookkeepingChecker(serper_api_key="test-key")
    result = checker.check_company("Summit Transport LLC", domain="summittransport.com")

    assert result.intent_found is True
    assert "Bookkeeper" in (result.job_title or "")
    assert "Confirmed bookkeeping requirement via Indeed" in result.reason
    assert "Indeed" in result.source


@patch("automation.pipeline_v2.indeed_checker.requests.post")
def test_indeed_date_filtering(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "Bookkeeper - Summit Transport LLC - Indeed",
                "link": "https://www.indeed.com/viewjob?jk=old123",
                "snippet": "Summit Transport is hiring. Posted 60 days ago.",
                "date": "2024-01-01",
            }
        ]
    }
    mock_post.return_value = mock_response

    checker = IndeedBookkeepingChecker(serper_api_key="test-key")
    # Require post on or after 2024-06-01: listing from 2024-01-01 should be skipped
    result = checker.check_company(
        "Summit Transport LLC",
        domain="summittransport.com",
        after_date="2024-06-01",
    )
    assert result.intent_found is False


@patch("automation.pipeline_v2.indeed_checker.requests.post")
def test_indeed_region_support(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "Accountant - London Express Ltd - Indeed",
                "link": "https://www.indeed.co.uk/viewjob?jk=uk123",
                "snippet": "London Express Ltd seeks a Full Charge Bookkeeper in London.",
                "date": "3 days ago",
            }
        ]
    }
    mock_post.return_value = mock_response

    checker = IndeedBookkeepingChecker(serper_api_key="test-key")
    result = checker.check_company(
        "London Express Ltd",
        domain="londonexpress.co.uk",
        region="UK",
    )
    assert result.intent_found is True
    assert "UK" in result.source


@patch("automation.pipeline_v2.indeed_checker.requests.post")
def test_indeed_no_intent(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "organic": [
            {
                "title": "CDL Truck Driver - Summit Transport LLC - Indeed",
                "link": "https://www.indeed.com/viewjob?jk=driver123",
                "snippet": "Summit Transport LLC is looking for Class A CDL Drivers for regional routes.",
            }
        ]
    }
    mock_post.return_value = mock_response

    checker = IndeedBookkeepingChecker(serper_api_key="test-key")
    result = checker.check_company("Summit Transport LLC", domain="summittransport.com")

    assert result.intent_found is False
    assert result.job_title is None

