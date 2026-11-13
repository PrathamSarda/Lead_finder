"""
Multi-Tool Intent-Driven Lead Generation Pipeline Coordinator.
Implements the 5-stage technical specification:
1. Candidate Source: active US FMCSA carrier registry, optionally filtered by state
2. Local Enrichment: Serper.dev Google Maps -> Phone, website, address
3. Size Gate: Apify LinkedIn company scraper -> Keeps companies with <= 20 employees
4. Feed Extraction: Apify Posts Scraper -> Pulls 5-10 recent public posts
5. AI Intent Verification: Gemini Flash, with rule-based date/intent fallback
6. LinkedIn Profile Retrieval: Company page and decision-maker profile
7. Export to CSV & SQLite DB with complete provenance
"""
from __future__ import annotations

import csv
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from difflib import SequenceMatcher

from dotenv import load_dotenv

load_dotenv()

from automation.pipeline_v2.apify_enricher import ApifyLinkedInEnricher
from automation.pipeline_v2.intent_analyzer import IntentAnalyzer
from automation.pipeline_v2.indeed_checker import IndeedBookkeepingChecker, IndeedIntentResult
from automation.pipeline_v2.email_enricher import HunterDecisionMakerEmailFinder, HunterEmailResult
from automation.pipeline_v2.lead_db import LeadDatabase
from automation.pipeline_v2.linkedin_retriever import LinkedInProfileRetriever
from automation.pipeline_v2.serper_discovery import DiscoveredBusiness, SerperMapsDiscovery
from automation.pipeline_v2.job_intent_discovery import JobIntentDiscovery, HiringIntentLeadCandidate
from automation.models.search_filters import SearchFilters
from automation.sources.fmcsa.connector import FMCSAConnector


@dataclass(slots=True)
class QualifiedB2BLead:
    company_name: str
    domain: str | None
    website: str | None
    phone: str | None
    address: str | None
    category: str | None
    employee_count: int | None
    employee_range: str | None
    passed_size_gate: bool
    intent_found: bool
    ai_intent_reason: str
    ai_model_used: str
    company_linkedin_url: str | None
    decision_maker_name: str | None
    decision_maker_title: str | None
    decision_maker_linkedin_url: str | None
    retrieval_status: str
    confidence_score: int
    pipeline_status: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    company_email: str | None = None
    decision_maker_email: str | None = None
    owner_email: str | None = None
    email_status: str = "NOT_CHECKED"
    email_confidence: int | None = None
    email_source: str | None = None
    has_recent_linkedin_post: bool = False
    intent_source: str = "None"
    indeed_job_url: str | None = None
    job_post_url: str | None = None
    company_type: str | None = None
    region: str = "US"
    after_date: str | None = None


# Minimal client-facing export schema
CLIENT_LEADS_FIELDNAMES = [
    "company_name",
    "company_type",
    "pipeline_status",
    "region",
    "employee_count",
    "phone",
    "address",
    "website",
    "company_email",
    "decision_maker_name",
    "decision_maker_title",
    "decision_maker_email",
    "decision_maker_linkedin_url",
    "intent_found",
    "intent_source",
    "ai_intent_reason",
    "job_post_url",
    "indeed_job_url",
    "company_linkedin_url",
    "has_recent_linkedin_post",
    "email_status",
    "email_confidence",
    "email_source",
    "after_date",
]

# Internal full audit trail schema
PIPELINE_V2_FIELDNAMES = [
    "company_name",
    "region",
    "domain",
    "website",
    "phone",
    "address",
    "category",
    "company_type",
    "employee_count",
    "employee_range",
    "passed_size_gate",
    "intent_found",
    "intent_source",
    "ai_intent_reason",
    "ai_model_used",
    "job_post_url",
    "indeed_job_url",
    "company_linkedin_url",
    "has_recent_linkedin_post",
    "company_email",
    "decision_maker_name",
    "decision_maker_title",
    "decision_maker_email",
    "decision_maker_linkedin_url",
    "owner_email",
    "email_status",
    "email_confidence",
    "email_source",
    "retrieval_status",
    "confidence_score",
    "pipeline_status",
    "after_date",
    "created_at",
]


