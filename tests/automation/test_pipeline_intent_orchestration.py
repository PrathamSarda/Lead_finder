"""
Test MultiToolLeadPipeline intent orchestration and size gate.
"""
from unittest.mock import MagicMock, patch

from automation.pipeline_v2.pipeline_orchestrator import MultiToolLeadPipeline, QualifiedB2BLead
from automation.pipeline_v2.apify_enricher import LinkedInCompanyProfile
from automation.pipeline_v2.indeed_checker import IndeedIntentResult
from automation.pipeline_v2.intent_analyzer import IntentAnalysisResult
from automation.pipeline_v2.linkedin_retriever import DecisionMakerLinkedIn
from automation.pipeline_v2.email_enricher import HunterEmailResult


@patch("automation.pipeline_v2.pipeline_orchestrator.FMCSAConnector")
@patch("automation.pipeline_v2.pipeline_orchestrator.SerperMapsDiscovery")
@patch("automation.pipeline_v2.pipeline_orchestrator.ApifyLinkedInEnricher")
@patch("automation.pipeline_v2.pipeline_orchestrator.IntentAnalyzer")
@patch("automation.pipeline_v2.pipeline_orchestrator.IndeedBookkeepingChecker")
@patch("automation.pipeline_v2.pipeline_orchestrator.LinkedInProfileRetriever")
@patch("automation.pipeline_v2.pipeline_orchestrator.HunterDecisionMakerEmailFinder")
def test_pipeline_confirms_via_indeed_when_linkedin_empty(
    mock_email_cls,
    mock_li_retriever_cls,
    mock_indeed_cls,
    mock_intent_cls,
    mock_apify_cls,
    mock_maps_cls,
    mock_fmcsa_cls,
    tmp_path,
):
    # Setup candidate
    lead_mock = MagicMock()
    lead_mock.company_name = "Blue Sky Transport LLC"
    lead_mock.contact_phone = "555-0100"
    lead_mock.location = "Dallas, TX"
    lead_mock.industry = "Motor Carrier"
    mock_fmcsa_cls.return_value.search_candidates.return_value = [lead_mock]

    # Maps mock
    mock_maps_cls.return_value.lookup_company.return_value = MagicMock(
        domain="blueskytransport.com",
        website="https://blueskytransport.com",
        phone="555-0100",
        address="Dallas, TX",
        category="Transportation",
    )

    # LinkedIn profile returns 12 employees (passes size gate 10-15), but NO recent posts
    mock_apify_cls.return_value.qualify_and_extract_posts.return_value = LinkedInCompanyProfile(
        company_name="Blue Sky Transport LLC",
        linkedin_url="https://linkedin.com/company/blue-sky-transport",
        employee_count=12,
        employee_range="10-15",
        passed_size_gate=True,
        recent_posts=[],
    )

    # LinkedIn intent is not found because no posts
    mock_intent_cls.return_value.analyze.return_value = IntentAnalysisResult(
        intent_found=False,
        reason="No posts",
        model_used="none",
    )

    # Indeed DOES find a job posting for Bookkeeper!
    mock_indeed_cls.return_value.check_company.return_value = IndeedIntentResult(
        intent_found=True,
        job_title="Bookkeeper / Staff Accountant",
        job_url="https://www.indeed.com/viewjob?jk=blue123",
        reason="Confirmed bookkeeping requirement via Indeed job posting: 'Bookkeeper / Staff Accountant'",
        source="Indeed Job Postings",
    )

    # Decision maker retriever
    mock_li_retriever_cls.return_value._find_company_linkedin.return_value = "https://linkedin.com/company/blue-sky-transport"
    mock_li_retriever_cls.return_value.retrieve.return_value = DecisionMakerLinkedIn(
        company_linkedin_url="https://linkedin.com/company/blue-sky-transport",
        decision_maker_name="John Doe",
        decision_maker_title="Owner & CEO",
        decision_maker_linkedin_url="https://linkedin.com/in/johndoe",
        retrieval_status="FOUND",
        confidence_score=90,
        source="Serper",
    )

    # Company email
    mock_email_cls.return_value.find_company_email.return_value = HunterEmailResult(
        email="contact@blueskytransport.com",
        status="VALID",
        confidence=85,
        source="Company Website",
    )

    # Hunter verifies decision-maker email
    mock_email_cls.return_value.find_and_verify.return_value = HunterEmailResult(
        email="johndoe@blueskytransport.com",
        status="VALID",
        confidence=95,
        source="Hunter",
    )

    db_path = tmp_path / "test_leads.db"
    out_dir = tmp_path / "outputs"

    pipeline = MultiToolLeadPipeline(
        serper_key="test",
        apify_token="test",
        hunter_key="test",
        db_path=db_path,
        min_employees=10,
        max_employees=15,
    )

    ready = pipeline.run(query="bookkeeping", target_count=1, output_dir=str(out_dir))

    assert len(ready) == 1
    lead = ready[0]
    assert lead.company_name == "Blue Sky Transport LLC"
    assert lead.intent_found is True
    assert lead.intent_source == "Indeed"
    assert "Bookkeeper" in lead.ai_intent_reason
    assert lead.indeed_job_url == "https://www.indeed.com/viewjob?jk=blue123"
    assert lead.employee_count == 12
    assert lead.company_email == "contact@blueskytransport.com"
    assert lead.decision_maker_email == "johndoe@blueskytransport.com"
    assert lead.pipeline_status == "QUALIFIED_CONVERTIBLE"


