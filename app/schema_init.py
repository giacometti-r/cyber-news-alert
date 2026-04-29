from __future__ import annotations

from app.db import Database
from app.models import Base


def initialize_schema(database: Database) -> None:
    Base.metadata.create_all(bind=database.engine, checkfirst=True)