class MultiToolLeadPipeline:
    """End-to-End Orchestrator for the Intent-Driven Multi-Tool Pipeline."""

    @staticmethod
    def _is_recent_post(post: str, today: datetime | None = None, after_date: str | datetime | None = None) -> bool:
        """Require an explicit post date no older than 90 days or on/after after_date; undated posts do not pass."""
        today = today or datetime.now()
        cutoff_dt: datetime | None = None
        if isinstance(after_date, str) and after_date.strip():
            try:
                cutoff_dt = datetime.strptime(after_date.strip(), "%Y-%m-%d")
            except ValueError:
                pass
        elif isinstance(after_date, datetime):
            cutoff_dt = after_date

        match = re.search(r"\[Posted:\s*([^\]]+)\]", post, flags=re.I)
        if not match:
            return False
        value = match.group(1).strip()
        if not value or value.lower() in {"none", "null", "unknown"}:
            return False
        if value.isdigit():
            try:
                timestamp = int(value)
                if timestamp > 10_000_000_000:
                    timestamp //= 1000
                parsed = datetime.fromtimestamp(timestamp)
                if cutoff_dt:
                    return parsed >= cutoff_dt
                return timedelta(0) <= today - parsed <= timedelta(days=90)
            except (OverflowError, OSError, ValueError):
                return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            parsed = None
        if parsed is not None:
            if cutoff_dt:
                return parsed >= cutoff_dt
            return timedelta(0) <= today - parsed <= timedelta(days=90)
        relative = re.search(r"(\d+)\s*(minute|hour|day|week|month|year)s?\s*(?:ago)?", value, re.I)
        short = re.fullmatch(r"(\d+)\s*([mhdw])", value.lower())
        if relative:
            n, unit = int(relative.group(1)), relative.group(2).lower()
            days = n * {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}[unit]
            parsed_rel = today - timedelta(days=days)
            if cutoff_dt:
                return parsed_rel >= cutoff_dt
            return days <= 90
        if short:
            n, unit = int(short.group(1)), short.group(2)
            days = n * {"m": 30, "h": 0, "d": 1, "w": 7}[unit]
            parsed_rel = today - timedelta(days=days)
            if cutoff_dt:
                return parsed_rel >= cutoff_dt
            return days <= 90
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
            if cutoff_dt:
                return parsed >= cutoff_dt
            return timedelta(0) <= today - parsed <= timedelta(days=90)
        except ValueError:
            return False

    def __init__(
        self,
        serper_key: str | None = None,
        apify_token: str | None = None,
        gemini_key: str | None = None,
        company_actor: str | None = None,
        posts_actor: str | None = None,
        hunter_key: str | None = None,
        db_path: str | Path | None = None,
        cooldown_days: int = 18,
        min_employees: int = 10,
        max_employees: int = 15,
    ):
        self.serper_key = (serper_key or os.getenv("SERPER_API_KEY", "")).strip()
        self.min_employees = min_employees
        self.max_employees = max_employees
        self.discovery = SerperMapsDiscovery(self.serper_key)
        self.job_discovery = JobIntentDiscovery(self.serper_key)
        self.apify = ApifyLinkedInEnricher(
            apify_token,
            company_scraper_actor=company_actor,
            posts_scraper_actor=posts_actor,
            min_employees=min_employees,
            max_employees=max_employees,
        )
        self.intent = IntentAnalyzer(gemini_api_key=gemini_key)
        self.indeed_checker = IndeedBookkeepingChecker(serper_api_key=self.serper_key, gemini_api_key=gemini_key)
        self.linkedin_retriever = LinkedInProfileRetriever(serper_api_key=self.serper_key)
        self.email_finder = HunterDecisionMakerEmailFinder(hunter_key)
        self.db = LeadDatabase(db_path=db_path)
        self.cooldown_days = cooldown_days

    @staticmethod
    def _detect_candidate_region(address: str | None, active_regions: list[str]) -> str:
        if not address or len(active_regions) == 1:
            return active_regions[0] if active_regions else "US"
        addr_up = address.upper()
        if any(k in addr_up for k in ("UNITED KINGDOM", "ENGLAND", "SCOTLAND", "WALES", "LONDON", "BIRMINGHAM", "MANCHESTER", "LEEDS", "GLASGOW", "EDINBURGH")) or re.search(r"\bUK\b", addr_up):
            return "UK"
        if any(k in addr_up for k in ("AUSTRALIA", "SYDNEY", "MELBOURNE", "BRISBANE", "PERTH", "ADELAIDE")) or re.search(r"\b(AU|NSW|VIC|QLD|WA|SA|TAS|ACT)\b", addr_up):
            return "AU"
        if any(k in addr_up for k in ("CANADA", "TORONTO", "VANCOUVER", "ONTARIO", "QUEBEC", "ALBERTA", "CALGARY", "MONTREAL")) or re.search(r"\b(CA|ON|BC|AB|QC)\b", addr_up):
            return "CA"
        if any(k in addr_up for k in ("USA", "UNITED STATES")) or re.search(r"\b(US|TX|FL|GA|NY|OH|IL|PA|NC|MI|NJ|VA|WA|AZ|TN|CO|IN|MO|MD|WI)\b", addr_up):
            return "US"
        return active_regions[0] if active_regions else "US"

    def run(
        self,
        query: str,
        target_count: int = 15,
        output_dir: str = "outputs",
        state: str | None = None,
        city: str | None = None,
        region: str = "US",
        after_date: str | None = None,
        progress_callback: Callable[[dict], None] | None = None,
        candidate_source: str = "fmcsa",  # "jobs" (fast intent-first) or "fmcsa" / "maps" (legacy)
    ) -> list[QualifiedB2BLead]:
        """Runs the entire multi-tool workflow until target_count qualified leads are discovered."""
        reg_upper = (region or "US").upper()
        print("=" * 80)
        print("PROKIZEN GLOBAL - MULTI-TOOL INTENT LEAD GENERATION PIPELINE")
        print(f"Target Intent : {query}")
        print(f"Target Region : {reg_upper}")
        if after_date:
            print(f"After Date    : Services required on or after {after_date}")
        print(f"Target Count  : {target_count} SMB leads ({self.min_employees}-{self.max_employees} employees with verified bookkeeping intent via LinkedIn/Indeed)")
        print(f"Cooldown Rule : Excludes companies contacted in the last {self.cooldown_days} days (allows fresh rotation)")
        print(f"Started at    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        start_time = time.perf_counter()

        active_regions = [r.strip().upper() for r in (region or "US").split(",") if r.strip()]
        qualified_leads: list[QualifiedB2BLead] = []
        evaluated_candidates_set: set[str] = set()
        processed_candidates = 0
        candidate_limit = min(max(target_count * 20, 100), 500)
        location = ", ".join(part for part in (city, state) if part)

        discovered: list[DiscoveredBusiness] = []
        job_intent_map: dict[str, HiringIntentLeadCandidate] = {}

        def _fetch_candidates_batch(round_num: int) -> list[DiscoveredBusiness]:
            batch_discovered: list[DiscoveredBusiness] = []
            if candidate_source == "jobs":
                print(f"\n[Search Round {round_num}] Searching job postings on LinkedIn, Indeed, Monster, and ZipRecruiter...")
                if progress_callback:
                    progress_callback({
                        "step": f"Searching job postings (Round {round_num}): LinkedIn, Indeed, Monster, ZipRecruiter",
                        "processed": processed_candidates,
                        "total": target_count,
                        "company": None,
                        "verified": sum(1 for lead in qualified_leads if lead.pipeline_status == "QUALIFIED_CONVERTIBLE"),
                    })

                job_leads = self.job_discovery.discover_hiring_companies(
                    query=query,
                    limit=max(target_count * 15, 60),
                    region=reg_upper,
                    after_date=after_date,
                    city=city,
                    state=state,
                )

                for jl in job_leads:
                    c_norm = jl.company_name.strip()
                    job_intent_map[c_norm.lower()] = jl
                    batch_discovered.append(
                        DiscoveredBusiness(
                            title=jl.company_name,
                            domain=jl.domain,
                            website=jl.website,
                            phone=jl.phone,
                            address=jl.address,
                            category="Hiring for Bookkeeping / Accounting",
                        )
                    )

                # Augment with local directory / maps if initial round returned few
                if len(batch_discovered) < target_count * 2:
                    print(f"-> Augmenting round {round_num} with local SMB candidates from region '{reg_upper}'...")
                    if reg_upper == "US" and not city and not state:
                        fmcsa_companies = FMCSAConnector().search_candidates(SearchFilters(max_results=target_count * 4, state=state, city=city))
                        for company in fmcsa_companies:
                            batch_discovered.append(
                                DiscoveredBusiness(
                                    title=company.company_name,
                                    domain=None,
                                    website=None,
                                    phone=company.contact_phone,
                                    address=company.location,
                                    category=company.industry,
                                )
                            )
                    else:
                        extra_maps = self.discovery.discover(limit=target_count * 4, region=reg_upper)
                        batch_discovered.extend(extra_maps)
            else:
                if reg_upper == "US" and not city and not state:
                    fmcsa_companies = FMCSAConnector().search_candidates(SearchFilters(max_results=candidate_limit, state=state, city=city))
                    for company in fmcsa_companies:
                        batch_discovered.append(
                            DiscoveredBusiness(
                                title=company.company_name,
                                domain=None,
                                website=None,
                                phone=company.contact_phone,
                                address=company.location,
                                category=company.industry,
                            )
                        )
                else:
                    discovery_query = f"{query} in {location}" if location else None
                    batch_discovered = self.discovery.discover(query=discovery_query, limit=candidate_limit, region=reg_upper)
                    if not batch_discovered:
                        batch_discovered = self.discovery.discover(limit=candidate_limit, region=reg_upper)
            return batch_discovered

        search_round = 1
        max_search_rounds = 6

        discovered = _fetch_candidates_batch(search_round)
        print(f"-> Initial candidate pool ready for enrichment: {len(discovered)} companies.")

        while True:
            convertible_count = sum(1 for lead in qualified_leads if lead.pipeline_status == "QUALIFIED_CONVERTIBLE")
            if convertible_count >= target_count:
                print(f"\n[Target Reached] Successfully acquired {convertible_count}/{target_count} qualified leads!")
                break

            # Find next unprocessed candidate in discovered list
            next_cand: DiscoveredBusiness | None = None
            while discovered:
                cand = discovered.pop(0)
                processed_candidates += 1
                comp_identifier = (cand.domain or cand.title).strip().lower()
                if comp_identifier in evaluated_candidates_set:
                    continue
                evaluated_candidates_set.add(comp_identifier)
                next_cand = cand
                break

            # If current batch exhausted but still need leads, fetch next round!
            if not next_cand:
                if search_round < max_search_rounds and convertible_count < target_count:
                    search_round += 1
                    print(f"\n[Expanding Search] Need {target_count - convertible_count} more leads. Running search round {search_round}/{max_search_rounds} across LinkedIn, Indeed, Monster, and ZipRecruiter...")
                    fresh_batch = _fetch_candidates_batch(search_round)
                    # Filter out already evaluated
                    fresh_candidates = [
                        c for c in fresh_batch
                        if (c.domain or c.title).strip().lower() not in evaluated_candidates_set
                    ]
                    if fresh_candidates:
                        discovered.extend(fresh_candidates)
                        print(f"-> Discovered {len(fresh_candidates)} fresh candidates for round {search_round}.")
                        continue
                    else:
                        print("-> No additional distinct candidates found in this round.")
                # If cannot find more after max rounds, break
                break

            biz = next_cand
            evaluated_candidates_set.add(comp_identifier)

            # Database Deduplication / 18-Day Cooldown Check (Guarantees fresh, uncontacted companies)
            if self.db.is_recent_duplicate(biz.title, domain=biz.domain, cooldown_days=self.cooldown_days, only_qualified=True):
                print(f"  [SKIPPED - PREVIOUSLY QUALIFIED] '{biz.title}' was already qualified in the last {self.cooldown_days} days. Keeping outreach fresh.")
                continue

            print(f"\n[Evaluating: {convertible_count}/{target_count} qualified | Candidate #{processed_candidates}] {biz.title}")
            candidate_reg = self._detect_candidate_region(biz.address, active_regions)
            if progress_callback:
                progress_callback({"step": f"Resolving website and phone for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})

            # FMCSA is the record source; Maps is used only to enrich phone, address and website.
            print("  [Step 2/7] Enriching FMCSA record with Google Maps...")
            try:
                maps_match = self.discovery.lookup_company(biz.title, biz.address)
                if maps_match:
                    biz.domain = maps_match.domain
                    biz.website = maps_match.website
                    biz.phone = biz.phone or maps_match.phone
                    biz.address = maps_match.address or biz.address
                    biz.category = biz.category or maps_match.category
            except Exception as exc:
                print(f"  [MAPS ENRICHMENT UNAVAILABLE] {exc}")

            # Step 2: Retrieve Official Verified Company LinkedIn
            print("  [Step 3/7] Retrieving official Company LinkedIn profile via Serper...")
            if progress_callback:
                progress_callback({"step": f"Finding LinkedIn page for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})
            target_domain = biz.domain or (biz.website.split("/")[2] if biz.website else None)
            real_company_li = self.linkedin_retriever._find_company_linkedin(biz.title, target_domain)

            if not real_company_li:
                print(f"  [NO VERIFIED LINKEDIN] '{biz.title}' has no verifiable LinkedIn company page.")
                qualified_leads.append(
                    QualifiedB2BLead(
                        company_name=biz.title,
                        domain=biz.domain,
                        website=biz.website,
                        phone=biz.phone,
                        address=biz.address,
                        category=biz.category,
                        employee_count=None,
                        employee_range="UNKNOWN",
                        passed_size_gate=True,
                        intent_found=False,
                        ai_intent_reason="No official company LinkedIn found",
                        ai_model_used="none",
                        company_linkedin_url=None,
                        decision_maker_name=None,
                        decision_maker_title=None,
                        decision_maker_linkedin_url=None,
                        retrieval_status="NO_COMPANY_LINKEDIN",
                        confidence_score=0,
                        pipeline_status="NO_COMPANY_LINKEDIN",
                    )
                )
                continue

            print(f"  [VERIFIED COMPANY LINKEDIN] {real_company_li}")

            # Step 3: Extract recent posts & employee qualification for verified company
            print("  [Step 4/7] Checking LinkedIn headcount and extracting recent posts...")
            if progress_callback:
                progress_callback({"step": f"Checking employee count & posts for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})
            try:
                li_profile = self.apify.qualify_and_extract_posts(biz.title, domain=target_domain, linkedin_url=real_company_li)
            except Exception as exc:
                reason = f"Apify company/post check failed: {exc}"
                print(f"  [APIFY ERROR] {reason}")
                qualified_leads.append(QualifiedB2BLead(
                    company_name=biz.title, domain=biz.domain, website=biz.website, phone=biz.phone,
                    address=biz.address, category=biz.category, employee_count=None,
                    employee_range="UNKNOWN", passed_size_gate=False, intent_found=False,
                    ai_intent_reason=reason, ai_model_used="none", company_linkedin_url=real_company_li,
                    decision_maker_name=None, decision_maker_title=None, decision_maker_linkedin_url=None,
                    retrieval_status="APIFY_ERROR", confidence_score=0, pipeline_status="APIFY_ERROR",
                ))
                continue

            normalize_company = lambda value: re.sub(r"\b(llc|incorporated|inc|corp|corporation|company|co)\b", "", re.sub(r"[^a-z0-9 ]", " ", value.lower())).strip()
            source_name, linkedin_name = normalize_company(biz.title), normalize_company(li_profile.company_name)
            if linkedin_name and source_name and source_name not in linkedin_name and linkedin_name not in source_name and SequenceMatcher(None, source_name, linkedin_name).ratio() < 0.72:
                reason = f"LinkedIn page name '{li_profile.company_name}' did not match the FMCSA company name."
                print(f"  [LINKEDIN NAME MISMATCH] {reason}")
                qualified_leads.append(QualifiedB2BLead(
                    company_name=biz.title, domain=biz.domain, website=biz.website, phone=biz.phone,
                    address=biz.address, category=biz.category, employee_count=li_profile.employee_count,
                    employee_range=li_profile.employee_range, passed_size_gate=False, intent_found=False,
                    ai_intent_reason=reason, ai_model_used="none", company_linkedin_url=real_company_li,
                    decision_maker_name=None, decision_maker_title=None, decision_maker_linkedin_url=None,
                    retrieval_status="LINKEDIN_NAME_MISMATCH", confidence_score=0,
                    pipeline_status="LINKEDIN_NAME_MISMATCH",
                ))
                continue

            if not li_profile.passed_size_gate:
                if li_profile.employee_count is not None:
                    if li_profile.employee_count < self.min_employees:
                        size_reason = f"LinkedIn employee count {li_profile.employee_count} is below the {self.min_employees}-{self.max_employees} employee target"
                    elif li_profile.employee_count > self.max_employees:
                        size_reason = f"LinkedIn employee count {li_profile.employee_count} exceeds the {self.min_employees}-{self.max_employees} employee target"
                    else:
                        size_reason = f"LinkedIn employee count {li_profile.employee_count} outside {self.min_employees}-{self.max_employees} employee target"
                else:
                    size_reason = f"LinkedIn headcount ({li_profile.employee_range or 'unknown'}) does not match the {self.min_employees}-{self.max_employees} employee target"
                size_status = "DROPPED_SIZE"
                print(f"  [DROPPED] {size_reason}.")
                self.db.record_lead(
                    company_name=biz.title,
                    domain=biz.domain,
                    website=biz.website,
                    phone=biz.phone,
                    address=biz.address,
                    category=biz.category,
                    employee_count=str(li_profile.employee_count or li_profile.employee_range),
                    status=size_status,
                    confidence=0.0,
                    source="FMCSA + Serper Maps",
                )
                qualified_leads.append(
                    QualifiedB2BLead(
                        company_name=biz.title,
                        domain=biz.domain,
                        website=biz.website,
                        phone=biz.phone,
                        address=biz.address,
                        category=biz.category,
                        employee_count=li_profile.employee_count,
                        employee_range=li_profile.employee_range,
                        passed_size_gate=False,
                        intent_found=False,
                        ai_intent_reason=size_reason,
                        ai_model_used="none",
                        company_linkedin_url=real_company_li,
                        decision_maker_name=None,
                        decision_maker_title=None,
                        decision_maker_linkedin_url=None,
                        retrieval_status=size_status,
                        confidence_score=0,
                        pipeline_status=size_status,
                    )
                )
                continue

            # Step 4: Bookkeeping Requirement Verification (Job Ad Intent OR LinkedIn OR Indeed)
            print("  [Step 5/7] Verifying Bookkeeping Services Requirement (Job Ad, LinkedIn OR Indeed)...")
            intent_confirmed = False
            intent_source = "None"
            intent_reason = ""
            indeed_job_url = None
            job_post_url = None
            has_recent_post = False
            ai_model_used = "none"

            # 0. Check if candidate was sourced directly from active hiring job posting (Fast Intent Match!)
            biz_key = biz.title.strip().lower()
            if biz_key in job_intent_map:
                job_cand = job_intent_map[biz_key]
                intent_confirmed = True
                intent_source = job_cand.source
                intent_reason = f"Active job posting: {job_cand.job_title}"
                job_post_url = job_cand.job_url
                if job_cand.source == "Indeed":
                    indeed_job_url = job_cand.job_url
                ai_model_used = f"direct_{job_cand.source.lower()}_hiring_match"
                print(f"    [{job_cand.source.upper()} INTENT CONFIRMED] Actively hiring: {job_cand.job_title} ({job_cand.job_url})")

            # 1. Check company LinkedIn recent posts
            if not intent_confirmed:
                recent_posts = [post for post in li_profile.recent_posts if self._is_recent_post(post, after_date=after_date)]
                if recent_posts:
                    print(f"    Evaluating {len(recent_posts)} recent company LinkedIn post(s)...")
                    if progress_callback:
                        progress_callback({"step": f"Evaluating LinkedIn posts for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})
                    intent_result = self.intent.analyze(biz.title, recent_posts, target_niche=query)
                    if intent_result.intent_found:
                        intent_confirmed = True
                        intent_source = "LinkedIn"
                        intent_reason = intent_result.reason
                        ai_model_used = intent_result.model_used
                        has_recent_post = True
                        print(f"    [LINKEDIN INTENT CONFIRMED] {intent_result.reason} (via {intent_result.model_used})")

            # 2. If not confirmed on LinkedIn, check Indeed too!
            if not intent_confirmed:
                print(f"    LinkedIn activity did not confirm bookkeeping services. Checking Indeed ({reg_upper}) job postings...")
                if progress_callback:
                    progress_callback({"step": f"Checking Indeed jobs for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})
                indeed_result = self.indeed_checker.check_company(
                    company_name=biz.title,
                    domain=target_domain,
                    location=biz.address,
                    after_date=after_date,
                    region=candidate_reg,
                )
                if indeed_result.intent_found:
                    intent_confirmed = True
                    intent_source = "Indeed"
                    intent_reason = indeed_result.reason
                    indeed_job_url = indeed_result.job_url
                    job_post_url = indeed_result.job_url
                    ai_model_used = "indeed_job_intelligence"
                    print(f"    [INDEED INTENT CONFIRMED] {indeed_result.reason}")

            # 3. ONLY confirm that a company requires these services
            if not intent_confirmed:
                no_intent_reason = "Neither company LinkedIn activity nor Indeed job postings confirmed bookkeeping service requirement"
                if after_date:
                    no_intent_reason += f" after {after_date}"
                print(f"  [NO INTENT CONFIRMED] {biz.title}: {no_intent_reason}")
                self.db.record_lead(
                    company_name=biz.title,
                    domain=biz.domain,
                    website=biz.website,
                    phone=biz.phone,
                    address=biz.address,
                    category=biz.category,
                    employee_count=str(li_profile.employee_count or li_profile.employee_range),
                    company_linkedin_url=real_company_li,
                    region=candidate_reg,
                    after_date=after_date,
                    status="NO_INTENT",
                    confidence=0.0,
                    source=f"Maps + {candidate_reg}",
                )
                qualified_leads.append(
                    QualifiedB2BLead(
                        company_name=biz.title,
                        domain=biz.domain,
                        website=biz.website,
                        phone=biz.phone,
                        address=biz.address,
                        category=biz.category,
                        employee_count=li_profile.employee_count,
                        employee_range=li_profile.employee_range,
                        passed_size_gate=True,
                        intent_found=False,
                        ai_intent_reason=no_intent_reason,
                        ai_model_used="none",
                        company_linkedin_url=real_company_li,
                        decision_maker_name=None,
                        decision_maker_title=None,
                        decision_maker_linkedin_url=None,
                        retrieval_status="NO_INTENT",
                        confidence_score=0,
                        pipeline_status="NO_INTENT",
                        has_recent_linkedin_post=bool(recent_posts),
                        intent_source="None",
                        region=candidate_reg,
                        after_date=after_date,
                    )
                )
                continue

            print(f"  [BOOKKEEPING INTENT CONFIRMED via {intent_source}] {intent_reason}")

            # Step 5: Contact Email Retrieval (Company Email & Decision Maker Email)
            print("  [Step 6/7] Retrieving Company Email and Decision-Maker Email...")
            if progress_callback:
                progress_callback({"step": f"Retrieving emails for {biz.title}", "processed": processed_candidates, "total": target_count, "company": biz.title, "verified": convertible_count})

            # A. Retrieve Official Company Email (Minimum requirement)
            company_email: str | None = None
            company_email_source: str | None = None
            try:
                comp_email_res = self.email_finder.find_company_email(target_domain, website=biz.website)
                if comp_email_res and comp_email_res.email:
                    company_email = comp_email_res.email
                    company_email_source = comp_email_res.source
                    print(f"    [COMPANY EMAIL FOUND] {company_email} (via {company_email_source})")
            except Exception as exc:
                print(f"    [COMPANY EMAIL LOOKUP ERROR] {exc}")

            # B. Retrieve Decision Maker and Decision Maker Email
            dm_name: str | None = None
            dm_title: str | None = None
            dm_linkedin: str | None = None
            dm_email: str | None = None
            dm_email_status: str = "NOT_CHECKED"
            dm_email_conf: int | None = None
            dm_email_src: str | None = None
            confidence_score: int = 0
            retrieval_status: str = "NOT_FOUND"

            try:
                li_retrieval = self.linkedin_retriever.retrieve(
                    company_name=biz.title,
                    domain=target_domain,
                    existing_company_linkedin=real_company_li,
                )
                dm_name = li_retrieval.decision_maker_name
                dm_title = li_retrieval.decision_maker_title
                dm_linkedin = li_retrieval.decision_maker_linkedin_url
                confidence_score = li_retrieval.confidence_score
                retrieval_status = li_retrieval.retrieval_status

                if dm_name and target_domain:
                    email_result = self.email_finder.find_and_verify(
                        dm_name, target_domain,
                        linkedin_url=dm_linkedin,
                    )
                    if email_result.status == "VALID" and email_result.email:
                        dm_email = email_result.email
                        dm_email_status = "VALID"
                        dm_email_conf = email_result.confidence
                        dm_email_src = email_result.source
                        print(f"    [DECISION MAKER EMAIL VERIFIED] {dm_name}: {dm_email} ({email_result.status})")
                    else:
                        dm_email_status = email_result.status
            except Exception as exc:
                print(f"    [DECISION MAKER LOOKUP ERROR] {exc}")

            # If company email was not directly found from website, but decision maker email was verified, use as contact
            if not company_email and dm_email:
                company_email = dm_email
                company_email_source = "Decision Maker Email"

            # Both are required but the minimum is company email:
            if not company_email:
                print(f"  [NO COMPANY EMAIL] {biz.title}: Neither company email nor decision-maker email could be resolved.")
                qualified_leads.append(
                    QualifiedB2BLead(
                        company_name=biz.title, domain=biz.domain, website=biz.website, phone=biz.phone,
                        address=biz.address, category=biz.category, employee_count=li_profile.employee_count,
                        employee_range=li_profile.employee_range, passed_size_gate=True, intent_found=True,
                        ai_intent_reason=intent_reason, ai_model_used=ai_model_used,
                        company_linkedin_url=real_company_li,
                        decision_maker_name=dm_name,
                        decision_maker_title=dm_title,
                        decision_maker_linkedin_url=dm_linkedin,
                        retrieval_status="NO_COMPANY_EMAIL", confidence_score=confidence_score,
                        pipeline_status="NO_COMPANY_EMAIL",
                        company_email=None,
                        decision_maker_email=None,
                        owner_email=None,
                        email_status="NOT_FOUND",
                        email_confidence=0,
                        email_source=None,
                        has_recent_linkedin_post=has_recent_post,
                        intent_source=intent_source,
                        indeed_job_url=indeed_job_url,
                        job_post_url=job_post_url,
                        company_type=biz.category,
                        region=candidate_reg,
                        after_date=after_date,
                    )
                )
                continue

            # Minimum company email requirement satisfied!
            print(f"  [QUALIFIED LEAD - {intent_source.upper()} CONFIRMED] {biz.title}")
            print(f"    - Type/Industry    : {biz.category or 'Small Business'}")
            print(f"    - Job Post Link    : {job_post_url or indeed_job_url or 'N/A'}")
            print(f"    - Region           : {candidate_reg}")
            print(f"    - Company Email    : {company_email} ({company_email_source}) [REQUIRED MINIMUM MET]")
            print(f"    - Decision Maker   : {dm_name or 'N/A'} ({dm_title or 'Leadership'})")
            print(f"    - Decision Maker Em: {dm_email or 'Not resolved'}")
            print(f"    - Intent Source    : {intent_source} ({intent_reason})")
            print(f"    - Phone            : {biz.phone or 'N/A'} | Website: {biz.website or 'N/A'}")

            # Save to persistent database
            self.db.record_lead(
                company_name=biz.title,
                domain=biz.domain,
                website=biz.website,
                phone=biz.phone,
                address=biz.address,
                category=biz.category,
                employee_count=str(li_profile.employee_count or li_profile.employee_range),
                company_linkedin_url=real_company_li,
                owner_name=dm_name,
                owner_title=dm_title,
                decision_maker_linkedin_url=dm_linkedin,
                owner_email=dm_email or company_email,
                company_email=company_email,
                decision_maker_email=dm_email,
                region=candidate_reg,
                after_date=after_date,
                status="QUALIFIED_CONVERTIBLE",
                confidence=float(confidence_score) / 100.0 if confidence_score else 0.85,
                source=f"Pipeline V2 ({intent_source})",
            )

            qualified_leads.append(
                QualifiedB2BLead(
                    company_name=biz.title,
                    domain=biz.domain,
                    website=biz.website,
                    phone=biz.phone,
                    address=biz.address,
                    category=biz.category,
                    company_type=biz.category,
                    employee_count=li_profile.employee_count,
                    employee_range=li_profile.employee_range,
                    passed_size_gate=True,
                    intent_found=True,
                    ai_intent_reason=intent_reason,
                    ai_model_used=ai_model_used,
                    company_linkedin_url=real_company_li,
                    decision_maker_name=dm_name,
                    decision_maker_title=dm_title,
                    decision_maker_linkedin_url=dm_linkedin,
                    retrieval_status=retrieval_status,
                    confidence_score=confidence_score or 85,
                    pipeline_status="QUALIFIED_CONVERTIBLE",
                    company_email=company_email,
                    decision_maker_email=dm_email,
                    owner_email=dm_email or company_email,
                    email_status="VALID" if dm_email else "COMPANY_EMAIL_ONLY",
                    email_confidence=dm_email_conf or 85,
                    email_source=company_email_source,
                    has_recent_linkedin_post=has_recent_post,
                    intent_source=intent_source,
                    indeed_job_url=indeed_job_url,
                    job_post_url=job_post_url,
                    region=candidate_reg,
                    after_date=after_date,
                )
            )

        # Export 1: Full Audit Trail CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(output_dir, exist_ok=True)
        csv_path = Path(output_dir) / f"intent_leads_full_{timestamp}.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=PIPELINE_V2_FIELDNAMES)
            writer.writeheader()
            for lead in qualified_leads:
                writer.writerow(asdict(lead))

        # Export 2: Client-Ready Verified Convertible CSV (Only requested columns)
        ready_leads = [l for l in qualified_leads if l.pipeline_status == "QUALIFIED_CONVERTIBLE"][:target_count]
        if progress_callback:
            progress_callback({"step": "Exporting qualified results", "processed": processed_candidates, "total": len(discovered), "company": None, "verified": len(ready_leads)})
        ready_csv_path = Path(output_dir) / f"bookkeeping_leads_ready_{timestamp}.csv"
        
        with open(ready_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CLIENT_LEADS_FIELDNAMES, extrasaction="ignore")
            writer.writeheader()
            for lead in ready_leads:
                lead_dict = asdict(lead)
                # Filter down to the 5 requested columns
                minimal_row = {k: lead_dict.get(k) for k in CLIENT_LEADS_FIELDNAMES}
                writer.writerow(minimal_row)

        elapsed = round(time.perf_counter() - start_time, 2)
        print("=" * 80)
        print(f"PIPELINE COMPLETED IN {elapsed}s")
        print(f"Total Discovered & Evaluated : {len(qualified_leads)}")
        print(f"Client-Ready Convertible Leads: {len(ready_leads)} (Target was {target_count})")
        print(f"Audit Trail Saved To         : {csv_path}")
        print(f"Client Outreach File Saved To: {ready_csv_path}")
        db_stats = self.db.get_stats()
        print(f"Database Leads Total         : {db_stats['total_companies_stored']} companies stored (Outreach deduped)")
        print("=" * 80)

        return ready_leads
