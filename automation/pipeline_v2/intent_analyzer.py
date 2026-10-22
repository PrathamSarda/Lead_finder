"""
AI Intent and Buying Signal Analysis.
Evaluates company recent LinkedIn post strings to detect financial hiring roles
(bookkeeper, accountant, CPA), expanding operations, or tax/scaling pain points.
Supports:
1. OpenAI API (gpt-4o-mini)
2. Google Gemini API (gemini-2.5-flash) as secondary/configured fallback
3. Offline rule-based intent analyzer if neither API key is active
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass(slots=True)
class IntentAnalysisResult:
    intent_found: bool
    reason: str
    model_used: str


SYSTEM_PROMPT = (
    "Analyze the following recent company LinkedIn posts with their posting dates/timestamps. "
    "First, verify if the posts are recent (posted within the last 90 days / 3 month). "
    "If the latest posts are older than 1 month or years old, intent_found must be false with reason 'Posts are outdated (>1 month old)'. "
    "Second, if recent, determine if there is any active indication that this business is hiring financial roles "
    "(bookkeeper, accountant, CPA), expanding operations, or experiencing tax/scaling pain points. "
    "Respond with a JSON object containing exactly two fields: 'intent_found' (boolean) and 'reason' (string short explanation)."
)


class IntentAnalyzer:
    """Analyzes recent LinkedIn activity to verify bookkeeping and financial scaling intent."""

    def __init__(self, openai_api_key: str | None = None, gemini_api_key: str | None = None):
        self.openai_key = (openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self.gemini_key = (gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()

    def analyze(self, company_name: str, posts: list[str]) -> IntentAnalysisResult:
        if not posts:
            return IntentAnalysisResult(
                intent_found=False,
                reason="No recent public posts available on LinkedIn profile to evaluate intent.",
                model_used="none",
            )

        combined_posts = "\n---\n".join(f"Post {i+1}: {p}" for i, p in enumerate(posts))

        # 1. Prioritize Gemini if GEMINI_API_KEY is configured
        if self.gemini_key:
            res = self._call_gemini(combined_posts)
            if res:
                return res

        # 2. Try OpenAI (gpt-4o-mini) as secondary
        if self.openai_key:
            res = self._call_openai(combined_posts)
            if res:
                return res

        # 3. Rule-based offline intent evaluation
        return self._rule_based_analysis(company_name, posts)

    def _call_openai(self, text: str) -> IntentAnalysisResult | None:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Company Posts:\n{text}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw = response.choices[0].message.content or "{}"
            parsed = json.loads(raw)
            return IntentAnalysisResult(
                intent_found=bool(parsed.get("intent_found", False)),
                reason=str(parsed.get("reason", "Analyzed by gpt-4o-mini.")),
                model_used="gpt-4o-mini",
            )
        except Exception as exc:
            print(f"[OpenAI Intent] Error: {exc}. Trying fallback.")
            return None

    def _call_gemini(self, text: str) -> IntentAnalysisResult | None:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            prompt = f"{SYSTEM_PROMPT}\n\nCompany Posts:\n{text}\n\nRespond ONLY with JSON."
            
            # Try available model endpoints in order of preference
            model_names = [
                "gemini-3.8-flash",
                "gemini-3.5-flash",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
            ]
            response = None
            last_err = None
            for m in model_names:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=prompt,
                    )
                    if response and response.text:
                        break
                except Exception as e:
                    last_err = e
                    continue

            if not response or not response.text:
                if last_err:
                    print(f"[Gemini Intent] Notice: {last_err}. Trying secondary/fallback.")
                return None

            raw_text = response.text.strip()
            # Extract json if wrapped in ```json
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)
            parsed = json.loads(raw_text)
            return IntentAnalysisResult(
                intent_found=bool(parsed.get("intent_found", False)),
                reason=str(parsed.get("reason", "Analyzed by Gemini.")),
                model_used="gemini",
            )
        except Exception as exc:
            print(f"[Gemini Intent] Error: {exc}. Using rule-based fallback.")
            return None

    def _rule_based_analysis(self, company_name: str, posts: list[str]) -> IntentAnalysisResult:
        full_text = " ".join(posts).lower()

        # Reject if posts explicitly indicate outdated activity (> 1 month or years old)
        outdated_markers = ["1 year ago", "2 years ago", "3 years ago", "years ago", "2y", "3y", "5y", "months ago"]
        if any(marker in full_text for marker in outdated_markers) and not any(r in full_text for r in ("1d", "2d", "3d", "1w", "2w", "3w", "days ago", "hours ago")):
            return IntentAnalysisResult(
                intent_found=False,
                reason="Latest posts are outdated (> 1 month old). Intent not actionable.",
                model_used="rule_based_heuristic",
            )

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
