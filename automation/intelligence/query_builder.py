from automation.intelligence.models import CompanyInput, SearchQuery


class QueryBuilder:

    SEARCH_TEMPLATES = [
    ("linkedin", 'site:linkedin.com/company "{name}"', 1),
    ("indeed", 'site:indeed.com "{name}"', 2),
    ("glassdoor", 'site:glassdoor.com "{name}"', 2),
    ("clutch", 'site:clutch.co "{name}"', 2),
    ("website", '"{name}" official website', 1),
    ("contact", '"{name}" contact', 2),
    ("email", '"{name}" email', 3),
    ("phone", '"{name}" phone', 3),
]

    def build(
    self,
    company: CompanyInput,
) -> list[SearchQuery]:

        queries = []

        for source, template, priority in self.SEARCH_TEMPLATES:

            queries.append(
                SearchQuery(
                    source=source,
                    query=template.format(name=company.name),
                    priority=priority,
                )
            )

        return queries