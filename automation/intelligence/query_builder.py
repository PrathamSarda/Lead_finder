from automation.intelligence.models import CompanyInput, SearchQuery


class QueryBuilder:

    SEARCH_STAGES = [

    [
        ("linkedin", 'site:linkedin.com/company "{name}"', 1),
    ],

    [
        ("indeed", 'site:indeed.com "{name}"', 2),
    ],

    [
        ("website", '"{name}" official website', 1),
    ],

    [
        ("email", '"{name}" email', 3),
    ],
]

    def build_stage(
    self,
    company: CompanyInput,
    stage: int,
) -> list[SearchQuery]:

        queries = []

        if stage >= len(self.SEARCH_STAGES):
            return queries

        for source, template, priority in self.SEARCH_STAGES[stage]:

            queries.append(
                SearchQuery(
                    source=source,
                    query=template.format(name=company.name),
                    priority=priority,
                )
            )

        return queries
    def stage_count(self) -> int:
        return len(self.SEARCH_STAGES)