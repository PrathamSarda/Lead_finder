"""
Multi-Tool Intent-Driven Lead Generation Pipeline Coordinator.
Implements the 5-stage technical specification:
1. Local Discovery: Serper.dev (Google Maps) -> Business names, phones, websites, domains
2. Size Gate: Apify LinkedIn scraper -> Filters companies with <= 20 employees (drops > 20)
3. Feed Extraction: Apify Posts Scraper -> Pulls 5-10 recent public posts
4. AI Intent Verification: Gemini/OpenAI intent analysis -> Evaluates financial/scaling buying signals
5. LinkedIn Profile Retrieval: Official Company LinkedIn URL & Decision-Maker Personal LinkedIn Profile URL (zero Hunter.io costs)
6. Export to CSV & SQLite DB with complete provenance
"""
from __future__ import annotations

import csv
import os
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from automation.pipeline_v2.apify_enricher import ApifyLinkedInEnricher
from automation.pipeline_v2.intent_analyzer import IntentAnalyzer
from automation.pipeline_v2.lead_db import LeadDatabase
from automation.pipeline_v2.linkedin_retriever import LinkedInProfileRetriever
from automation.pipeline_v2.serper_discovery import (
    DEFAULT_DISCOVERY_QUERIES,
    DiscoveredBusiness,
    SerperMapsDiscovery,
)


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


# Minimal client-facing export schema
CLIENT_LEADS_FIELDNAMES = [
    "company_name",
    "website",
    "company_linkedin_url",
    "decision_maker_name",
    "decision_maker_linkedin_url",
]

# Internal full audit trail schema
PIPELINE_V2_FIELDNAMES = [
    "company_name",
    "domain",
    "website",
    "phone",
    "address",
    "category",
    "employee_count",
    "employee_range",
    "passed_size_gate",
    "intent_found",
    "ai_intent_reason",
    "ai_model_used",
    "company_linkedin_url",
    "decision_maker_name",
    "decision_maker_title",
    "decision_maker_linkedin_url",
    "retrieval_status",
    "confidence_score",
    "pipeline_status",
    "created_at",
]