@patch("automation.pipeline_v2.pipeline_orchestrator.FMCSAConnector")
@patch("automation.pipeline_v2.pipeline_orchestrator.SerperMapsDiscovery")
@patch("automation.pipeline_v2.pipeline_orchestrator.ApifyLinkedInEnricher")
@patch("automation.pipeline_v2.pipeline_orchestrator.IntentAnalyzer")
@patch("automation.pipeline_v2.pipeline_orchestrator.IndeedBookkeepingChecker")
@patch("automation.pipeline_v2.pipeline_orchestrator.LinkedInProfileRetriever")
def test_pipeline_rejects_when_neither_linkedin_nor_indeed_has_intent(
    mock_li_retriever_cls,
    mock_indeed_cls,
    mock_intent_cls,
    mock_apify_cls,
    mock_maps_cls,
    mock_fmcsa_cls,
    tmp_path,
):
    lead_mock = MagicMock()
    lead_mock.company_name = "Silver Star Logistics LLC"
    lead_mock.contact_phone = "555-0200"
    lead_mock.location = "Houston, TX"
    lead_mock.industry = "Motor Carrier"
    mock_fmcsa_cls.return_value.search_candidates.return_value = [lead_mock]

    mock_maps_cls.return_value.lookup_company.return_value = MagicMock(
        domain="silverstar.com",
        website="https://silverstar.com",
        phone="555-0200",
        address="Houston, TX",
        category="Transportation",
    )

    mock_apify_cls.return_value.qualify_and_extract_posts.return_value = LinkedInCompanyProfile(
        company_name="Silver Star Logistics LLC",
        linkedin_url="https://linkedin.com/company/silver-star",
        employee_count=14,
        employee_range="10-15",
        passed_size_gate=True,
        recent_posts=[],
    )

    mock_li_retriever_cls.return_value._find_company_linkedin.return_value = "https://linkedin.com/company/silver-star"

    # Both return NO intent
    mock_intent_cls.return_value.analyze.return_value = IntentAnalysisResult(
        intent_found=False, reason="No intent in posts", model_used="none"
    )
    mock_indeed_cls.return_value.check_company.return_value = IndeedIntentResult(
        intent_found=False,
        job_title=None,
        job_url=None,
        reason="No bookkeeping jobs found on Indeed",
        source="Indeed Job Postings",
    )

    db_path = tmp_path / "test_leads.db"
    out_dir = tmp_path / "outputs"

    pipeline = MultiToolLeadPipeline(
        serper_key="test",
        apify_token="test",
        db_path=db_path,
        min_employees=10,
        max_employees=15,
    )

    ready = pipeline.run(query="bookkeeping", target_count=1, output_dir=str(out_dir))

    # Must be 0 because neither LinkedIn nor Indeed confirmed bookkeeping requirement!
    assert len(ready) == 0


@patch("automation.pipeline_v2.pipeline_orchestrator.FMCSAConnector")
@patch("automation.pipeline_v2.pipeline_orchestrator.SerperMapsDiscovery")
@patch("automation.pipeline_v2.pipeline_orchestrator.ApifyLinkedInEnricher")
@patch("automation.pipeline_v2.pipeline_orchestrator.LinkedInProfileRetriever")
def test_pipeline_drops_outside_10_15_employees(
    mock_li_retriever_cls,
    mock_apify_cls,
    mock_maps_cls,
    mock_fmcsa_cls,
    tmp_path,
):
    lead_mock = MagicMock()
    lead_mock.company_name = "Big Fleet Freight LLC"
    lead_mock.contact_phone = "555-0300"
    lead_mock.location = "Atlanta, GA"
    lead_mock.industry = "Motor Carrier"
    mock_fmcsa_cls.return_value.search_candidates.return_value = [lead_mock]

    mock_maps_cls.return_value.lookup_company.return_value = MagicMock(
        domain="bigfleet.com",
        website="https://bigfleet.com",
        phone="555-0300",
        address="Atlanta, GA",
        category="Transportation",
    )

    # 35 employees - outside target 10-15
    mock_apify_cls.return_value.qualify_and_extract_posts.return_value = LinkedInCompanyProfile(
        company_name="Big Fleet Freight LLC",
        linkedin_url="https://linkedin.com/company/big-fleet",
        employee_count=35,
        employee_range="11-50",
        passed_size_gate=False,
        recent_posts=[],
    )

    mock_li_retriever_cls.return_value._find_company_linkedin.return_value = "https://linkedin.com/company/big-fleet"

    db_path = tmp_path / "test_leads.db"
    out_dir = tmp_path / "outputs"

    pipeline = MultiToolLeadPipeline(
        serper_key="test",
        apify_token="test",
        db_path=db_path,
        min_employees=10,
        max_employees=15,
    )

    ready = pipeline.run(query="bookkeeping", target_count=1, output_dir=str(out_dir))
    assert len(ready) == 0


