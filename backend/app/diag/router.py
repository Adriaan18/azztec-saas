"""
Azztec_SaaS_app_diag_router_v1_0_1.py  ->  backend/app/diag/router.py
Version:  1.0.1
Author:   Adriaan
Spec:     Azztec_SaaS_D1a_Persist_Chunk_Spec_v1_0_0.md §3.3 · OD-61 (signed 2026-09-19)
Pair:     backend/tests/test_diag_trail.py 1.0.0

Support routes, not product routes. Two consequences, both deliberate:

  include_in_schema=False  they stay out of the OpenAPI document, so the contract file and the generated
                           TypeScript client are untouched by this slice (test_openapi_contract proves it).
  _dev_only                outside WORKMATE_ENV=dev every one of them is a 404 - not a 403, which would
                           advertise that the route exists. The trail is personal information; the auth
                           slice replaces this check with an administrator role, and D1b's viewer inherits
                           whatever is in place then.

Changelog:
  1.0.1  Smoke fix, before the tag: POST /_diag/purge defaulted days to 0 under a ge=1 constraint, so
         the documented call (no days = the retention setting) was a 422. days is optional now; absent
         means System_Configuration DIAG_RETENTION_DAYS, default 60 (OD-60).
  1.0.0  Initial D1a.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.engine import Connection

from app.core import db, diag
from app.core.config import get_settings
from app.diag import repo
from app.diag import sql as dsql

__version__ = "1.0.1"

router = APIRouter(prefix="/_diag", tags=["diag"], include_in_schema=False)


def _dev_only(request: Request) -> None:
    s = get_settings()
    if s.is_dev:
        return
    rid = getattr(request.state, "rid", "")
    diag.log("G", f"diag route refused env={s.env}", request_id=rid, source="diag", dedupe=False)
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not Found"})


Dev = Annotated[None, Depends(_dev_only)]
Conn = Annotated[Connection, Depends(db.get_conn)]


@router.get("/trail")
def get_trail(
    _dev: Dev,
    conn: Conn,
    userId: Annotated[int, Query(description="0 = everyone")] = 0,  # noqa: N803 - the wire name
    minutesBack: Annotated[int, Query(ge=1, le=43200)] = 30,  # noqa: N803
    problemsOnly: Annotated[bool, Query(description="only [E] and [G]")] = False,  # noqa: N803
    rowLimit: Annotated[int, Query(ge=1, le=2000)] = dsql.DEFAULT_ROW_LIMIT,  # noqa: N803
) -> dict[str, Any]:
    rows = repo.trail(
        conn, user_id=userId, minutes_back=minutesBack, problems_only=problemsOnly, row_limit=rowLimit
    )
    return {"ok": True, "count": len(rows), "rows": rows}


@router.get("/problems")
def get_problems(
    _dev: Dev,
    conn: Conn,
    hoursBack: Annotated[int, Query(ge=1, le=720)] = 24,  # noqa: N803
    rowLimit: Annotated[int, Query(ge=1, le=2000)] = dsql.DEFAULT_ROW_LIMIT,  # noqa: N803
) -> dict[str, Any]:
    rows = repo.problems(conn, hours_back=hoursBack, row_limit=rowLimit)
    return {"ok": True, "count": len(rows), "rows": rows}


@router.get("/whoison")
def get_who_is_on(
    _dev: Dev,
    conn: Conn,
    minutesBack: Annotated[int, Query(ge=1, le=1440)] = 30,  # noqa: N803
) -> dict[str, Any]:
    rows = repo.who_is_on(conn, minutes_back=minutesBack)
    return {"ok": True, "count": len(rows), "rows": rows}


@router.get("/users")
def get_users(
    _dev: Dev,
    conn: Conn,
    minutesBack: Annotated[int, Query(ge=1, le=43200)] = 1440,  # noqa: N803
) -> dict[str, Any]:
    rows = repo.users(conn, minutes_back=minutesBack)
    return {"ok": True, "count": len(rows), "rows": rows}


@router.post("/purge")
def post_purge(
    request: Request,
    _dev: Dev,
    conn: Conn,
    days: Annotated[int | None, Query(ge=1, le=3650, description="absent = the retention setting")] = None,
    dry_run: Annotated[bool, Query(alias="dry_run")] = True,
) -> dict[str, Any]:
    """OD-60. dry_run defaults to true; the daily task is the only caller that passes false by itself."""
    rid = getattr(request.state, "rid", "")
    keep = days or repo.retention_days(conn)
    out = repo.purge(conn, days=keep, dry_run=dry_run)
    diag.log(
        "S" if dry_run else "F",
        f"diag purge {out['deleted']} of {out['rows']} rows older than {keep} days dryRun={out['dryRun']}",
        request_id=rid,
        source="diag",
        dedupe=False,
    )
    return {"ok": True, **out}
