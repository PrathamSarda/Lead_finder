"""
Leads discovery and pipeline management endpoints.

Provides:
- Listing discovered leads from runs / outputs
- Filter, search, and aggregated statistics
- Running live FMCSA discovery or benchmark test cases with custom company count
- Real-time run status and live progress tracking
- Professional Excel (.xlsx) and CSV report exports
"""
from __future__ import annotations

import csv
import io
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from automation.verification.models import EXPORT_FIELDNAMES

try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings

router = APIRouter()

WORKSPACE_DIR = Path(__file__).resolve().parents[5]
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


# Global running state for discovery / test pipeline
RUN_STATE_LOCK = threading.Lock()
RUN_CANCEL_FLAG = False

run_state: Dict[str, Any] = {
    "status": "idle",  # "idle" | "running" | "completed" | "error"
    "run_id": None,
    "mode": "discovery",
    "requested_count": 10,
    "processed_count": 0,
    "current_company": None,
    "current_step": "Idle",
    "total_steps": 3,
    "verified_count": 0,
    "full_lead_count": 0,
    "start_time": None,
    "elapsed_seconds": 0,
    "output_file": None,
    "error": None,
    "logs": [],
}


def add_log(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    with RUN_STATE_LOCK:
        run_state["logs"].append(formatted)
        if len(run_state["logs"]) > 200:
            run_state["logs"] = run_state["logs"][-200:]


def get_all_csv_files() -> List[Path]:
    """Find all lead CSV output files sorted by modification time (newest first)."""
    if not OUTPUTS_DIR.exists():
        return []
    patterns = ["bookkeeping_leads_*.csv", "leads_*.csv", "intent_leads_*.csv"]
    files: List[Path] = []
    for pat in patterns:
        files.extend(OUTPUTS_DIR.glob(pat))
    # Also include benchmark CSVs if present
    benchmark_dir = OUTPUTS_DIR / "benchmark"
    if benchmark_dir.exists():
        files.extend(benchmark_dir.glob("*.csv"))
    # Remove duplicates if any
    files = list({f.resolve(): f for f in files}.values())
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def parse_csv_lead(row: Dict[str, str], source_file: str) -> Dict[str, Any]:
    """Normalize a CSV lead row into a consistent dictionary, supporting both v1 and intent pipelines."""
    # Support both column namings
    company_name = (
        row.get("Company Name")
        or row.get("company_name")
        or ""
    ).strip()

    location = (
        row.get("Location Address")
        or row.get("address")
        or row.get("location")
        or ""
    ).strip()

    company_email = (
        row.get("Company Email")
        or row.get("company_email")
        or ""
    ).strip()

    decision_maker_email = (
        row.get("Decision Maker Email")
        or row.get("decision_maker_email")
        or row.get("Verified Email")
        or row.get("owner_email")
        or ""
    ).strip()

    # General email field for backwards compatibility
    email = decision_maker_email or company_email or (
        row.get("email")
        or ""
    ).strip()

    region = (
        row.get("Region")
        or row.get("region")
        or "US"
    ).strip().upper()

    after_date = (
        row.get("After Date")
        or row.get("after_date")
        or ""
    ).strip()

    phone = (
        row.get("Phone")
        or row.get("phone")
        or ""
    ).strip()

    website = (
        row.get("Website")
        or row.get("website")
        or row.get("domain")
        or ""
    ).strip()

    status_raw = (
        row.get("Lead Status")
        or row.get("pipeline_status")
        or row.get("status")
        or "UNRESOLVED"
    ).strip().upper()

    # Normalize status for dashboard display
    if status_raw in ("READY_FOR_OUTREACH", "QUALIFIED_CONVERTIBLE", "VERIFIED"):
        status = "VERIFIED"
        if company_email and decision_maker_email:
            lead_tier = "FULL_LEAD"
        elif company_email:
            lead_tier = "COMPANY_EMAIL_ONLY"
        else:
            lead_tier = "WEBSITE_ONLY"
    elif status_raw in ("NEEDS_REVIEW", "INTENT_VERIFIED_NO_EMAIL", "NO_COMPANY_EMAIL"):
        status = "NEEDS_REVIEW"
        lead_tier = "WEBSITE_ONLY"
    elif status_raw in ("DROPPED_SIZE", "NO_INTENT"):
        status = "UNRESOLVED"
        lead_tier = "UNRESOLVED"
    else:
        status = status_raw
        lead_tier = row.get("lead_tier", "UNRESOLVED").strip().upper()

    status_reason = (
        row.get("Bookkeeping Intent Reason")
        or row.get("ai_intent_reason")
        or row.get("status_reason")
        or ""
    ).strip()
    intent_raw = str(row.get("intent_found", "")).strip().lower()
    intent_source = (row.get("intent_source") or row.get("Intent Source") or "").strip()
    indeed_job_url = (row.get("indeed_job_url") or row.get("Indeed Job URL") or "").strip()

    if intent_raw in {"true", "1", "yes"}:
        intent_status = f"CONFIRMED ({intent_source})" if intent_source and intent_source != "None" else "CONFIRMED"
    elif intent_raw in {"false", "0", "no"}:
        intent_status = "NOT CONFIRMED"
    else:
        intent_status = status_raw.replace("_", " ")

    employee_count = row.get("employee_count") or row.get("employee_range") or ""

    raw_conf = row.get("Verification Score") or row.get("email_confidence") or row.get("confidence") or "0"
    confidence_val = 0.0
    try:
        val = float(str(raw_conf).replace("%", "").strip() or 0.0)
        # Normalize: if provided as percentage (e.g. 92.0), scale down to 0.92
        confidence_val = val / 100.0 if val > 1.0 else val
    except (ValueError, TypeError):
        pass

    elapsed_val = 0.0
    try:
        elapsed_val = float(row.get("elapsed_seconds", 0.0) or 0.0)
    except (ValueError, TypeError):
        pass

    candidate_results_raw = row.get("candidate_results", "")
    candidates_list = []
    if candidate_results_raw:
        import json
        try:
            candidates_list = json.loads(candidate_results_raw)
        except Exception:
            pass

    owner_name = (
        row.get("Decision Maker Name")
        or row.get("decision_maker_name")
        or row.get("owner_name")
        or ""
    ).strip()
    owner_title = (
        row.get("Decision Maker Title")
        or row.get("decision_maker_title")
        or row.get("owner_title")
        or ""
    ).strip()
    company_linkedin_url = (
        row.get("Company LinkedIn")
        or row.get("company_linkedin_url")
        or row.get("linkedin")
        or ""
    ).strip()
    decision_maker_linkedin_url = (
        row.get("Decision Maker LinkedIn")
        or row.get("decision_maker_linkedin_url")
        or ""
    ).strip()

    return {
        "company_name": company_name,
        "location": location,
        "status": status,
        "lead_tier": lead_tier,
        "status_reason": status_reason,
        "intent_status": intent_status,
        "intent_reason": status_reason,
        "employee_count": employee_count,
        "website": website,
        "website_status": "VALID" if website else "",
        "website_source": row.get("website_source", ""),
        "email": email,
        "email_status": (row.get("email_status") or ("VERIFIED" if email else "")).strip().upper(),
        "email_source": row.get("email_source", ""),
        "email_confidence": row.get("email_confidence", ""),
        "has_recent_linkedin_post": str(row.get("has_recent_linkedin_post", "")).strip().lower() in {"true", "1", "yes"},
        "phone": phone,
        "phone_status": "VERIFIED" if phone else "",
        "phone_source": row.get("phone_source", ""),
        "confidence": confidence_val,
        "source": "intent_pipeline" if "bookkeeping" in source_file or "intent" in source_file else row.get("source", "fmcsa"),
        "candidate_results": candidates_list,
        "elapsed_seconds": elapsed_val,
        "created_at": row.get("created_at", "").strip(),
        "source_file": source_file,
        "owner_name": owner_name,
        "owner_title": owner_title,
        "company_linkedin_url": company_linkedin_url,
        "decision_maker_name": owner_name,
        "decision_maker_title": owner_title,
        "decision_maker_linkedin_url": decision_maker_linkedin_url,
        "company_email": company_email,
        "decision_maker_email": decision_maker_email,
        "region": region,
        "after_date": after_date,
        "intent_source": intent_source,
        "indeed_job_url": indeed_job_url,
    }


def load_leads_from_file(file_path: Path) -> List[Dict[str, Any]]:
    if not file_path.exists():
        return []
    leads: List[Dict[str, Any]] = []
    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed = parse_csv_lead(row, file_path.name)
                if parsed["company_name"]:
                    leads.append(parsed)
    except Exception as exc:
        print(f"Error loading {file_path}: {exc}")
    return leads


def load_all_leads_deduplicated() -> List[Dict[str, Any]]:
    """Loads all leads across all CSV files in outputs/ deduplicating by company_name."""
    files = get_all_csv_files()
    seen: Dict[str, Dict[str, Any]] = {}
    for f in files:
        file_leads = load_leads_from_file(f)
        for lead in file_leads:
            key = lead["company_name"].casefold()
            # If we already have this company, keep the one with higher confidence or verified status
            if key not in seen:
                seen[key] = lead
            else:
                existing = seen[key]
                if lead["lead_tier"] == "FULL_LEAD" and existing["lead_tier"] != "FULL_LEAD":
                    seen[key] = lead
                elif lead["confidence"] > existing["confidence"]:
                    seen[key] = lead
    return list(seen.values())


class RunRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=100, description="Number of companies to process")
    state: Optional[str] = Field(default=None, description="Optional US State filter (e.g. TX, GA, CA)")
    city: Optional[str] = Field(default=None, max_length=100, description="Optional city filter")
    mode: str = Field(default="bookkeeping", description="'bookkeeping' runs the full intent qualification workflow")
    niche: str = Field(default="bookkeeping, accounting, tax preparation, payroll, or scaling support", max_length=200)
    region: str = Field(default="US", description="Target region/country (US, UK, AU, CA)")
    after_date: Optional[str] = Field(default=None, description="Services required on or after date (YYYY-MM-DD)")


