from automation.intelligence.query_builder import QueryBuilder
from automation.intelligence.models import CompanyInput

qb = QueryBuilder()

company = CompanyInput(name="Google")

print(qb.build_stage(company, 0))
print(qb.build_stage(company, 1))
print(qb.build_stage(company, 2))
print(qb.build_stage(company, 3))