"""
Azztec_SaaS_alembic_env_v1_0_0.py  ->  backend/alembic/env.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_S1j_KT_Uplift_Chunk_Spec_v1_0_0.md §3.1 (OD-43); Data Layer 1.0.0 §98

The URL comes from Settings through db.build_url() - the same URL the app runs on, so a migration lands
in the database the API reads. target_metadata is None on purpose: there is nothing to autogenerate
from and never will be against the legacy schema (CLAUDE.md rule 5). alembic_version lives in dbo.

Offline mode (`alembic upgrade head --sql`) renders every statement to stdout without a connection -
that is the migration's DRY_RUN. Migrations must not touch the inspector when
context.is_offline_mode() is True (0001 checks that flag).

Changelog:
  1.0.0  Initial. S1j.
"""

from __future__ import annotations

from alembic import context

from app.core.config import get_settings
from app.core.db import build_url, get_engine

__version__ = "1.0.0"

VERSION_TABLE = "alembic_version"
VERSION_SCHEMA = "dbo"


def run_migrations_offline() -> None:
    context.configure(
        url=build_url(get_settings()),
        target_metadata=None,
        literal_binds=True,
        version_table=VERSION_TABLE,
        version_table_schema=VERSION_SCHEMA,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = get_engine()  # pyodbc pooling off, pre_ping on - the app's own engine, not a second one
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table=VERSION_TABLE,
            version_table_schema=VERSION_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
