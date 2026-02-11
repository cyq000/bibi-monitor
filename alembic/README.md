# Alembic scaffold (minimal)

This folder is a minimal scaffold to document how to add alembic migrations.

Steps to initialize alembic locally:

1. Install alembic: `pip install alembic`
2. From repo root run: `alembic init alembic` (this will create a more complete scaffold)
3. Edit `alembic/env.py` to import `src.db.Base` and set `target_metadata = src.db.Base.metadata`.
4. Generate migrations: `alembic revision --autogenerate -m "init"`
5. Apply migrations: `alembic upgrade head`

The `src/db.py` provides `Base` and `get_engine()` to integrate with Alembic.
