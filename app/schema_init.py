from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy import text

from app.db import Database
from app.models import Base


def _add_column_if_missing(conn: object, table_name: str, column_name: str, ddl: str) -> None:
    inspector = inspect(conn)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return
    conn.execute(text(ddl))


def initialize_schema(database: Database) -> None:
    Base.metadata.create_all(bind=database.engine, checkfirst=True)
    with database.engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE articles ALTER COLUMN source_name TYPE VARCHAR(1024)"))

        _add_column_if_missing(
            conn,
            "articles",
            "article_type",
            "ALTER TABLE articles ADD COLUMN article_type VARCHAR(40) DEFAULT 'opinion'",
        )
        _add_column_if_missing(conn, "articles", "incident_key", "ALTER TABLE articles ADD COLUMN incident_key VARCHAR(64)")
        _add_column_if_missing(
            conn,
            "alerts",
            "channel",
            "ALTER TABLE alerts ADD COLUMN channel VARCHAR(20) DEFAULT 'immediate'",
        )
        _add_column_if_missing(conn, "alerts", "routing_reason", "ALTER TABLE alerts ADD COLUMN routing_reason VARCHAR(80)")
