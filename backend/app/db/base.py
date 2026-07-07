"""
Import all models here so Alembic's autogenerate can discover them
via `Base.metadata`. Add new model imports as the schema grows.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.company import Company  # noqa: F401
