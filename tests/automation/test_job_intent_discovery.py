"""
Tests for JobIntentDiscovery service.
"""
from unittest.mock import MagicMock, patch

from automation.pipeline_v2.job_intent_discovery import JobIntentDiscovery, HiringIntentLeadCandidate


def test_extract_company_from_job_linkedin_title():
    title = "Full Charge Bookkeeper at Cubepros — United States"
    snippet = "Apply for Full Charge Bookkeeper at Cubepros in United States. Full-cycle bookkeeping..."
    link = "https://www.linkedin.com/jobs/view/full-charge-bookkeeper-at-cubepros-4412558907"

    extracted = JobIntentDiscovery._extract_company_from_job(title, snippet, link)
    assert extracted is not None
    assert extracted["company"] == "Cubepros"
    assert "Bookkeeper" in extracted["role"]
    assert extracted["source"] == "LinkedIn"


def test_extract_company_from_job_indeed_snippet():
    title = "Remote Bookkeeper (QuickBooks Expert) - Denver, CO"
    snippet = "Remote Bookkeeper (QuickBooks Expert). Sound Advice. ·. 4.1. Job details. $32 an hour."
    link = "https://www.indeed.com/viewjob?jk=8e2345dec0ddc11e"

    extracted = JobIntentDiscovery._extract_company_from_job(title, snippet, link)
    assert extracted is not None
    assert extracted["company"] == "Sound Advice"
    assert extracted["source"] == "Indeed"


@patch("automation.pipeline_v2.job_intent_discovery.requests.post")
def test_discover_hiring_companies_returns_leads(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organic": [
            {
                "title": "Remote Bookkeeper at Law Firm Velocity — USA",
                "snippet": "Apply for Remote Bookkeeper at Law Firm Velocity in USA. Manage QuickBooks accounts.",
                "link": "https://www.linkedin.com/jobs/view/remote-bookkeeper-law-firm-velocity-12345",
                "date": "3 days ago",
            },
            {
                "title": "Staff Bookkeeper. Apex Commercial Group. Job details.",
                "snippet": "Staff Bookkeeper. Apex Commercial Group. Job details. Full charge bookkeeping...",
                "link": "https://www.indeed.com/viewjob?jk=apex999",
                "date": "5 days ago",
            },
        ]
    }
    mock_post.return_value = mock_resp

    discovery = JobIntentDiscovery(serper_api_key="test_key")
    results = discovery.discover_hiring_companies(query="bookkeeping", limit=5)

    assert len(results) == 2
    assert results[0].company_name == "Law Firm Velocity"
    assert results[0].source == "LinkedIn"
    assert results[1].company_name == "Apex Commercial Group"
    assert results[1].source == "Indeed"

