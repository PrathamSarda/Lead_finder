import re

from automation.intelligence.models import CompanyInput, SearchQuery

LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "llc",
    "l.l.c",
    "ltd",
    "limited",
    "corp",
    "corporation",
    "company",
    "co",
    "pllc",
    "lp",
    "llp",
}


def clean_company_name(name: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", name.lower())
    meaningful = [t for t in tokens if t not in LEGAL_SUFFIXES]
    if meaningful:
        return " ".join(meaningful).title()
    return name.strip()


class QueryBuilder:

    def build_stage(
        self,
        company: CompanyInput,
        stage: int,
    ) -> list[SearchQuery]:
        cleaned = clean_company_name(company.name)
        location_parts = [p for p in (company.city, company.state) if p and p.strip()]
        location_str = " ".join(location_parts).strip()

        # Build stages:
        # Stage 0: Official website search (with location context if available)
        # Stage 1: LinkedIn company search
        # Stage 2: Direct contact / email search
        # Stage 3: Broad company search
        stages = [
            # Stage 0: Website search
            [
                (
                    "website",
                    f"{cleaned} {location_str} official website".strip() if location_str else f"{cleaned} official website",
                    1,
                ),
            ],
            # Stage 1: LinkedIn
            [
                (
                    "linkedin",
                    f'site:linkedin.com/company "{cleaned}"',
                    1,
                ),
            ],
            # Stage 2: Contact / email
            [
                (
                    "email",
                    f"{cleaned} {location_str} contact email".strip() if location_str else f"{cleaned} contact email",
                    2,
                ),
            ],
            # Stage 3: Broader search
            [
                (
                    "website",
                    f'"{cleaned}" website',
                    3,
                ),
            ],
        ]

        if stage >= len(stages):
            return []

        queries = []
        for source, query_str, priority in stages[stage]:
            queries.append(
                SearchQuery(
                    source=source,
                    query=query_str,
                    priority=priority,
                )
            )
        return queries

    def build(
        self,
        company: CompanyInput,
    ) -> list[SearchQuery]:
        """Return all queries across all stages."""
        all_queries: list[SearchQuery] = []
        for stage in range(self.stage_count()):
            all_queries.extend(self.build_stage(company, stage))
        return all_queries

    def stage_count(self) -> int:
        return 4