@patch("automation.pipeline_v2.pipeline_orchestrator.FMCSAConnector")
@patch("automation.pipeline_v2.pipeline_orchestrator.SerperMapsDiscovery")
@patch("automation.pipeline_v2.pipeline_orchestrator.ApifyLinkedInEnricher")
@patch("automation.pipeline_v2.pipeline_orchestrator.IntentAnalyzer")
@patch("automation.pipeline_v2.pipeline_orchestrator.IndeedBookkeepingChecker")
@patch("automation.pipeline_v2.pipeline_orchestrator.LinkedInProfileRetriever")
@patch("automation.pipeline_v2.pipeline_orchestrator.HunterDecisionMakerEmailFinder")
def test_pipeline_minimum_company_email_qualifies(
    mock_email_cls,
    mock_li_retriever_cls,
    mock_indeed_cls,
    mock_intent_cls,
    mock_apify_cls,
    mock_maps_cls,
    mock_fmcsa_cls,
    tmp_path,
):
    """If decision maker email is missing, but company email is found, lead qualifies (minimum requirement met)."""
    lead_mock = MagicMock()
    lead_mock.company_name = "Lone Star Dispatch LLC"
    lead_mock.contact_phone = "555-0400"
    lead_mock.location = "Austin, TX"
    lead_mock.industry = "Motor Carrier"
    mock_fmcsa_cls.return_value.search_candidates.return_value = [lead_mock]

    mock_maps_cls.return_value.lookup_company.return_value = MagicMock(
        domain="lonestardispatch.com",
        website="https://lonestardispatch.com",
        phone="555-0400",
        address="Austin, TX",
        category="Logistics",
    )

    mock_apify_cls.return_value.qualify_and_extract_posts.return_value = LinkedInCompanyProfile(
        company_name="Lone Star Dispatch LLC",
        linkedin_url="https://linkedin.com/company/lone-star-dispatch",
        employee_count=14,
        employee_range="10-15",
        passed_size_gate=True,
        recent_posts=[],
    )

    mock_intent_cls.return_value.analyze.return_value = IntentAnalysisResult(
        intent_found=False,
        reason="No posts",
        model_used="none",
    )

    mock_indeed_cls.return_value.check_company.return_value = IndeedIntentResult(
        intent_found=True,
        job_title="Bookkeeper",
        job_url="https://www.indeed.com/viewjob?jk=lsd1",
        reason="Confirmed bookkeeping requirement via Indeed job posting",
        source="Indeed Job Postings",
    )

    mock_li_retriever_cls.return_value._find_company_linkedin.return_value = "https://linkedin.com/company/lone-star-dispatch"
    mock_li_retriever_cls.return_value.retrieve.return_value = DecisionMakerLinkedIn(
        company_linkedin_url="https://linkedin.com/company/lone-star-dispatch",
        decision_maker_name="Jane Smith",
        decision_maker_title="Managing Director",
        decision_maker_linkedin_url=None,
        retrieval_status="FOUND",
        confidence_score=85,
        source="Serper",
    )

    # Company email found from website
    mock_email_cls.return_value.find_company_email.return_value = HunterEmailResult(
        email="info@lonestardispatch.com",
        status="VALID",
        confidence=85,
        source="Company Website",
    )
    # Decision maker email NOT found
    mock_email_cls.return_value.find_and_verify.return_value = HunterEmailResult(
        email=None,
        status="NOT_FOUND",
        confidence=0,
    )

    db_path = tmp_path / "test_leads.db"
    out_dir = tmp_path / "outputs"

    pipeline = MultiToolLeadPipeline(
        serper_key="test",
        apify_token="test",
        hunter_key="test",
        db_path=db_path,
        min_employees=10,
        max_employees=15,
    )

    ready = pipeline.run(query="bookkeeping", target_count=1, output_dir=str(out_dir))

    assert len(ready) == 1
    lead = ready[0]
    assert lead.company_name == "Lone Star Dispatch LLC"
    assert lead.company_email == "info@lonestardispatch.com"
    assert lead.decision_maker_email is None
    assert lead.pipeline_status == "QUALIFIED_CONVERTIBLE"
    assert lead.email_status == "COMPANY_EMAIL_ONLY"


def test_detect_candidate_region_multi():
    active_regions = ["US", "UK", "AU", "CA"]
    detect = MultiToolLeadPipeline._detect_candidate_region

    assert detect("124 Oxford St, London, UK", active_regions) == "UK"
    assert detect("50 George St, Sydney NSW, Australia", active_regions) == "AU"
    assert detect("100 King St W, Toronto, ON, Canada", active_regions) == "CA"
    assert detect("100 Main St, Austin, TX, USA", active_regions) == "US"
    # Fallback to first region if unrecognized
    assert detect("Unknown Place", ["UK", "AU"]) == "UK"
    assert detect(None, ["US", "UK"]) == "US"

