"""
CLI Runner for the Multi-Tool Intent-Driven Lead Generation Pipeline.
Example usages:
    python run_intent_pipeline.py --query "plumbing firms in Austin, TX" --count 10
    python run_intent_pipeline.py --query "digital marketing agencies in Miami, FL"
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
    parser.add_argument(
        "--query",
        type=str,
        default="plumbing firms in Austin, TX",
        help="Search query for Serper Google Maps discovery (e.g. 'plumbing firms in Austin, TX').",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of local businesses to discover and evaluate.",
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
    pipeline.run(query=args.query, target_count=args.count, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