def _run_pipeline_worker(
    count: int,
    state: Optional[str],
    city: Optional[str],
    mode: str,
    niche: str,
    region: str = "US",
    after_date: Optional[str] = None,
) -> None:
    """Background worker executing the discovery or test cases pipeline."""
    global RUN_CANCEL_FLAG

    with RUN_STATE_LOCK:
        run_state["status"] = "running"
        run_state["mode"] = mode
        run_state["requested_count"] = count
        run_state["processed_count"] = 0
        run_state["verified_count"] = 0
        run_state["full_lead_count"] = 0
        run_state["start_time"] = time.time()
        run_state["error"] = None
        run_state["logs"] = []
        RUN_CANCEL_FLAG = False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"leads_{timestamp}.csv"
    output_path = OUTPUTS_DIR / out_filename
    with RUN_STATE_LOCK:
        run_state["run_id"] = out_filename
        run_state["output_file"] = str(output_path)

    add_log(f"Starting {mode.upper()} pipeline for {count} companies in region {region.upper()}...")
    if after_date:
        add_log(f"Cutoff Date Filter: Services needed on or after {after_date}")
    if state:
        add_log(f"Filter US State: {state.upper()}")

    results: List[Dict[str, Any]] = []

    try:
        from automation.intelligence.company_service import CompanyService
        from automation.intelligence.models import CompanyInput
        from automation.models.search_filters import SearchFilters
        from automation.sources.fmcsa.connector import FMCSAConnector
        from automation.verification.lead_verifier import LeadVerifier
        from automation.verification.models import VerificationStatus

        service = CompanyService()
        verifier = LeadVerifier()

        leads_to_process = []

        if mode == "bookkeeping" or mode == "intent":
            with RUN_STATE_LOCK:
                run_state["current_step"] = f"Discovering SMBs & Verifying Bookkeeping Intent ({region.upper()})"
            add_log(f"[Step 1/3] Running automated Bookkeeping Intent Discovery for {count} companies in {region.upper()}...")
            from automation.pipeline_v2.pipeline_orchestrator import MultiToolLeadPipeline
            
            intent_pipe = MultiToolLeadPipeline(
                serper_key=settings.SERPER_API_KEY,
                apify_token=settings.APIFY_API_TOKEN,
                gemini_key=settings.GEMINI_API_KEY,
                hunter_key=settings.HUNTER_API_KEY,
                company_actor=settings.APIFY_LINKEDIN_COMPANY_ACTOR,
                posts_actor=settings.APIFY_LINKEDIN_POSTS_ACTOR,
                min_employees=10,
                max_employees=15,
            )
            # Default automated query for bookkeeping candidates
            def report_pipeline_progress(event: dict[str, Any]) -> None:
                with RUN_STATE_LOCK:
                    run_state["current_step"] = event.get("step", "Processing")
                    run_state["current_company"] = event.get("company")
                    run_state["processed_count"] = int(event.get("processed", run_state["processed_count"]))
                    run_state["requested_count"] = int(event.get("total", run_state["requested_count"])) or count
                    run_state["verified_count"] = int(event.get("verified", run_state["verified_count"]))
                    run_state["full_lead_count"] = run_state["verified_count"]
                    msg = event.get("step")
                    company = event.get("company")
                    if msg:
                        run_state["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}" + (f": {company}" if company else ""))
                        run_state["logs"] = run_state["logs"][-200:]

            leads_result = intent_pipe.run(
                query=niche,
                target_count=count,
                output_dir=str(OUTPUTS_DIR),
                state=state,
                city=city,
                region=region,
                after_date=after_date,
                progress_callback=report_pipeline_progress,
                candidate_source="jobs",
            )
            
            with RUN_STATE_LOCK:
                run_state["verified_count"] = sum(1 for l in leads_result if l.pipeline_status == "QUALIFIED_CONVERTIBLE")
                run_state["full_lead_count"] = sum(1 for l in leads_result if l.pipeline_status == "QUALIFIED_CONVERTIBLE")
                run_state["status"] = "completed"
                run_state["current_step"] = "Complete"
                if run_state["start_time"]:
                    run_state["elapsed_seconds"] = round(time.time() - run_state["start_time"], 1)

            add_log(f"Bookkeeping Pipeline Finished! Found {run_state['verified_count']} verified leads ready for outreach.")
            return

        if mode == "test_batch":
            with RUN_STATE_LOCK:
                run_state["current_step"] = "Loading Curated Test Cases"
            add_log("[Step 1/3] Loading curated test companies batch...")
            from scripts.test_company_batch import load_sample_companies

            sample_comps = load_sample_companies()
            # If state filter given, filter sample companies
            if state:
                filtered = [c for c in sample_comps if (c.state or "").upper() == state.upper()]
                if filtered:
                    sample_comps = filtered
            sample_comps = sample_comps[:count]

            for sc in sample_comps:
                leads_to_process.append({
                    "company_name": sc.name,
                    "city": sc.city,
                    "state": sc.state,
                    "location": f"{sc.city}, {sc.state}" if sc.city and sc.state else (sc.state or "US"),
                })
        else:
            with RUN_STATE_LOCK:
                run_state["current_step"] = "Querying FMCSA Small Business Registry"
            add_log(f"[Step 1/3] Querying FMCSA database for up to {count} US small companies...")
            connector = FMCSAConnector()
            fmcsa_leads = connector.search(SearchFilters(max_results=count))
            add_log(f"-> Retrieved {len(fmcsa_leads)} active US company records from FMCSA.")

            for lead in fmcsa_leads:
                city, lead_state = None, None
                if lead.location and "," in lead.location:
                    parts = [p.strip() for p in lead.location.split(",", 1)]
                    city, lead_state = parts[0], parts[1]
                elif lead.location:
                    city = lead.location.strip()
                
                if state and lead_state and lead_state.upper() != state.upper():
                    continue

                leads_to_process.append({
                    "company_name": lead.company_name,
                    "city": city,
                    "state": lead_state,
                    "location": lead.location or "US",
                })

        total_target = len(leads_to_process)
        add_log(f"[Step 2/3] Resolving official websites & executing contact enrichment ({total_target} total)...")

        total_verified = 0
        total_full = 0

        for idx, item in enumerate(leads_to_process, start=1):
            if RUN_CANCEL_FLAG:
                add_log("Pipeline run cancelled by user.")
                break

            comp_name = item["company_name"]
            with RUN_STATE_LOCK:
                run_state["current_company"] = comp_name
                run_state["processed_count"] = idx - 1
                run_state["current_step"] = f"Resolving [{idx}/{total_target}]: {comp_name}"

            comp_start = time.perf_counter()
            add_log(f"[{idx}/{total_target}] Processing: {comp_name} ({item['location']})")

            company_input = CompanyInput(
                name=comp_name,
                city=item.get("city"),
                state=item.get("state"),
            )

            try:
                evidence = service.resolve(company_input)
                duration = round(time.perf_counter() - comp_start, 2)
                verified = verifier.verify(company_input, evidence, duration=duration)
                res_dict = verified.to_dict()

                if verified.status == VerificationStatus.VERIFIED.value:
                    total_verified += 1
                    if res_dict.get("lead_tier") == "FULL_LEAD":
                        total_full += 1
                        add_log(f"  [FULL LEAD] {comp_name} -> {verified.website} | Email: {verified.email} | Phone: {verified.phone}")
                    else:
                        add_log(f"  [WEBSITE ONLY] {comp_name} -> {verified.website}")
                elif verified.status == VerificationStatus.NEEDS_REVIEW.value:
                    add_log(f"  [NEEDS REVIEW] {comp_name} -> {verified.status_reason}")
                else:
                    add_log(f"  [UNRESOLVED] {comp_name} -> {verified.status_reason}")

                results.append(res_dict)

                with RUN_STATE_LOCK:
                    run_state["processed_count"] = idx
                    run_state["verified_count"] = total_verified
                    run_state["full_lead_count"] = total_full
                    if run_state["start_time"]:
                        run_state["elapsed_seconds"] = round(time.time() - run_state["start_time"], 1)

            except Exception as e:
                add_log(f"  [ERROR] {comp_name}: {e}")

        # Save to CSV
        with RUN_STATE_LOCK:
            run_state["current_step"] = "Writing results to CSV and finalizing report"
        add_log(f"[Step 3/3] Saving {len(results)} verified lead outputs to {out_filename}...")

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDNAMES)
            writer.writeheader()
            for r in results:
                row = {
                    field: r.get(field, "") if r.get(field) is not None else ""
                    for field in EXPORT_FIELDNAMES
                }
                writer.writerow(row)

        add_log(f"Run completed successfully! {total_verified} verified leads ({total_full} full leads).")

        with RUN_STATE_LOCK:
            run_state["status"] = "completed"
            run_state["current_step"] = "Complete"
            run_state["current_company"] = None
            if run_state["start_time"]:
                run_state["elapsed_seconds"] = round(time.time() - run_state["start_time"], 1)

    except Exception as exc:
        add_log(f"FATAL Pipeline Error: {exc}")
        with RUN_STATE_LOCK:
            run_state["status"] = "error"
            run_state["error"] = str(exc)
            run_state["current_step"] = "Error"


