"""
Azztec_SaaS_app_workorders_router_v1_0_0.py  ->  backend/app/workorders/router.py
Version:  1.0.0
Author:   Adriaan
Spec:     Azztec_SaaS_W1a_WOMaint_Read_Api_Chunk_Spec_v1_0_0.md §3.5 · OD-64, OD-68, OD-69, OD-70
Ported:   the WOMaint v16.28.3 read path - the list (Search v12), the record (Item + Detail/Item +
          responsible users + resources compare), the Linked / Event History / Queries / PO tabs.
Pair:     backend/tests/test_workorders_api.py 1.0.0

Six GET routes, plain def (D-2), mounted under /api/v1 by main.py 0.5.0. Every 200 carries the OD-14
envelope; every error is the flat OD-15 shape (main.py's handler renders the HTTPException detail).
  400  BAD_FILTER   woType outside '' / N / CP / M  (a JSONResponse, the planner's WindowError shape)
  404  ARCHIVED     the id is in WO_C_header only (OD-68) - the archive record is a later slice
  404  NOT_FOUND    the id is in neither table
  401  from the actor dependency · 405 from Starlette · 422 FastAPI's own for range violations
One [F] line per 200, printed and NOT persisted (OD-69 - the trail is for writes and failures; the
middleware still persists >= 400 and >= 2000 ms). One persisted [G] when a record has no details row.

Changelog:
  1.0.0  Initial W1a.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Connection

from app.core import db, diag
from app.core.deps import get_current_actor
from app.workorders import repo
from app.workorders.schemas import (
    ApiError,
    EventPage,
    LinkedFamily,
    PoList,
    QueryList,
    WoList,
    WoRecord,
)

__version__ = "1.0.0"

router = APIRouter(prefix="/workorders", tags=["workorders"])

Conn = Annotated[Connection, Depends(db.get_conn)]
Actor = Annotated[int, Depends(get_current_actor)]
WoId = Annotated[int, Path(gt=0, description="WO_N_Header.WO_ID")]

_ERRORS = {401: {"model": ApiError}, 404: {"model": ApiError}}


def _envelope(data: dict, actor: int, t0: float) -> int:
    ms = int((time.perf_counter() - t0) * 1000)
    data["ok"] = True
    data["apiVersion"] = __version__
    data["actor"] = actor
    data["ms"] = ms
    return ms


def _require_live(conn: Connection, wo_id: int, rid: str, actor: int) -> None:
    """The tab routes' guard and the record's 404 split (OD-68)."""
    if repo.live_exists(conn, wo_id):
        return
    if repo.archived_exists(conn, wo_id):
        diag.log("G", f"wo {wo_id} is archived", request_id=rid, actor=actor)
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ARCHIVED",
                "message": f"WO {wo_id} is in the archive (WO_C_header); the archive record is not in W1",
            },
        )
    diag.log("G", f"wo {wo_id} not found", request_id=rid, actor=actor)
    raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"WO {wo_id} not found"})


@router.get("", response_model=WoList, responses={400: {"model": ApiError}, 401: {"model": ApiError}})
def list_workorders(
    request: Request,
    conn: Conn,
    actor: Actor,
    woType: Annotated[str, Query(description="'' all · N work orders · CP capital · M PMs")] = "N",
    includeClosed: Annotated[int, Query(ge=0, le=2, description="0 open · 1 all · 2 closed/cancelled")] = 0,
    includeArchive: Annotated[int, Query(ge=0, le=2, description="0 live · 1 both · 2 archive only")] = 0,
    search: Annotated[str, Query(description="one term, Short_WO_Id or WO_Title contains")] = "",
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WoList:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    wo_type = woType.strip()
    if wo_type not in repo.WO_TYPES:
        diag.log("G", f"wo search refused: woType={woType!r}", request_id=rid, actor=actor)
        message = f"woType must be one of '', N, CP, M (got {woType!r})"
        body = {"ok": False, "code": "BAD_FILTER", "message": message, "rid": rid}
        return JSONResponse(body, status_code=400)
    term = search.strip()
    rows, more = repo.search(
        conn,
        wo_type=wo_type,
        closed=includeClosed,
        archive=includeArchive,
        q=term,
        limit=limit,
        offset=offset,
    )
    data = {
        "rows": rows,
        "count": len(rows),
        "more": more,
        "filters": {
            "woType": wo_type,
            "includeClosed": includeClosed,
            "includeArchive": includeArchive,
            "search": term,
            "limit": limit,
            "offset": offset,
        },
    }
    ms = _envelope(data, actor, t0)
    diag.log(
        "F",
        f"wo search type={wo_type} closed={includeClosed} archive={includeArchive} q={term!r} "
        f"offset={offset} rows={len(rows)} more={more} in {ms} ms",
        request_id=rid,
        actor=actor,
        persist=False,
    )
    return WoList.model_validate(data)  # extra="forbid": contract drift raises here, loudly


@router.get("/{wo_id}", response_model=WoRecord, responses=_ERRORS)
def get_workorder(request: Request, wo_id: WoId, conn: Conn, actor: Actor) -> WoRecord:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    rec = repo.fetch_item(conn, wo_id)
    if rec is None:
        _require_live(conn, wo_id, rid, actor)  # raises 404 ARCHIVED or NOT_FOUND
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": f"WO {wo_id} not found"})
    if rec["detailsMissing"]:
        diag.log("G", f"wo {wo_id} has no WO_N_Details row", request_id=rid, actor=actor)
    ms = _envelope(rec, actor, t0)
    diag.log(
        "F",
        f"wo {wo_id} {rec['sid']} status={rec['status']} prog={rec['prog']} within={rec['completeWithin']} "
        f"resp={len(rec['respUsers'])} res={len(rec['resources']['rows'])} "
        f"details={'missing' if rec['detailsMissing'] else 'ok'} in {ms} ms",
        request_id=rid,
        actor=actor,
        persist=False,
    )
    return WoRecord.model_validate(rec)


@router.get("/{wo_id}/events", response_model=EventPage, responses=_ERRORS)
def get_events(
    request: Request,
    wo_id: WoId,
    conn: Conn,
    actor: Actor,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> EventPage:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    _require_live(conn, wo_id, rid, actor)
    rows, more = repo.fetch_events(conn, wo_id, offset=offset, limit=limit)
    data = {"rows": rows, "count": len(rows), "more": more, "offset": offset}
    ms = _envelope(data, actor, t0)
    diag.log(
        "F",
        f"wo {wo_id} events offset={offset} rows={len(rows)} more={more} in {ms} ms",
        request_id=rid,
        actor=actor,
        persist=False,
    )
    return EventPage.model_validate(data)


@router.get("/{wo_id}/linked", response_model=LinkedFamily, responses=_ERRORS)
def get_linked(request: Request, wo_id: WoId, conn: Conn, actor: Actor) -> LinkedFamily:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    _require_live(conn, wo_id, rid, actor)
    data = repo.fetch_linked(conn, wo_id)
    ms = _envelope(data, actor, t0)
    diag.log(
        "F",
        f"wo {wo_id} linked rows={data['count']} root={data['root']} in {ms} ms",
        request_id=rid,
        actor=actor,
        persist=False,
    )
    return LinkedFamily.model_validate(data)


@router.get("/{wo_id}/queries", response_model=QueryList, responses=_ERRORS)
def get_queries(request: Request, wo_id: WoId, conn: Conn, actor: Actor) -> QueryList:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    _require_live(conn, wo_id, rid, actor)
    rows = repo.fetch_queries(conn, wo_id)
    data = {"rows": rows, "count": len(rows)}
    ms = _envelope(data, actor, t0)
    diag.log(
        "F", f"wo {wo_id} queries rows={len(rows)} in {ms} ms", request_id=rid, actor=actor, persist=False
    )
    return QueryList.model_validate(data)


@router.get("/{wo_id}/pos", response_model=PoList, responses=_ERRORS)
def get_po_lines(request: Request, wo_id: WoId, conn: Conn, actor: Actor) -> PoList:
    rid = getattr(request.state, "rid", "")
    t0 = time.perf_counter()
    _require_live(conn, wo_id, rid, actor)
    rows = repo.fetch_po_lines(conn, wo_id)
    data = {"rows": rows, "count": len(rows)}
    ms = _envelope(data, actor, t0)
    diag.log("F", f"wo {wo_id} pos rows={len(rows)} in {ms} ms", request_id=rid, actor=actor, persist=False)
    return PoList.model_validate(data)
