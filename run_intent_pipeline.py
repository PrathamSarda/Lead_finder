"""
CLI Runner for the Multi-Tool Intent-Driven Lead Generation Pipeline.
Example usage:
    python run_intent_pipeline.py --niche "bookkeeping, payroll, or scaling needs" --city Austin --state TX --count 10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv()

from automation.pipeline_v2.pipeline_orchestrator import MultiToolLeadPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Multi-Tool Lead Generation Pipeline for B2B Bookkeeping Intent Leads."
    )
    parser.add_argument("--niche", "--query", dest="niche", type=str, default="bookkeeping, accounting, tax preparation, payroll, or scaling support", help="Buying intent to evaluate from recent company LinkedIn posts.")
    parser.add_argument("--city", type=str, default=None, help="Optional FMCSA company city filter.")
    parser.add_argument("--state", type=str, default=None, help="Optional two-letter US state filter.")
    parser.add_argument("--region", type=str, default="US", help="Target country/region code: US, UK, AU, CA.")
    parser.add_argument("--after-date", dest="after_date", type=str, default=None, help="Filter for bookkeeping need posted on or after this date (YYYY-MM-DD).")
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of qualified SMB leads (10-15 headcount, verified bookkeeping intent, company email) to find.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Output directory for generated CSV reports.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline = MultiToolLeadPipeline()
    pipeline.run(
        query=args.niche,
        target_count=args.count,
        output_dir=args.output_dir,
        city=args.city,
        state=args.state,
        region=args.region,
        after_date=args.after_date,
        candidate_source="jobs",
    )


if __name__ == "__main__":
    main()
