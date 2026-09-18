"""
Azztec_SaaS_app_diag_repo_v1_0_0.py  ->  backend/app/diag/repo.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.3 · OD-60
Pair:     backend/tests/test_diag_trail.py 1.0.0

Binds the statements in sql.py and hands back plain dicts. db.rows() already strips char(n) padding and
turns Decimal into int, so a row is JSON-ready without a schema layer - these are dev-only support
routes, not the contract (OD-61).

purge() counts before it deletes and defaults to dry_run=True. The caller decides; the lifespan task
passes dry_run=False once a day. Deletes run in batches so the table everything writes to is never held
under one long lock.

Changelog:
  1.0.0  Initial D1a.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Connection

from app.core import db
from app.diag import sql as dsql

__version__ = "1.0.0"


def trail(
    conn: Connection,
    user_id: int = 0,
    minutes_back: int = 30,
    problems_only: bool = False,
    row_limit: int = dsql.DEFAULT_ROW_LIMIT,
) -> list[dict[str, Any]]:
    return db.rows(
        conn,
        dsql.TRAIL,
        user_id=int(user_id or 0),
        minutes_back=max(1, int(minutes_back)),
        problems_only=1 if problems_only else 0,
        row_limit=max(1, int(row_limit)),
    )


def problems(
    conn: Connection, hours_back: int = 24, row_limit: int = dsql.DEFAULT_ROW_LIMIT
) -> list[dict[str, Any]]:
    return db.rows(conn, dsql.PROBLEMS, hours_back=max(1, int(hours_back)), row_limit=max(1, int(row_limit)))


def by_rid(conn: Connection, session_id: str, row_limit: int = 10) -> list[dict[str, Any]]:
    """The self-test's read-back: the rows the writer just wrote for one request id."""
    return db.rows(conn, dsql.BY_RID, session_id=str(session_id), row_limit=max(1, int(row_limit)))


def who_is_on(conn: Connection, minutes_back: int = 30) -> list[dict[str, Any]]:
    return db.rows(conn, dsql.WHOISON, minutes_back=max(1, int(minutes_back)))


def users(conn: Connection, minutes_back: int = 1440) -> list[dict[str, Any]]:
    return db.rows(conn, dsql.USERS, minutes_back=max(1, int(minutes_back)))


def retention_days(conn: Connection, default: int = dsql.DEFAULT_RETENTION_DAYS) -> int:
    """System_Configuration DIAG_RETENTION_DAYS. Absent or junk -> the default (60, OD-60). The app reads
    this key and never writes it - a DBA sets it."""
    raw = db.config_value(conn, "DIAG_RETENTION_DAYS", str(default))
    try:
        days = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return days if days > 0 else default


def purge(
    conn: Connection,
    days: int = dsql.DEFAULT_RETENTION_DAYS,
    dry_run: bool = True,
    batch: int = dsql.PURGE_BATCH_ROWS,
) -> dict[str, Any]:
    """Count first, then delete in batches. Returns what it found and what it removed."""
    days = max(1, int(days))
    found = int(db.scalar(conn, dsql.PURGE_COUNT, days=days) or 0)
    if dry_run or found == 0:
        return {"cutoffDays": days, "rows": found, "deleted": 0, "dryRun": bool(dry_run)}
    deleted = 0
    while True:
        n = db.execute(conn, dsql.PURGE_BATCH, days=days, batch=max(1, int(batch)))
        deleted += int(n or 0)
        if not n:
            break
    return {"cutoffDays": days, "rows": found, "deleted": deleted, "dryRun": False}


def delete_by_id(conn: Connection, diag_id: int) -> int:
    """Marker Law. The only delete a test or the self-test may make."""
    return db.execute(conn, dsql.DELETE_BY_ID, diag_id=int(diag_id))
