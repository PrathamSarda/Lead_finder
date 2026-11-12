"""
AI Intent and Buying Signal Analysis.
Evaluates company recent LinkedIn post strings to detect financial hiring roles
(bookkeeper, accountant, CPA), expanding operations, or tax/scaling pain points.
Supports:
1. Google Gemini API (gemini-3.8-flash)
2. Offline date and intent rules when Gemini is unavailable or fails
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass(slots=True)
class IntentAnalysisResult:
    intent_found: bool
    reason: str
    model_used: str


SYSTEM_PROMPT = (
    "Evaluate recent public company LinkedIn posts for actionable buying intent relevant to the target niche. "
    "Only treat posts published within the last 90 days as current. Look for explicit financial hiring, "
    "bookkeeping/accounting/tax/payroll needs, operational expansion, or scaling signals. Do not infer intent "
    "from generic promotional content. Respond only with JSON fields intent_found (boolean) and reason (short string)."
)


class IntentAnalyzer:
    """Analyzes recent LinkedIn activity to verify bookkeeping and financial scaling intent."""

    def __init__(self, gemini_api_key: str | None = None):
        self.gemini_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def analyze(self, company_name: str, posts: list[str], target_niche: str | None = None) -> IntentAnalysisResult:
        if not posts:
            return IntentAnalysisResult(
                intent_found=False,
                reason="No recent public posts available on LinkedIn profile to evaluate intent.",
                model_used="none",
            )

        combined_posts = f"Target niche: {target_niche or 'bookkeeping, accounting, tax, payroll, and scaling support'}\n\n" + "\n---\n".join(f"Post {i+1}: {p}" for i, p in enumerate(posts))

        # Gemini is the primary analyzer; any request/parse failure falls through to deterministic rules.
        if self.gemini_key:
            res = self._call_gemini(combined_posts)
            if res:
                return res
        return self._rule_based_analysis(company_name, posts)

    def _call_gemini(self, text: str) -> IntentAnalysisResult | None:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            prompt = f"{SYSTEM_PROMPT}\n\nCompany Posts:\n{text}\n\nRespond ONLY with JSON."
            
            response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
            if not response or not response.text:
                return None

            raw_text = response.text.strip()
            # Extract json if wrapped in ```json
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)
            parsed = json.loads(raw_text)
            intent_value = parsed.get("intent_found", False)
            return IntentAnalysisResult(
                intent_found=intent_value is True or str(intent_value).strip().lower() == "true",
                reason=str(parsed.get("reason", "Analyzed by Gemini.")),
                model_used="gemini-3.8-flash",
            )
        except Exception as exc:
            print(f"[Gemini Intent] Error: {exc}. Using rule-based fallback.")
            return None

    def _rule_based_analysis(self, company_name: str, posts: list[str]) -> IntentAnalysisResult:
        full_text = " ".join(posts).lower()
        post_ages_days: list[int] = []
        for post in posts:
            match = re.search(r"\[Posted:\s*([^\]]+)\]", post, re.I)
            posted = match.group(1).strip().lower() if match else post.lower()
            if match:
                try:
                    parsed = datetime.fromisoformat(posted.replace("z", "+00:00"))
                    parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
                    post_ages_days.append(max(0, (datetime.now(timezone.utc) - parsed).days))
                    continue
                except ValueError:
                    pass
            relative = re.search(r"(\d+)\s*(hour|day|week|month|year)s?\s+ago", posted)
            if relative:
                amount = int(relative.group(1))
                unit = relative.group(2)
                days = amount if unit == "day" else amount * 7 if unit == "week" else amount * 30 if unit == "month" else amount * 365 if unit == "year" else 0
                post_ages_days.append(days)
            elif re.search(r"\b(today|yesterday|\d+\s*(?:h|d|w))\b", posted):
                relative_short = re.search(r"(\d+)\s*(h|d|w)\b", posted)
                post_ages_days.append(int(relative_short.group(1)) * (7 if relative_short.group(2) == "w" else 1) if relative_short else 0)
        if post_ages_days and min(post_ages_days) > 90:
            return IntentAnalysisResult(
                intent_found=False,
                reason=f"Latest public post is approximately {min(post_ages_days)} days old; intent is not current.",
                model_used="rule_based_heuristic",
            )
        if not post_ages_days:
            return IntentAnalysisResult(False, "Post dates were unavailable, so recent intent could not be confirmed.", "rule_based_heuristic")

        intent_keywords = [
            "bookkeeper", "accountant", "cpa", "quickbooks", "payroll",
            "tax prep", "financial records", "tax season", "growing fast",
            "expanding operations", "scaling", "hiring finance", "accounting",
        ]
        matches = [kw for kw in intent_keywords if kw in full_text]
        if matches:
            return IntentAnalysisResult(
                intent_found=True,
                reason=f"Detected financial hiring/scaling triggers in recent posts: {', '.join(matches)}.",
                model_used="rule_based_heuristic",
            )
        return IntentAnalysisResult(
            intent_found=False,
            reason="Recent posts did not contain hiring, accounting, or scaling keywords.",
            model_used="rule_based_heuristic",
        )