class MultiToolLeadPipeline:
    """End-to-End Orchestrator for the Intent-Driven Multi-Tool Pipeline."""

    def __init__(
        self,
        serper_key: str | None = None,
        apify_token: str | None = None,
        gemini_key: str | None = None,
        openai_key: str | None = None,
        db_path: str | Path | None = None,
        cooldown_days: int = 18,
    ):
        self.discovery = SerperMapsDiscovery(serper_key)
        self.apify = ApifyLinkedInEnricher(apify_token)
        self.intent = IntentAnalyzer(openai_api_key=openai_key, gemini_api_key=gemini_key)
        self.linkedin_retriever = LinkedInProfileRetriever(serper_api_key=serper_key)
        self.db = LeadDatabase(db_path=db_path)
        self.cooldown_days = cooldown_days

    def run(
        self,
        query: str,
        target_count: int = 15,
        output_dir: str = "outputs",
    ) -> list[QualifiedB2BLead]:
        """Runs the entire multi-tool workflow until target_count qualified leads are discovered."""
        print("=" * 80)
        print("PROKIZEN GLOBAL - MULTI-TOOL INTENT LEAD GENERATION PIPELINE")
        print(f"Target Query  : {query}")
        print(f"Target Count  : {target_count} SMB leads (<20 employees with verified intent & LinkedIn profiles)")
        print(f"Cooldown Rule : Excludes companies contacted in the last {self.cooldown_days} days (allows fresh rotation)")
        print(f"Started at    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        start_time = time.perf_counter()

        # Build dynamic queries list starting with user query, then rotating across diverse trade/cities
        query_pool = [query] if query else []
        query_pool.extend([q for q in DEFAULT_DISCOVERY_QUERIES if q != query])

        qualified_leads: list[QualifiedB2BLead] = []
        evaluated_candidates_set: set[str] = set()
        
        query_idx = 0
        max_queries = len(query_pool)

        while sum(1 for l in qualified_leads if l.pipeline_status == "QUALIFIED_CONVERTIBLE") < target_count and query_idx < max_queries:
            active_q = query_pool[query_idx]
            query_idx += 1

            needed = target_count - sum(1 for l in qualified_leads if l.pipeline_status == "QUALIFIED_CONVERTIBLE")
            pool_size = max(needed * 3, 20)

            print(f"\n[Step 1/5] Sourcing candidates via Google Maps for: '{active_q}' (Still need: {needed} leads)...")
            discovered = self.discovery.discover(query=active_q, limit=pool_size)
            print(f"-> Sourced {len(discovered)} candidates from Google Maps.")

            for biz in discovered:
                # Check target fulfillment
                convertible_count = sum(1 for l in qualified_leads if l.pipeline_status == "QUALIFIED_CONVERTIBLE")
                if convertible_count >= target_count:
                    break

                comp_identifier = (biz.domain or biz.title).strip().lower()
                if comp_identifier in evaluated_candidates_set:
                    continue
                evaluated_candidates_set.add(comp_identifier)

                # Database Deduplication / 18-Day Cooldown Check
                if self.db.is_recent_duplicate(biz.title, domain=biz.domain, cooldown_days=self.cooldown_days):
                    print(f"  [SKIPPED - RECENT RUN] '{biz.title}' was processed within the last {self.cooldown_days} days. Keeping outreach fresh.")
                    continue

                print(f"\n[Evaluating: {convertible_count}/{target_count}] {biz.title} ({biz.domain or 'No Domain'})")

                # Step 2: Retrieve Official Verified Company LinkedIn
                print("  [Step 2/5] Retrieving verified Company LinkedIn profile via search...")
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
                print("  [Step 3/5] Extracting recent posts and evaluating employee size...")
                li_profile = self.apify.qualify_and_extract_posts(biz.title, domain=target_domain, linkedin_url=real_company_li)

                if not li_profile.passed_size_gate:
                    print(f"  [DROPPED] Company size ({li_profile.employee_count or li_profile.employee_range}) exceeds 20 employee threshold.")
                    self.db.record_lead(
                        company_name=biz.title,
                        domain=biz.domain,
                        website=biz.website,
                        phone=biz.phone,
                        address=biz.address,
                        category=biz.category,
                        employee_count=str(li_profile.employee_count or li_profile.employee_range),
                        status="DROPPED_SIZE",
                        confidence=0.0,
                        source="Google Maps",
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
                            ai_intent_reason="Dropped at size gate (>20 employees)",
                            ai_model_used="none",
                            company_linkedin_url=real_company_li,
                            decision_maker_name=None,
                            decision_maker_title=None,
                            decision_maker_linkedin_url=None,
                            retrieval_status="DROPPED_SIZE",
                            confidence_score=0,
                            pipeline_status="DROPPED_SIZE",
                        )
                    )
                    continue

                if not li_profile.recent_posts:
                    print(f"  [NO RECENT POSTS] '{biz.title}' has no recent public LinkedIn posts.")
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
                            ai_intent_reason="No recent LinkedIn posts found",
                            ai_model_used="none",
                            company_linkedin_url=real_company_li,
                            decision_maker_name=None,
                            decision_maker_title=None,
                            decision_maker_linkedin_url=None,
                            retrieval_status="NO_RECENT_POSTS",
                            confidence_score=0,
                            pipeline_status="NO_RECENT_POSTS",
                        )
                    )
                    continue

                # Step 4: AI Intent and Buying Signal Analysis on recent posts
                print(f"  [Step 4/5] Evaluating financial hiring & scaling intent on {len(li_profile.recent_posts)} recent post(s)...")
                intent_result = self.intent.analyze(biz.title, li_profile.recent_posts)

                if not intent_result.intent_found:
                    print(f"  [NO INTENT] {intent_result.reason} (via {intent_result.model_used})")
                    self.db.record_lead(
                        company_name=biz.title,
                        domain=biz.domain,
                        website=biz.website,
                        phone=biz.phone,
                        address=biz.address,
                        category=biz.category,
                        employee_count=str(li_profile.employee_count or li_profile.employee_range),
                        company_linkedin_url=real_company_li,
                        status="NO_INTENT",
                        confidence=0.0,
                        source="Google Maps",
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
                            ai_intent_reason=intent_result.reason,
                            ai_model_used=intent_result.model_used,
                            company_linkedin_url=real_company_li,
                            decision_maker_name=None,
                            decision_maker_title=None,
                            decision_maker_linkedin_url=None,
                            retrieval_status="NO_INTENT",
                            confidence_score=0,
                            pipeline_status="NO_INTENT",
                        )
                    )
                    continue

                print(f"  [INTENT VERIFIED] {intent_result.reason} (via {intent_result.model_used})")

                # Step 5: Decision Maker Retrieval for verified company
                print("  [Step 5/5] Retrieving Decision-Maker Profile URL...")
                li_retrieval = self.linkedin_retriever.retrieve(
                    company_name=biz.title,
                    domain=target_domain,
                    existing_company_linkedin=real_company_li,
                )

                has_profile = bool(li_retrieval.company_linkedin_url)

                if has_profile:
                    print(f"  [QUALIFIED LINKEDIN LEAD] {biz.title}")
                    print(f"    - Company LinkedIn : {li_retrieval.company_linkedin_url or 'N/A'}")
                    print(f"    - Decision Maker   : {li_retrieval.decision_maker_name or 'N/A'} ({li_retrieval.decision_maker_title or 'Leadership'})")
                    print(f"    - Decision Maker LI: {li_retrieval.decision_maker_linkedin_url or 'N/A'}")
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
                        company_linkedin_url=li_retrieval.company_linkedin_url,
                        owner_name=li_retrieval.decision_maker_name,
                        owner_title=li_retrieval.decision_maker_title,
                        decision_maker_linkedin_url=li_retrieval.decision_maker_linkedin_url,
                        status="QUALIFIED_CONVERTIBLE",
                        confidence=float(li_retrieval.confidence_score) / 100.0,
                        source="Pipeline V2 Multi-Tool",
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
                            intent_found=True,
                            ai_intent_reason=intent_result.reason,
                            ai_model_used=intent_result.model_used,
                            company_linkedin_url=li_retrieval.company_linkedin_url,
                            decision_maker_name=li_retrieval.decision_maker_name,
                            decision_maker_title=li_retrieval.decision_maker_title,
                            decision_maker_linkedin_url=li_retrieval.decision_maker_linkedin_url,
                            retrieval_status=li_retrieval.retrieval_status,
                            confidence_score=li_retrieval.confidence_score,
                            pipeline_status="QUALIFIED_CONVERTIBLE",
                        )
                    )
                else:
                    print("  [NO_LINKEDIN_FOUND] Intent verified, but LinkedIn profiles could not be resolved.")
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
                            intent_found=True,
                            ai_intent_reason=intent_result.reason,
                            ai_model_used=intent_result.model_used,
                            company_linkedin_url=None,
                            decision_maker_name=None,
                            decision_maker_title=None,
                            decision_maker_linkedin_url=None,
                            retrieval_status="NOT_FOUND",
                            confidence_score=0,
                            pipeline_status="INTENT_VERIFIED_NO_LINKEDIN",
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
