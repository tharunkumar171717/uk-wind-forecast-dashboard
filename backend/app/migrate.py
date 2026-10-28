"""Apply SQL migrations in order. Every migration is idempotent (IF NOT EXISTS).

Usage: python -m app.migrate
"""

from pathlib import Path

from sqlalchemy.engine import Engine

from app.db import get_engine

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def apply_migrations(engine: Engine) -> list[str]:
    applied = []
    with engine.begin() as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            conn.exec_driver_sql(path.read_text())
            applied.append(path.name)
    return applied


def main() -> None:
    for name in apply_migrations(get_engine()):
        print(f"applied {name}")


if __name__ == "__main__":
    main()