@router.get("/runs")
def list_runs() -> Dict[str, Any]:
    """List all available lead runs and historical datasets."""
    files = get_all_csv_files()
    runs_info = []

    for f in files:
        size_kb = round(f.stat().st_size / 1024, 1)
        mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        
        # Read quick summary of file
        leads = load_leads_from_file(f)
        total = len(leads)
        verified = sum(1 for r in leads if r["status"] == "VERIFIED")
        full_leads = sum(1 for r in leads if r["lead_tier"] == "FULL_LEAD")
        emails = sum(1 for r in leads if r.get("email"))

        runs_info.append({
            "id": f.name,
            "filename": f.name,
            "path": str(f),
            "modified_at": mtime,
            "size_kb": size_kb,
            "total_leads": total,
            "verified_leads": verified,
            "full_leads": full_leads,
            "emails_found": emails,
        })

    return {
        "runs": runs_info,
        "total_runs": len(runs_info),
        "latest_run": runs_info[0]["id"] if runs_info else None,
    }


@router.get("")
def get_leads(
    run_id: Optional[str] = Query(default="latest", description="'latest', 'all', or specific run filename"),
    status: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    has_email: Optional[bool] = Query(default=None),
    has_linkedin: Optional[bool] = Query(default=None),
    has_phone: Optional[bool] = Query(default=None),
    has_website: Optional[bool] = Query(default=None),
    min_confidence: Optional[float] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    if not isinstance(run_id, str):
        run_id = "latest"
    if not isinstance(status, str):
        status = None
    if not isinstance(tier, str):
        tier = None
    if not isinstance(query, str):
        query = None
    if not isinstance(state, str):
        state = None
    if not isinstance(has_email, bool):
        has_email = None
    if not isinstance(has_linkedin, bool):
        has_linkedin = None
    if not isinstance(has_phone, bool):
        has_phone = None
    if not isinstance(has_website, bool):
        has_website = None
    if not isinstance(min_confidence, (int, float)):
        min_confidence = None
    if not isinstance(limit, int):
        limit = 100
    if not isinstance(offset, int):
        offset = 0

    all_files = get_all_csv_files()

    if run_id == "all":
        raw_leads = load_all_leads_deduplicated()
        active_source = "All Combined Runs (De-duplicated)"
    elif run_id == "latest":

        if all_files:
            raw_leads = load_leads_from_file(all_files[0])
            active_source = all_files[0].name
        else:
            raw_leads = []
            active_source = "None"
    else:
        target_path = OUTPUTS_DIR / run_id
        if not target_path.exists():
            target_path = OUTPUTS_DIR / "benchmark" / run_id
        if target_path.exists():
            raw_leads = load_leads_from_file(target_path)
            active_source = target_path.name
        else:
            raw_leads = []
            active_source = "File not found"

    # Compute overall stats before filtering
    total_in_run = len(raw_leads)
    verified_in_run = sum(1 for r in raw_leads if r["status"] == "VERIFIED")
    full_in_run = sum(1 for r in raw_leads if r["lead_tier"] == "FULL_LEAD")
    website_only_in_run = sum(1 for r in raw_leads if r["lead_tier"] == "WEBSITE_ONLY")
    needs_review_in_run = sum(1 for r in raw_leads if r["status"] == "NEEDS_REVIEW")
    unresolved_in_run = sum(1 for r in raw_leads if r["status"] == "UNRESOLVED")
    emails_in_run = sum(1 for r in raw_leads if r.get("email"))
    phones_in_run = sum(1 for r in raw_leads if r.get("phone"))
    avg_conf = (
        round(sum(r.get("confidence", 0.0) for r in raw_leads) / total_in_run, 2)
        if total_in_run > 0
        else 0.0
    )

    # Apply search and filters
    filtered = raw_leads

    if query:
        q = query.casefold().strip()
        filtered = [
            r for r in filtered
            if q in r["company_name"].casefold()
            or q in r["website"].casefold()
            or q in r["email"].casefold()
            or q in r["phone"].casefold()
            or q in r["location"].casefold()
        ]

    if status and status.upper() != "ALL":
        filtered = [r for r in filtered if r["status"] == status.upper()]

    if tier and tier.upper() != "ALL":
        filtered = [r for r in filtered if r["lead_tier"] == tier.upper()]

    if state and state.upper() != "ALL":
        st = state.upper().strip()
        filtered = [r for r in filtered if st in r["location"].upper()]

    if has_email is True:
        filtered = [r for r in filtered if bool(r.get("email"))]
    elif has_email is False:
        filtered = [r for r in filtered if not bool(r.get("email"))]

    if has_linkedin is True:
        filtered = [r for r in filtered if r.get("company_linkedin_url") or r.get("decision_maker_linkedin_url")]
    elif has_linkedin is False:
        filtered = [r for r in filtered if not (r.get("company_linkedin_url") or r.get("decision_maker_linkedin_url"))]

    if has_phone is True:
        filtered = [r for r in filtered if bool(r.get("phone"))]
    elif has_phone is False:
        filtered = [r for r in filtered if not bool(r.get("phone"))]

    if has_website is True:
        filtered = [r for r in filtered if bool(r.get("website"))]
    elif has_website is False:
        filtered = [r for r in filtered if not bool(r.get("website"))]

    if min_confidence is not None:
        filtered = [r for r in filtered if r.get("confidence", 0.0) >= min_confidence]

    total_filtered = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "items": paginated,
        "total": total_filtered,
        "offset": offset,
        "limit": limit,
        "source": active_source,
        "summary": {
            "total_leads": total_in_run,
            "filtered_leads": total_filtered,
            "verified_count": verified_in_run,
            "full_lead_count": full_in_run,
            "website_only_count": website_only_in_run,
            "needs_review_count": needs_review_in_run,
            "unresolved_count": unresolved_in_run,
            "emails_count": emails_in_run,
            "phones_count": phones_in_run,
            "avg_confidence": avg_conf,
            "verification_rate": round((verified_in_run / total_in_run * 100), 1) if total_in_run else 0.0,
            "full_lead_rate": round((full_in_run / total_in_run * 100), 1) if total_in_run else 0.0,
        },
    }


