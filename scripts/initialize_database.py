"""Initialize the PostgreSQL schema and apply pending migrations."""

from __future__ import annotations

from pathlib import Path

import psycopg

from hidden_link_checker_api.config import ApiSettings

ROOT = Path(__file__).resolve().parents[1]
INITIAL_SCHEMA = ROOT / "scripts" / "initial_schema.sql"
MIGRATIONS = ROOT / "migrations"


def main() -> None:
    database_url = ApiSettings().database_url
    if not database_url:
        raise SystemExit(
            "HIDDEN_LINK_CHECKER_DATABASE_URL is required. "
            "Set it before starting the API."
        )

    with psycopg.connect(database_url) as connection:
        _ensure_schema(connection)
        _apply_migrations(connection)


def _ensure_schema(connection: psycopg.Connection[object]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'users')"
        )
        schema_exists = cursor.fetchone()[0]
        if not schema_exists:
            cursor.execute(INITIAL_SCHEMA.read_text(encoding="utf-8"))
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                ("0001_initial_schema",),
            )


def _apply_migrations(connection: psycopg.Connection[object]) -> None:
    with connection.cursor() as cursor:
        for migration_path in sorted(MIGRATIONS.glob("*.sql")):
            version = migration_path.stem
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = %s", (version,))
            if cursor.fetchone() is not None:
                continue
            cursor.execute(migration_path.read_text(encoding="utf-8"))
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))


if __name__ == "__main__":
    main()
