from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


from automation.intelligence.models import (
    CollectedResult,
    CompanyInput,
)
from automation.resolvers.zenserp_resolver import LEGAL_SUFFIXES


class ResultFilter:
    """
    Filters and ranks search results before they are passed to extractors.

    The filter considers:

    1. Company-name similarity
    2. Source reliability
    3. Company-name token overlap
    4. Negative or irrelevant terms
    5. Duplicate URLs
    """

    DEFAULT_MINIMUM_SCORE = 0.55

    LEGAL_SUFFIXES = {
    "inc",
    "inc.",
    "llc",
    "l.l.c",
    "ltd",
    "ltd.",
    "corp",
    "corp.",
    "corporation",
    "company",
    "co",
    "co.",
    "limited",
    "plc",
}

    SOURCE_SCORES: dict[str, float] = {
        "linkedin": 1.00,
        "fmcsa": 0.95,
        "website": 0.95,
        "official_website": 0.95,
        "clutch": 0.85,
        "glassdoor": 0.80,
        "indeed": 0.70,
        "contact": 0.65,
        "email": 0.65,
        "phone": 0.65,
        "generic": 0.60,
        "google": 0.60,
    }

    COMPANY_SUFFIXES: set[str] = {
        "inc",
        "incorporated",
        "llc",
        "ltd",
        "limited",
        "corp",
        "corporation",
        "company",
        "co",
        "plc",
        "lp",
        "llp",
        "group",
        "holdings",
    }

    NEGATIVE_TERMS: set[str] = {
        "job",
        "jobs",
        "career",
        "careers",
        "salary",
        "salaries",
        "hiring",
        "vacancy",
        "vacancies",
        "apply",
        "application",
        "interview",
        "resume",
        "reddit",
        "youtube",
        "facebook",
        "instagram",
        "pinterest",
        "wikipedia",
        "news",
        "obituary",
        "obituaries",
        "lawsuit",
        "court",
        "arrest",
        "mugshot",
        "pdf",
        "download",
    }

    TRACKING_PARAMETERS: set[str] = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
        "ref",
        "source",
    }

    def __init__(
        self,
        minimum_score: float = DEFAULT_MINIMUM_SCORE,
    ) -> None:
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "minimum_score must be between 0.0 and 1.0."
            )

        self.minimum_score = minimum_score

    
    def filter(
        self,
        company: CompanyInput,
        results: list[CollectedResult],
    ) -> list[CollectedResult]:
        """
        Filter, deduplicate, and rank collected search results.

        Args:
            company:
                Company for which evidence is being collected.

            results:
                Raw results returned by EvidenceCollector.

        Returns:
            A new list containing relevant and deduplicated results,
            ordered from highest to lowest relevance.
        """

        company_name = self._get_company_name(company)

        if not results:
            return []
        scored_results: list[
    tuple[float, float, int, CollectedResult]
] = []

        for index, collected_result in enumerate(results):
            score = self.score(company, collected_result)
            name_similarity = self._company_similarity(
            company_name,
            self._get_result_value(
                collected_result,
                "title",
            ),
        )   
            if name_similarity < 0.70:
                continue

            if score < self.minimum_score:
                continue

            source = self._get_source(collected_result)
            source_score = self._source_score(source)

            scored_results.append(
                (
                    score,
                    source_score,
                    index,
                    collected_result,
                )
            )

        # Ranking priority:
        # 1. Overall relevance score
        # 2. Source reliability
        # 3. Original order as a stable final tie-breaker
        scored_results.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2],
            )
        )

        ranked_results = [
            collected_result
            for _, _, _, collected_result in scored_results
        ]

        return self._deduplicate(
            company_name=company_name,
            results=ranked_results,
        )

    def score(
        self,
        company: CompanyInput,
        collected_result: CollectedResult,
    ) -> float:
        """
        Calculate the relevance score for one collected result.

        Score range:
            0.0 = irrelevant
            1.0 = highly relevant
        """

        company_name = self._get_company_name(company)

        title = self._get_result_value(
            collected_result,
            "title",
        )
        snippet = self._get_result_value(
            collected_result,
            "snippet",
        )
        url = self._get_result_value(
            collected_result,
            "url",
        )
        source = self._get_source(collected_result)

        combined_text = " ".join(
            value
            for value in (title, snippet, url)
            if value
        )

        if not combined_text.strip():
            return 0.0

        title_similarity = self._company_similarity(
            company_name,
            title,
        )

        text_similarity = self._company_similarity(
            company_name,
            combined_text,
        )

        token_overlap = self._company_token_overlap(
            company_name,
            combined_text,
        )

        source_score = self._source_score(source)

        exact_name_bonus = self._exact_company_name_bonus(
            company_name,
            combined_text,
        )

        negative_penalty = self._negative_term_penalty(
            source=source,
            title=title,
            snippet=snippet,
            url=url,
        )

        score = (
            title_similarity * 0.38
            + text_similarity * 0.17
            + token_overlap * 0.25
            + source_score * 0.20
            + exact_name_bonus
            - negative_penalty
        )

        return round(
            max(0.0, min(score, 1.0)),
            4,
        )

    def _deduplicate(
        self,
        company_name: str,
        results: list[CollectedResult],
    ) -> list[CollectedResult]:
        """
        Remove duplicate result URLs.

        Results are already ordered by relevance, so the first result for
        each canonical URL is retained.
        """

        unique_results: list[CollectedResult] = []
        seen_keys: set[str] = set()

        for collected_result in results:
            url = self._get_result_value(
                collected_result,
                "url",
            )

            title = self._get_result_value(
                collected_result,
                "title",
            )

            canonical_url = self._canonical_url(url)

            if canonical_url:
                deduplication_key = canonical_url
            else:
                # Fall back to a normalized title if no URL is available.
                deduplication_key = (
                    "title:"
                    + self._normalize_text(title)
                    + ":"
                    + self._normalize_text(company_name)
                )

            if deduplication_key in seen_keys:
                continue

            seen_keys.add(deduplication_key)
            unique_results.append(collected_result)

        return unique_results

    def _company_similarity(
        self,
        company_name: str,
        candidate_text: str,
    ) -> float:
        """
        Measure similarity between a company name and candidate text.

        Legal suffixes such as INC, LLC, and CORPORATION are removed before
        comparison.
        """

        normalized_company = self._normalize_company_name(
            company_name
        )
        normalized_candidate = self._normalize_company_name(
            candidate_text
        )

        if not normalized_company or not normalized_candidate:
            return 0.0

        if normalized_company == normalized_candidate:
            return 1.0

        if normalized_company in normalized_candidate:
            return 1.0

        company_tokens = normalized_company.split()
        candidate_tokens = normalized_candidate.split()

        # Search for a similarly sized text window inside the candidate.
        best_window_similarity = 0.0

        if company_tokens and candidate_tokens:
            minimum_window_size = max(
                1,
                len(company_tokens) - 1,
            )
            maximum_window_size = min(
                len(candidate_tokens),
                len(company_tokens) + 1,
            )

            for window_size in range(
                minimum_window_size,
                maximum_window_size + 1,
            ):
                for start in range(
                    0,
                    len(candidate_tokens) - window_size + 1,
                ):
                    window = " ".join(
                        candidate_tokens[
                            start : start + window_size
                        ]
                    )

                    similarity = SequenceMatcher(
                        None,
                        normalized_company,
                        window,
                    ).ratio()

                    best_window_similarity = max(
                        best_window_similarity,
                        similarity,
                    )

        full_similarity = SequenceMatcher(
            None,
            normalized_company,
            normalized_candidate,
        ).ratio()

        token_overlap = self._company_token_overlap(
        company_name,
        candidate_text,
)

        return max(
            full_similarity,
            best_window_similarity,
            token_overlap,
        )

    def _company_token_overlap(
        self,
        company_name: str,
        candidate_text: str,
    ) -> float:
        """
        Return the proportion of meaningful company-name tokens found in
        the candidate text.
        """

        company_tokens = set(
            self._normalize_company_name(company_name).split()
        )
        candidate_tokens = set(
            self._normalize_company_name(candidate_text).split()
        )

        if not company_tokens:
            return 0.0

        matched_tokens = company_tokens.intersection(
            candidate_tokens
        )

        return len(matched_tokens) / len(company_tokens)

    def _exact_company_name_bonus(
        self,
        company_name: str,
        candidate_text: str,
    ) -> float:
        normalized_company = self._normalize_company_name(
            company_name
        )
        normalized_candidate = self._normalize_company_name(
            candidate_text
        )

        if (
            normalized_company
            and normalized_company in normalized_candidate
        ):
            return 0.10

        return 0.0

    def _negative_term_penalty(
        self,
        source: str,
        title: str,
        snippet: str,
        url: str,
    ) -> float:
        """
        Apply a penalty when a result appears to be a job posting or
        irrelevant content page.

        Job-oriented sources such as Indeed and Glassdoor receive a smaller
        penalty because company profile pages can legitimately exist there.
        """

        text = self._normalize_text(
            " ".join((title, snippet, url))
        )

        matched_terms = {
            term
            for term in self.NEGATIVE_TERMS
            if re.search(
                rf"\b{re.escape(term)}\b",
                text,
            )
        }

        if not matched_terms:
            return 0.0

        source = source.lower().strip()

        job_terms = {
            "job",
            "jobs",
            "career",
            "careers",
            "salary",
            "salaries",
            "hiring",
            "vacancy",
            "vacancies",
            "apply",
        }

        matched_job_terms = matched_terms.intersection(job_terms)
        matched_other_terms = matched_terms.difference(job_terms)

        penalty = 0.0

        if matched_job_terms:
            if source in {"indeed", "glassdoor"}:
                penalty += 0.22
            else:
                penalty += 0.32

        if matched_other_terms:
            penalty += min(
                0.30,
                len(matched_other_terms) * 0.12,
            )

        return min(penalty, 0.55)

    def _source_score(
        self,
        source: str,
    ) -> float:
        normalized_source = self._normalize_text(source)

        return self.SOURCE_SCORES.get(
            normalized_source,
            self.SOURCE_SCORES["generic"],
        )

    def _canonical_url(
        self,
        url: str,
    ) -> str:
        """
        Create a canonical URL for deduplication.

        Important behavior:

        - Removes URL fragments
        - Removes common tracking parameters
        - Removes trailing slashes
        - Normalizes localized LinkedIn domains
        - Removes www.
        - Normalizes HTTP and HTTPS duplicates
        """

        if not url:
            return ""

        raw_url = url.strip()

        if not raw_url:
            return ""

        if not raw_url.startswith(("http://", "https://")):
            raw_url = f"https://{raw_url}"

        try:
            parsed = urlparse(raw_url)
        except ValueError:
            return raw_url.lower().rstrip("/")

        hostname = (
            parsed.hostname or ""
        ).lower().strip(".")

        if hostname.startswith("www."):
            hostname = hostname[4:]

        # LinkedIn often returns localized subdomains:
        #
        # ch.linkedin.com
        # nl.linkedin.com
        # tr.linkedin.com
        # ec.linkedin.com
        #
        # They all represent the same LinkedIn page.
        if (
            hostname == "linkedin.com"
            or hostname.endswith(".linkedin.com")
        ):
            hostname = "linkedin.com"

        path = re.sub(
            r"/+",
            "/",
            parsed.path or "/",
        )

        if path != "/":
            path = path.rstrip("/")

        filtered_query_parameters = [
            (key, value)
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=False,
            )
            if key.lower() not in self.TRACKING_PARAMETERS
        ]

        filtered_query_parameters.sort()

        canonical_query = urlencode(
            filtered_query_parameters,
            doseq=True,
        )

        # The scheme is intentionally normalized to HTTPS so that HTTP and
        # HTTPS versions are treated as duplicates.
        canonical = urlunparse(
            (
                "https",
                hostname,
                path,
                "",
                canonical_query,
                "",
            )
        )

        return canonical.lower()

    def _normalize_company_name(
        self,
        value: str,
    ) -> str:
        normalized = self._normalize_text(value)

        tokens = [
            token
            for token in normalized.split()
            if token not in self.COMPANY_SUFFIXES
        ]

        return " ".join(tokens)

    @staticmethod
    def _normalize_text(
        value: str | None,
    ) -> str:
        if not value:
            return ""

        normalized = value.casefold()

        normalized = normalized.replace("&", " and ")

        normalized = re.sub(
            r"https?://",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"www\.",
            " ",
            normalized,
        )

        normalized = re.sub(
            r"[^a-z0-9]+",
            " ",
            normalized,
        )

        return re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

    @staticmethod
    def _get_company_name(
        company: CompanyInput,
    ) -> str:
        name = getattr(company, "name", None)

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "CompanyInput must contain a non-empty 'name'."
            )

        return name.strip()

    @staticmethod
    def _get_source(
        collected_result: CollectedResult,
    ) -> str:
        query = getattr(
            collected_result,
            "query",
            None,
        )

        source = getattr(
            query,
            "source",
            "",
        )

        return str(source or "").strip().lower()

    @staticmethod
    def _get_result_value(
        collected_result: CollectedResult,
        field_name: str,
    ) -> str:
        result = getattr(
            collected_result,
            "result",
            None,
        )

        value = getattr(
            result,
            field_name,
            "",
        )

        return str(value or "").strip()

    