@router.post("/run")
def trigger_run(payload: RunRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger an automated lead discovery or benchmark test run."""
    with RUN_STATE_LOCK:
        if run_state["status"] == "running":
            raise HTTPException(status_code=409, detail="A discovery pipeline run is already in progress.")

    if payload.mode != "test_batch" and not settings.SERPER_API_KEY.strip():
        raise HTTPException(status_code=503, detail="SERPER_API_KEY is required for Maps and LinkedIn enrichment. Configure backend/.env and restart the API.")
    if payload.mode != "test_batch" and not settings.APIFY_API_TOKEN.strip():
        raise HTTPException(status_code=503, detail="APIFY_API_TOKEN is required for company size and post checks. Configure backend/.env and restart the API.")
    if payload.mode in {"bookkeeping", "intent"} and not settings.HUNTER_API_KEY.strip():
        raise HTTPException(status_code=503, detail="HUNTER_API_KEY is required to find and verify decision-maker emails. Configure backend/.env and restart the API.")
    background_tasks.add_task(
        _run_pipeline_worker,
        payload.count,
        payload.state,
        payload.city,
        payload.mode,
        payload.niche,
        payload.region,
        payload.after_date,
    )

    return {
        "message": f"Pipeline run initiated for {payload.count} companies in region {payload.region.upper()}.",
        "mode": payload.mode,
        "count": payload.count,
        "state": payload.state,
        "city": payload.city,
        "niche": payload.niche,
        "region": payload.region,
        "after_date": payload.after_date,
    }


@router.get("/run/status")
def get_run_status() -> Dict[str, Any]:
    """Check the real-time status, step progression, and live logs of the running pipeline."""
    with RUN_STATE_LOCK:
        state_copy = dict(run_state)
        # Calculate live elapsed seconds if running
        if state_copy["status"] == "running" and state_copy["start_time"]:
            state_copy["elapsed_seconds"] = round(time.time() - state_copy["start_time"], 1)
        return state_copy


@router.post("/run/cancel")
def cancel_run() -> Dict[str, Any]:
    """Signal the active pipeline run to terminate safely."""
    global RUN_CANCEL_FLAG
    RUN_CANCEL_FLAG = True
    add_log("Cancel request received. Stopping after current company...")
    return {"message": "Cancellation flag set."}


@router.get("/export/excel")
def export_leads_excel(
    run_id: Optional[str] = Query(default="latest"),
    status: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
) -> StreamingResponse:
    if not isinstance(run_id, str):
        run_id = "latest"
    if not isinstance(status, str):
        status = None
    if not isinstance(tier, str):
        tier = None
    if not isinstance(query, str):
        query = None

    response_data = get_leads(
        run_id=run_id,
        status=status,
        tier=tier,
        query=query,
        limit=10000,
        offset=0,
    )
    leads = response_data["items"]
    summary = response_data["summary"]

    wb = openpyxl.Workbook()
    # Sheet 1: Leads
    ws = wb.active
    ws.title = "Company Leads"

    # Styling definitions
    brand_header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")  # Slate 900
    sub_header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")    # Slate 800
    white_bold = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    white_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    regular_font = Font(name="Segoe UI", size=10)
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    link_font = Font(name="Segoe UI", size=10, color="2563EB", underline="single")

    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    # Status fills
    fill_full_lead = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")     # Emerald 100
    font_full_lead = Font(name="Segoe UI", size=10, bold=True, color="166534")
    fill_web_only = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")      # Sky 100
    font_web_only = Font(name="Segoe UI", size=10, bold=True, color="075985")
    fill_review = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")        # Amber 100
    font_review = Font(name="Segoe UI", size=10, bold=True, color="92400E")
    fill_unresolved = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")    # Slate 100
    font_unresolved = Font(name="Segoe UI", size=10, color="64748B")

    # Title Banner
    ws.merge_cells("A1:M1")
    title_cell = ws["A1"]
    title_cell.value = "PROKIZEN GLOBAL LLP — COMPANY LEAD FINDER REPORT"
    title_cell.font = white_title
    title_cell.fill = brand_header_fill
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Subtitle with Summary Stats
    ws.merge_cells("A2:M2")
    sub_cell = ws["A2"]
    sub_cell.value = (
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Total Leads: {summary['total_leads']} | "
        f"Verified Leads: {summary['verified_count']} ({summary['verification_rate']}%) | "
        f"Full Leads (Web + Contact): {summary['full_lead_count']} ({summary['full_lead_rate']}%) | "
        f"Emails Found: {summary['emails_count']} | Phones Found: {summary['phones_count']}"
    )
    sub_cell.font = Font(name="Segoe UI", size=9, italic=True, color="94A3B8")
    sub_cell.fill = sub_header_fill
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24

    # Headers
    headers = [
        ("Company Name", 32),
        ("Region", 12),
        ("Location", 18),
        ("Employees (10-15)", 18),
        ("Lead Tier", 16),
        ("Status", 14),
        ("Intent Source", 16),
        ("Official Website", 32),
        ("Company Email (Min Req)", 28),
        ("Decision Maker", 24),
        ("Decision Maker Email", 28),
        ("Verified Phone", 20),
        ("Confidence", 14),
        ("Status Reason", 44),
    ]

    header_row_idx = 4
    ws.row_dimensions[header_row_idx].height = 28

    for col_idx, (header_text, width) in enumerate(headers, start=1):
        cell = ws.cell(row=header_row_idx, column=col_idx, value=header_text)
        cell.font = white_bold
        cell.fill = sub_header_fill
        cell.alignment = Alignment(horizontal="center" if "Confidence" in header_text or "Tier" in header_text or "Employees" in header_text or "Region" in header_text else "left", vertical="center")
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # Data Rows
    for row_idx, lead in enumerate(leads, start=5):
        ws.row_dimensions[row_idx].height = 22
        tier = lead.get("lead_tier", "UNRESOLVED")
        status_val = lead.get("status", "UNRESOLVED")
        website = lead.get("website", "")
        comp_email = lead.get("company_email", "")
        dm_email = lead.get("decision_maker_email", "")
        phone = lead.get("phone", "")
        dm_name = lead.get("decision_maker_name") or lead.get("owner_name") or ""
        emp_count = lead.get("employee_count") or ""
        intent_src = lead.get("intent_source") or ""
        reg = lead.get("region") or "US"

        c1 = ws.cell(row=row_idx, column=1, value=lead.get("company_name"))
        c1.font = bold_font
        c1.border = thin_border

        c2 = ws.cell(row=row_idx, column=2, value=reg)
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c2.font = regular_font
        c2.border = thin_border

        c3 = ws.cell(row=row_idx, column=3, value=lead.get("location"))
        c3.font = regular_font
        c3.border = thin_border

        c4 = ws.cell(row=row_idx, column=4, value=emp_count)
        c4.alignment = Alignment(horizontal="center", vertical="center")
        c4.font = regular_font
        c4.border = thin_border

        c5 = ws.cell(row=row_idx, column=5, value=tier)
        c5.alignment = Alignment(horizontal="center", vertical="center")
        c5.border = thin_border
        if tier == "FULL_LEAD":
            c5.fill = fill_full_lead
            c5.font = font_full_lead
        elif tier in ("WEBSITE_ONLY", "COMPANY_EMAIL_ONLY"):
            c5.fill = fill_web_only
            c5.font = font_web_only
        elif status_val == "NEEDS_REVIEW":
            c5.fill = fill_review
            c5.font = font_review
        else:
            c5.fill = fill_unresolved
            c5.font = font_unresolved

        c6 = ws.cell(row=row_idx, column=6, value=status_val)
        c6.font = regular_font
        c6.border = thin_border

        c7 = ws.cell(row=row_idx, column=7, value=intent_src)
        c7.font = regular_font
        c7.border = thin_border

        c8 = ws.cell(row=row_idx, column=8, value=website)
        c8.border = thin_border
        if website:
            c8.font = link_font
            if website.startswith("http"):
                c8.hyperlink = website
        else:
            c8.font = regular_font

        c9 = ws.cell(row=row_idx, column=9, value=comp_email)
        c9.font = regular_font
        c9.border = thin_border

        c10 = ws.cell(row=row_idx, column=10, value=dm_name)
        c10.font = regular_font
        c10.border = thin_border

        c11 = ws.cell(row=row_idx, column=11, value=dm_email)
        c11.font = regular_font
        c11.border = thin_border

        c12 = ws.cell(row=row_idx, column=12, value=phone)
        c12.font = regular_font
        c12.border = thin_border

        conf = lead.get("confidence", 0.0)
        c13 = ws.cell(row=row_idx, column=13, value=f"{conf:.2f}")
        c13.alignment = Alignment(horizontal="center", vertical="center")
        c13.font = regular_font
        c13.border = thin_border

        c14 = ws.cell(row=row_idx, column=14, value=lead.get("status_reason", ""))
        c14.font = regular_font
        c14.border = thin_border

    # Freeze panes below headers
    ws.freeze_panes = "A5"

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"Prokizen_Leads_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/csv")
def export_leads_csv(
    run_id: Optional[str] = Query(default="latest"),
    status: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
) -> Response:
    if not isinstance(run_id, str):
        run_id = "latest"
    if not isinstance(status, str):
        status = None
    if not isinstance(tier, str):
        tier = None
    if not isinstance(query, str):
        query = None

    response_data = get_leads(
        run_id=run_id,
        status=status,
        tier=tier,
        query=query,
        limit=10000,
        offset=0,
    )
    leads = response_data["items"]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDNAMES)
    writer.writeheader()
    for lead in leads:
        import json
        cands = lead.get("candidate_results")
        if isinstance(cands, (list, dict)):
            cand_str = json.dumps(cands, ensure_ascii=True).replace("\r", " ").replace("\n", " ")
        else:
            cand_str = str(cands or "").replace("\r", " ").replace("\n", " ")

        row = {
            "company_name": str(lead.get("company_name", "") or ""),
            "location": str(lead.get("location", "") or ""),
            "status": str(lead.get("status", "UNRESOLVED") or "UNRESOLVED"),
            "lead_tier": str(lead.get("lead_tier", "UNRESOLVED") or "UNRESOLVED"),
            "status_reason": str(lead.get("status_reason", "") or ""),
            "website": str(lead.get("website", "") or ""),
            "website_status": str(lead.get("website_status", "UNRESOLVED") or "UNRESOLVED"),
            "website_source": str(lead.get("website_source", "") or ""),
            "email": str(lead.get("email", "") or ""),
            "email_status": str(lead.get("email_status", "UNRESOLVED") or "UNRESOLVED"),
            "email_source": str(lead.get("email_source", "") or ""),
            "decision_maker_name": str(lead.get("decision_maker_name", "") or ""),
            "decision_maker_title": str(lead.get("decision_maker_title", "") or ""),
            "decision_maker_linkedin_url": str(lead.get("decision_maker_linkedin_url", "") or ""),
            "has_recent_linkedin_post": str(bool(lead.get("has_recent_linkedin_post", False))),
            "email_confidence": str(lead.get("email_confidence", "") or ""),
            "phone": str(lead.get("phone", "") or ""),
            "phone_status": str(lead.get("phone_status", "UNRESOLVED") or "UNRESOLVED"),
            "phone_source": str(lead.get("phone_source", "") or ""),
            "confidence": round(float(lead.get("confidence", 0.0) or 0.0), 2),
            "source": str(lead.get("source", "") or ""),
            "candidate_results": cand_str,
            "elapsed_seconds": round(float(lead.get("elapsed_seconds", 0.0) or 0.0), 2),
            "created_at": str(lead.get("created_at", "") or ""),
        }
        writer.writerow(row)

    filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
